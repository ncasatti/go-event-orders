"""Deploy stack to AWS"""

import os
import subprocess
import time
from argparse import ArgumentParser, Namespace
from typing import List, Optional

# Import build and zip commands for --all flag
from commands.core_commands.build import BuildCommand
from commands.core_commands.zip import ZipCommand
from config import (
    BIN_DIR,
    GO_FUNCTIONS,
    PROJECT_ROOT,
    SERVERLESS_PROFILE,
    SERVERLESS_STAGE,
)
from core.function_utils import resolve_function_list
from core.subprocess_helper import run_in_project_root

from clingy.commands.base import BaseCommand
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


class DeployCommand(BaseCommand):
    """Deploy serverless stack to AWS"""

    name = "deploy"
    help = "Deploy stack to AWS"
    description = "Deploy the serverless stack to AWS using Serverless Framework"
    epilog = """Examples:
  manager.py deploy                    # Deploy full stack to AWS
  manager.py deploy -f status          # Deploy only status function (fast)
  manager.py deploy --debug            # Deploy with debug output
  manager.py deploy --all              # Build, zip, and deploy all functions
  manager.py deploy --all -f status    # Build, zip, and deploy only status function
"""

    def add_arguments(self, parser: ArgumentParser):
        """Add command-specific arguments"""
        parser.add_argument("--debug", action="store_true", help="Enable debug mode for deployment")
        parser.add_argument("--all", action="store_true", help="Build, zip, and deploy in one step")
        parser.add_argument(
            "-f",
            "--function",
            type=str,
            help="Specific function name to deploy (standalone) or build/zip/deploy (with --all)",
        )

    def execute(self, args: Namespace) -> bool:
        """Execute deploy command"""
        # Check if --all flag is set (CLI mode)
        if hasattr(args, "all") and args.all:
            return self._execute_all(args)

        # Resolve function list (supports both dev mode and CLI mode)
        functions = resolve_function_list(args)
        if not functions:
            return False

        # Check debug flag (may not exist in interactive mode)
        debug = getattr(args, "debug", False)
        return self._deploy(debug, functions)

    def get_menu_tree(self) -> MenuNode:
        return super().get_menu_tree()

    def _execute_all(self, args: Namespace) -> bool:
        """Execute build, zip, and deploy in sequence"""
        log_header("BUILD, ZIP, AND DEPLOY")

        # Resolve function list
        functions = resolve_function_list(args)
        if not functions:
            return False

        # Step 1: Build
        log_section("STEP 1: BUILDING")
        build_cmd = BuildCommand()
        build_args = Namespace(function=args.function, function_list=functions)

        if not build_cmd.execute(build_args):
            log_error("Build failed. Stopping pipeline.")
            return False

        # Step 2: Zip
        log_section("STEP 2: COMPRESSING")
        zip_cmd = ZipCommand()
        zip_args = Namespace(function=args.function, function_list=functions)

        if not zip_cmd.execute(zip_args):
            log_error("Compression failed. Stopping pipeline.")
            return False

        # Add blank line between build/zip and deploy
        print()

        # Step 3: Deploy
        log_section("STEP 3: DEPLOYING")
        debug = getattr(args, "debug", False)
        if not self._deploy(debug, functions):
            log_error("Deployment failed.")
            return False

        log_success("All steps completed successfully!")
        return True

    def _validate_function(self, func_name: str) -> bool:
        """
        Validate that function exists and has a zip file

        Args:
            func_name: Function name to validate

        Returns:
            True if valid, False otherwise
        """
        # Check if function exists in GO_FUNCTIONS
        if func_name not in GO_FUNCTIONS:
            log_error(f"Function '{func_name}' not found in GO_FUNCTIONS list")
            log_info(
                f"Available functions: {', '.join(GO_FUNCTIONS[:5])}{'...' if len(GO_FUNCTIONS) > 5 else ''}"
            )
            return False

        # Check if zip file exists
        zip_path = os.path.join(BIN_DIR, func_name, f"{func_name}.zip")
        if not os.path.exists(zip_path):
            log_warning(f"Zip file not found: {zip_path}")
            log_info("Run 'python manager.py build' and 'python manager.py zip' first")
            return False

        return True

    def _deploy(self, debug: bool = False, functions: Optional[List[str]] = None) -> bool:
        """
        Execute the actual deployment with smart strategy selection.

        Strategy:
        - Single function: Fast deploy (code only, no infrastructure)
        - All functions: Full stack deploy (infrastructure + all functions)
        - Partial list: Deploy each function individually

        Args:
            debug: Enable debug mode
            functions: List of function names to deploy (None = full stack)

        Returns:
            True if deployment succeeded
        """
        # Determine deployment strategy
        if functions is None or len(functions) == len(GO_FUNCTIONS):
            # Full stack deployment (all functions or explicit None)
            return self._deploy_full_stack(debug)
        elif len(functions) == 1:
            # Single function deployment (fast, code only)
            return self._deploy_single_function(debug, functions[0])
        else:
            # Multiple (but not all) functions - deploy each individually
            return self._deploy_multiple_functions(debug, functions)

    def _deploy_single_function(self, debug: bool, function_name: str) -> bool:
        """
        Deploy a single function (fast, code only).

        Args:
            debug: Enable debug mode
            function_name: Function name to deploy

        Returns:
            True if deployment succeeded
        """
        # Validate function
        if not self._validate_function(function_name):
            return False

        log_header(f"DEPLOYING FUNCTION: {function_name}")
        log_section(
            f"DEPLOYING {function_name} (stage: {SERVERLESS_STAGE}, profile: {SERVERLESS_PROFILE})"
        )

        # Build serverless deploy function command
        command = [
            "serverless",
            "deploy",
            "function",
            "-f",
            function_name,
            "--stage",
            SERVERLESS_STAGE,
            "--aws-profile",
            SERVERLESS_PROFILE,
        ]

        if debug:
            command.append("--debug")
            log_info("Debug mode enabled for deployment")

        log_info(f"Executing: {' '.join(command)}")
        log_info("Note: This only updates function code, not infrastructure/endpoints")
        start_time = time.time()

        try:
            result = run_in_project_root(command, check=True, capture_output=False, text=True)

            duration = time.time() - start_time

            if result.returncode == 0:
                log_success(f"Function '{function_name}' deployed successfully to AWS", duration)
                return True
            else:
                log_error(f"Deployment failed with code {result.returncode}", duration)
                return False

        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            log_error("Error during deployment", duration)
            return False

        except FileNotFoundError:
            log_error("Serverless Framework is not installed or not found in PATH")
            log_info("Install with: npm install -g serverless")
            return False

    def _deploy_full_stack(self, debug: bool) -> bool:
        """
        Deploy full stack (infrastructure + all functions).

        Args:
            debug: Enable debug mode

        Returns:
            True if deployment succeeded
        """
        log_header("DEPLOYING TO AWS")
        log_section(
            f"DEPLOYING FULL STACK (stage: {SERVERLESS_STAGE}, profile: {SERVERLESS_PROFILE})"
        )

        # Build serverless command
        command = [
            "serverless",
            "deploy",
            "--stage",
            SERVERLESS_STAGE,
            "--aws-profile",
            SERVERLESS_PROFILE,
        ]

        if debug:
            command.append("--debug")
            log_info("Debug mode enabled for deployment")

        log_info(f"Executing: {' '.join(command)}")
        start_time = time.time()

        try:
            result = run_in_project_root(command, check=True, capture_output=False, text=True)

            duration = time.time() - start_time

            if result.returncode == 0:
                log_success("Stack deployed successfully to AWS", duration)
                return True
            else:
                log_error(f"Deployment failed with code {result.returncode}", duration)
                return False

        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            log_error("Error during deployment", duration)
            return False

        except FileNotFoundError:
            log_error("Serverless Framework is not installed or not found in PATH")
            log_info("Install with: npm install -g serverless")
            return False

    def _deploy_multiple_functions(self, debug: bool, functions: List[str]) -> bool:
        """
        Deploy multiple functions individually (not all functions).

        Args:
            debug: Enable debug mode
            functions: List of function names to deploy

        Returns:
            True if all deployments succeeded
        """
        log_header(f"DEPLOYING {len(functions)} FUNCTIONS")
        log_info(f"Deploying functions individually: {', '.join(functions)}")
        log_info("Note: This only updates function code, not infrastructure/endpoints")

        success_count = 0
        failed_functions = []

        for func in functions:
            if self._deploy_single_function(debug, func):
                success_count += 1
            else:
                failed_functions.append(func)

            # Add spacing between function deployments
            if func != functions[-1]:
                print()

        # Summary
        print()
        if failed_functions:
            log_error(f"Deployment completed with {len(failed_functions)} failure(s)")
            log_info(f"Failed functions: {', '.join(failed_functions)}")
            return False
        else:
            log_success(f"All {success_count} functions deployed successfully")
            return True
