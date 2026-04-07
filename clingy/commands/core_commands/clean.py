"""Clean build artifacts"""

import os
import shutil
from argparse import ArgumentParser, Namespace
from typing import List, Optional

from config import BIN_DIR, GO_FUNCTIONS
from core.function_utils import resolve_function_list

from clingy.commands.base import BaseCommand
from clingy.core.logger import (
    log_error,
    log_header,
    log_info,
    log_section,
    log_success,
)
from clingy.core.menu import MenuNode


class CleanCommand(BaseCommand):
    """Remove build artifacts (binaries and zips)"""

    name = "clean"
    help = "Clean build artifacts"
    description = "Remove compiled binaries and zip files for functions"
    epilog = """Examples:
  manager.py clean              # Clean all build artifacts
  manager.py clean -f status    # Clean only status function artifacts
"""

    def add_arguments(self, parser: ArgumentParser):
        """Add command-specific arguments"""
        parser.add_argument(
            "-f",
            "--function",
            type=str,
            help="Specific function to clean (cleans all if not specified)",
        )

    def execute(self, args: Namespace) -> bool:
        """Execute clean command"""
        # Resolve function list (supports both CLI and interactive mode)
        functions = resolve_function_list(args)
        if not functions:
            return False

        # If no specific function, clean all
        if functions == GO_FUNCTIONS:
            return self._clean_all()
        else:
            return self._clean_functions(functions)

    def get_menu_tree(self) -> MenuNode:
        return super().get_menu_tree()

    def _clean_all(self) -> bool:
        """Clean all build artifacts (remove entire .bin directory)"""
        log_header("CLEANING ALL BUILD ARTIFACTS")

        if not os.path.exists(BIN_DIR):
            log_info("No artifacts to clean (.bin directory does not exist)")
            return True

        try:
            shutil.rmtree(BIN_DIR)
            log_success(f"Removed {BIN_DIR} directory")
            return True
        except Exception as e:
            log_error(f"Error removing {BIN_DIR}: {e}")
            return False

    def _clean_functions(self, functions: List[str]) -> bool:
        """Clean specific functions' artifacts"""
        log_section(f"CLEANING {len(functions)} FUNCTIONS")

        if not os.path.exists(BIN_DIR):
            log_info("No artifacts to clean (.bin directory does not exist)")
            return True

        success_count = 0
        failed_functions = []

        for func in functions:
            if self._clean_function(func):
                success_count += 1
            else:
                failed_functions.append(func)

        # Summary
        log_info(f"Cleaned {success_count}/{len(functions)} functions")
        if failed_functions:
            log_error(f"Failed to clean: {', '.join(failed_functions)}")
            return False

        log_success("All selected functions cleaned successfully")
        return True

    def _clean_function(self, function_name: str) -> bool:
        """
        Clean artifacts for a specific function.

        Removes:
        - Binary: .bin/{function}/bootstrap
        - Zip: .bin/{function}/{function}.zip
        - Directory: .bin/{function}/ (if empty after cleaning)

        Args:
            function_name: Function name to clean

        Returns:
            True if cleaned successfully, False otherwise
        """
        function_dir = os.path.join(BIN_DIR, function_name)

        if not os.path.exists(function_dir):
            log_info(f"{function_name}: No artifacts to clean (directory does not exist)")
            return True

        artifacts_removed = []

        # Remove binary (bootstrap)
        binary_path = os.path.join(function_dir, "bootstrap")
        if os.path.exists(binary_path):
            try:
                os.remove(binary_path)
                artifacts_removed.append("binary")
            except Exception as e:
                log_error(f"{function_name}: Failed to remove binary: {e}")
                return False

        # Remove zip
        zip_path = os.path.join(function_dir, f"{function_name}.zip")
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
                artifacts_removed.append("zip")
            except Exception as e:
                log_error(f"{function_name}: Failed to remove zip: {e}")
                return False

        # Remove directory if empty
        try:
            if not os.listdir(function_dir):
                os.rmdir(function_dir)
        except Exception as e:
            log_info(f"{function_name}: Directory not empty, keeping it")

        if artifacts_removed:
            log_success(f"{function_name}: Removed {', '.join(artifacts_removed)}")
        else:
            log_info(f"{function_name}: No artifacts found")

        return True
