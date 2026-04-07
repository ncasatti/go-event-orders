"""Build Go functions to binaries"""

import os
import subprocess
import time
from argparse import ArgumentParser, Namespace
from typing import List, Optional

from config import BIN_DIR, BUILD_FLAGS, BUILD_SETTINGS, FUNCTIONS_DIR, GO_FUNCTIONS
from core.function_utils import resolve_function_list
from core.subprocess_helper import run_in_project_root

from clingy.commands.base import BaseCommand
from clingy.core.colors import Colors
from clingy.core.logger import (
    log_error,
    log_header,
    log_info,
    log_section,
    log_success,
    log_warning,
    print_summary,
)
from clingy.core.menu import MenuNode
from clingy.core.stats import stats


class BuildCommand(BaseCommand):
    """Build Go functions to binaries"""

    name = "build"
    help = "Build Go functions to binaries"
    description = "Compile Go Lambda functions to Linux/amd64 binaries for AWS Lambda"
    epilog = """Examples:
  manager.py build                 # Build all functions
  manager.py build -f status       # Build only the status function
  manager.py build -f getClientes  # Build only getClientes function
"""

    def add_arguments(self, parser: ArgumentParser):
        """Add command-specific arguments"""
        parser.add_argument(
            "-f",
            "--function",
            type=str,
            help="Specific function name to build (e.g., status, getClientes)",
        )

    def execute(self, args: Namespace) -> bool:
        """Execute build command"""
        # log_header("BUILDING GO FUNCTIONS")

        # Resolve function list (supports both dev mode and CLI mode)
        functions_to_build = resolve_function_list(args)
        if not functions_to_build:
            return False

        # Reset stats
        stats.reset()
        stats.total_functions = len(functions_to_build)

        # Build functions
        success = self._build_functions(functions_to_build)

        # Print summary
        print_summary()

        return success

    def get_menu_tree(self) -> MenuNode:
        return super().get_menu_tree()

    def _validate_function_exists(self, func_name: str) -> bool:
        """
        Validate that main.go exists for the function

        Args:
            func_name: Function name

        Returns:
            True if main.go exists, False otherwise
        """
        main_go_path = os.path.join(FUNCTIONS_DIR, func_name, "main.go")
        if not os.path.exists(main_go_path):
            log_warning(f"File {main_go_path} not found for function '{func_name}'")
            return False
        return True

    def _build_functions(self, functions_to_build: List[str]) -> bool:
        """
        Build Go functions with enhanced logging and filtering

        Args:
            functions_to_build: List of function names to build

        Returns:
            True if all builds succeeded, False otherwise
        """
        log_section(f"BUILDING {len(functions_to_build)} GO FUNCTIONS")

        overall_success = True

        for i, func_name in enumerate(functions_to_build, 1):
            log_info(f"Processing function {i}/{len(functions_to_build)}: {func_name}")
            start_time = time.time()

            # Validate source file exists
            if not self._validate_function_exists(func_name):
                stats.add_failure(func_name)
                overall_success = False
                continue

            source_dir = os.path.abspath(os.path.join(FUNCTIONS_DIR, func_name))
            go_file = os.path.join(source_dir, "main.go")
            output_dir = os.path.abspath(os.path.join(BIN_DIR, func_name))
            bootstrap_file = os.path.join(output_dir, "bootstrap")

            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                log_info(f"Directory created: {output_dir}")

            # Configure environment for cross-platform compilation
            env = os.environ.copy()
            env.update(BUILD_SETTINGS)

            # Build command
            command = ["go", "build"] + BUILD_FLAGS + ["-o", bootstrap_file, go_file]

            try:
                result = run_in_project_root(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=source_dir,
                )

                duration = time.time() - start_time

                if result.returncode == 0:
                    # Verify file was created correctly
                    if os.path.exists(bootstrap_file):
                        file_size = os.path.getsize(bootstrap_file)
                        log_success(f"{func_name} → {file_size:,} bytes", duration)
                        stats.add_success()
                    else:
                        log_error(f"{func_name} → bootstrap file not found", duration)
                        stats.add_failure(func_name)
                        overall_success = False
                else:
                    log_error(f"{func_name} → exit code {result.returncode}", duration)
                    if result.stderr:
                        print(f"  {Colors.RED}Error: {result.stderr.strip()}{Colors.RESET}")
                    stats.add_failure(func_name)
                    overall_success = False

            except subprocess.CalledProcessError as e:
                duration = time.time() - start_time
                log_error(f"{func_name} → compilation failed", duration)
                if e.stderr:
                    print(f"  {Colors.RED}Error: {e.stderr.strip()}{Colors.RESET}")
                stats.add_failure(func_name)
                overall_success = False

            except FileNotFoundError:
                duration = time.time() - start_time
                log_error("Go is not installed or not found in PATH", duration)
                stats.add_failure(func_name)
                overall_success = False
                break  # If Go is not available, don't try more functions

        return overall_success
