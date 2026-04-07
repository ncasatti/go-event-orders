"""Status command - Show Lambda functions status and configuration"""

import os
import subprocess
from argparse import ArgumentParser, Namespace
from typing import Optional

from config import (
    AWS_PROFILE,
    BIN_DIR,
    BUILD_SETTINGS,
    DEPENDENCIES,
    ENV,
    FUNCTIONS_DIR,
    GO_FUNCTIONS,
    SERVERLESS_STAGE,
    SERVICE_NAME,
)

from clingy.commands.base import BaseCommand
from clingy.core.colors import Colors
from clingy.core.emojis import Emoji
from clingy.core.logger import (
    log_error,
    log_header,
    log_info,
    log_section,
    log_success,
)
from clingy.core.menu import MenuNode


class StatusCommand(BaseCommand):
    """Show Lambda functions status and configuration"""

    name = "status"
    help = "Show functions status"
    description = "Display Lambda functions status, build status, dependencies, and configuration"

    def execute(self, args: Namespace) -> bool:
        """Execute status command"""
        log_header("SERVERLESS STATUS")
        self._show_all_status()
        return True

    def add_arguments(self, parser: ArgumentParser):
        return super().add_arguments(parser)

    def get_menu_tree(self) -> MenuNode:
        """Interactive menu for status information"""
        return MenuNode(
            label="Status & Info",
            emoji=Emoji.INFO,
            children=[
                MenuNode(
                    label="List All Functions",
                    emoji=Emoji.LIST,
                    action=self._list_functions,
                ),
                MenuNode(
                    label="Build Status",
                    emoji=Emoji.BUILD,
                    action=self._show_build_status,
                ),
                MenuNode(
                    label="Check Dependencies",
                    emoji=Emoji.PACKAGE,
                    action=self._check_dependencies,
                ),
                MenuNode(
                    label="Show Configuration",
                    emoji=Emoji.GEAR,
                    action=self._show_config,
                ),
                MenuNode(
                    label="Show All Status",
                    emoji=Emoji.INFO,
                    action=self._show_all_status,
                ),
            ],
        )

    # ========================================================================
    # Status Actions
    # ========================================================================

    def _list_functions(self) -> bool:
        """List all Lambda functions"""
        log_section(f"LAMBDA FUNCTIONS ({len(GO_FUNCTIONS)} total)")

        for i, func in enumerate(GO_FUNCTIONS, 1):
            # Check if source exists
            source_path = os.path.join(FUNCTIONS_DIR, func, "main.go")
            source_exists = os.path.exists(source_path)

            # Check if binary exists
            binary_path = os.path.join(BIN_DIR, func, "bootstrap")
            binary_exists = os.path.exists(binary_path)

            status_icon = "✅" if source_exists else "❌"
            build_icon = "📦" if binary_exists else "⚠️"

            log_info(f"{i:3d}. {status_icon} {build_icon} {func}")

        log_info(f"\nLegend: ✅ Source exists | 📦 Built | ⚠️ Not built | ❌ Missing source")
        return True

    def _show_build_status(self) -> bool:
        """Show build status for all functions"""
        log_section("BUILD STATUS")

        built_count = 0
        not_built_count = 0
        missing_source_count = 0

        for func in GO_FUNCTIONS:
            source_path = os.path.join(FUNCTIONS_DIR, func, "main.go")
            binary_path = os.path.join(BIN_DIR, func, "bootstrap")

            source_exists = os.path.exists(source_path)
            binary_exists = os.path.exists(binary_path)

            if not source_exists:
                log_error(f"{func} → Missing source (main.go)")
                missing_source_count += 1
            elif binary_exists:
                # Get binary size
                size = os.path.getsize(binary_path)
                log_success(f"{func} → Built ({size:,} bytes)")
                built_count += 1
            else:
                log_info(f"{func} → Not built")
                not_built_count += 1

        # Summary
        log_section("SUMMARY")
        log_success(f"Built: {built_count}")
        log_info(f"Not built: {not_built_count}")
        if missing_source_count > 0:
            log_error(f"Missing source: {missing_source_count}")

        return True

    def _check_dependencies(self) -> bool:
        """Check required system dependencies"""
        log_section("SYSTEM DEPENDENCIES")

        all_ok = True
        for dep in DEPENDENCIES:
            try:
                # Try to run the command
                result = subprocess.run(
                    [dep.command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    log_success(f"{dep.name} → {version}")
                else:
                    log_error(f"{dep.name} → Not found")
                    log_info(f"  Install: {dep.install_macos or dep.install_linux}")
                    all_ok = False
            except FileNotFoundError:
                log_error(f"{dep.name} → Not installed")
                log_info(f"  Install: {dep.install_macos or dep.install_linux}")
                all_ok = False
            except subprocess.TimeoutExpired:
                log_error(f"{dep.name} → Timeout")
                all_ok = False

        if all_ok:
            log_success("\nAll dependencies are installed")
        else:
            log_error("\nSome dependencies are missing")

        return all_ok

    def _show_config(self) -> bool:
        """Show current configuration"""
        log_section("CONFIGURATION")

        log_info(f"Environment: {Colors.CYAN}{ENV}{Colors.RESET}")
        log_info(f"AWS Profile: {Colors.CYAN}{AWS_PROFILE}{Colors.RESET}")
        log_info(f"Service Name: {Colors.CYAN}{SERVICE_NAME}{Colors.RESET}")
        log_info(f"Serverless Stage: {Colors.CYAN}{SERVERLESS_STAGE}{Colors.RESET}")
        log_info(f"Functions Directory: {Colors.CYAN}{FUNCTIONS_DIR}{Colors.RESET}")
        log_info(f"Binary Directory: {Colors.CYAN}{BIN_DIR}{Colors.RESET}")

        log_section("BUILD SETTINGS")
        for key, value in BUILD_SETTINGS.items():
            log_info(f"{key}: {Colors.CYAN}{value}{Colors.RESET}")

        return True

    def _show_all_status(self) -> bool:
        """Show all status information"""
        self._show_config()
        print()
        self._check_dependencies()
        print()
        self._show_build_status()
        return True
