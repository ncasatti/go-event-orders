"""Compress binaries to zip files"""

import os
import subprocess
import time
from argparse import ArgumentParser, Namespace
from typing import List, Optional

from config import BIN_DIR, GO_FUNCTIONS
from core.function_utils import resolve_function_list

from clingy.commands.base import BaseCommand
from clingy.core.colors import Colors
from clingy.core.logger import (
    log_error,
    log_header,
    log_info,
    log_section,
    log_success,
    print_summary,
)
from clingy.core.menu import MenuNode
from clingy.core.stats import stats


class ZipCommand(BaseCommand):
    """Compress binaries to zip files"""

    name = "zip"
    help = "Compress binaries to zip files"
    description = "Compress compiled Go binaries into deployment-ready zip files"
    epilog = """Examples:
  manager.py zip                   # Compress all built functions
  manager.py zip -f status         # Compress only the status function
  manager.py zip -f getVendedores  # Compress only getVendedores function
"""

    def add_arguments(self, parser: ArgumentParser):
        """Add command-specific arguments"""
        parser.add_argument(
            "-f",
            "--function",
            type=str,
            help="Specific function name to compress (e.g., status, getClientes)",
        )

    def execute(self, args: Namespace) -> bool:
        """Execute zip command"""
        # log_header("COMPRESSING FUNCTIONS")

        # Resolve function list (supports both dev mode and CLI mode)
        functions_to_zip = resolve_function_list(args)
        if not functions_to_zip:
            return False

        # Initialize stats if not already set (e.g., from build command)
        if stats.total_functions == 0:
            stats.reset()
            stats.total_functions = len(functions_to_zip)

        # Compress functions
        success = self._zip_functions(functions_to_zip)

        # Print summary
        print_summary()

        return success

    def get_menu_tree(self) -> MenuNode:
        return super().get_menu_tree()

    def _zip_functions(self, functions_to_zip: List[str]) -> bool:
        """
        Compress Go functions with enhanced logging and filtering

        Args:
            functions_to_zip: List of function names to compress

        Returns:
            True if all compressions succeeded, False otherwise
        """
        log_section(f"COMPRESSING {len(functions_to_zip)} FUNCTIONS")

        overall_success = True

        for i, func_name in enumerate(functions_to_zip, 1):
            log_info(f"Compressing function {i}/{len(functions_to_zip)}: {func_name}")
            start_time = time.time()

            output_dir = os.path.abspath(os.path.join(BIN_DIR, func_name))
            zip_file = os.path.join(output_dir, f"{func_name}.zip")
            bootstrap_file = os.path.join(output_dir, "bootstrap")

            # Validate bootstrap file exists
            if not os.path.exists(bootstrap_file):
                duration = time.time() - start_time
                log_error(f"{func_name} → bootstrap not found: {bootstrap_file}", duration)
                stats.add_failure(func_name)
                overall_success = False
                continue

            # Remove old zip file if it exists
            if os.path.exists(zip_file):
                os.remove(zip_file)

            # Compression command
            zip_command = ["zip", "-j", zip_file, bootstrap_file]

            try:
                result = subprocess.run(zip_command, check=True, capture_output=True, text=True)

                duration = time.time() - start_time

                if result.returncode == 0 and os.path.exists(zip_file):
                    zip_size = os.path.getsize(zip_file)
                    bootstrap_size = os.path.getsize(bootstrap_file)
                    compression_ratio = (
                        (1 - zip_size / bootstrap_size) * 100 if bootstrap_size > 0 else 0
                    )

                    log_success(
                        f"{func_name} → {zip_size:,} bytes (-{compression_ratio:.1f}%)",
                        duration,
                    )
                    # Only count success if this is a standalone zip command (not after build)
                    if stats.total_functions == len(functions_to_zip):
                        stats.add_success()
                else:
                    log_error(f"{func_name} → compression failed", duration)
                    if result.stderr:
                        print(f"  {Colors.RED}Error: {result.stderr.strip()}{Colors.RESET}")
                    stats.add_failure(func_name)
                    overall_success = False

            except subprocess.CalledProcessError as e:
                duration = time.time() - start_time
                log_error(f"{func_name} → error executing zip", duration)
                if e.stderr:
                    print(f"  {Colors.RED}Error: {e.stderr.strip()}{Colors.RESET}")
                stats.add_failure(func_name)
                overall_success = False

            except FileNotFoundError:
                duration = time.time() - start_time
                log_error("'zip' command not found on system", duration)
                stats.add_failure(func_name)
                overall_success = False
                break  # If zip is not available, don't try more functions

        return overall_success
