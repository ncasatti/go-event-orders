"""Interactive logs menu for Lambda functions"""

import subprocess
from argparse import ArgumentParser, Namespace
from typing import Optional

from config import AWS_PROFILE, GO_FUNCTIONS, SERVERLESS_STAGE, SERVICE_NAME
from core.subprocess_helper import run_in_project_root

from clingy.commands.base import BaseCommand
from clingy.core.colors import Colors
from clingy.core.emojis import Emoji
from clingy.core.logger import (
    log_error,
    log_header,
    log_info,
    log_success,
    log_warning,
)
from clingy.core.menu import MenuNode


class LogsCommand(BaseCommand):
    """Interactive logs menu for Lambda functions"""

    name = "logs"
    help = "Interactive logs menu"
    description = (
        "View CloudWatch logs for Lambda functions with multiple viewing options"
    )
    epilog = """Examples:
  manager.py logs           # Open interactive logs menu
"""

    def add_arguments(self, parser: ArgumentParser):
        """Add command-specific arguments"""
        parser.add_argument(
            "-f",
            "--function",
            type=str,
            help="Specific function name to view logs (skips function selection menu)",
        )

    def execute(self, args: Namespace) -> bool:
        """Execute logs command"""
        # If function is pre-selected (from logs menu), go directly to logs submenu
        if hasattr(args, "function") and args.function:
            if args.function in GO_FUNCTIONS:
                return self._show_logs_submenu(args.function)
            else:
                log_error(
                    f"Function '{args.function}' not found in available functions"
                )
                return False

        # Otherwise, show interactive menu
        return self._logs_menu()

    def get_menu_tree(self) -> MenuNode:
        return super().get_menu_tree()

    def _get_log_group_name(self, func_name: str) -> str:
        """
        Build CloudWatch log group name for a Lambda function

        Args:
            func_name: Lambda function name

        Returns:
            Full log group name
        """
        return f"/aws/lambda/{SERVICE_NAME}-{SERVERLESS_STAGE}-{func_name}"

    def _save_logs_to_file(self, func_name: str, logs_output: str) -> None:
        """
        Save logs output to results/logs/{func_name}.log

        Args:
            func_name: Lambda function name
            logs_output: Log output to save
        """
        import os

        from config import LOGS_DIR

        # Create logs folder if it doesn't exist
        os.makedirs(LOGS_DIR, exist_ok=True)

        # Write logs to centralized logs directory
        log_file_path = os.path.join(LOGS_DIR, f"{func_name}.log")
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(logs_output)

        # Get absolute path for display
        abs_path = os.path.abspath(log_file_path)
        print(f"\n{Colors.CYAN}💾 Logs saved to: {abs_path}{Colors.RESET}")

    def _execute_logs_command(
        self, func_name: str, option: str, query: str = None
    ) -> bool:
        """
        Execute AWS CLI command to get logs based on selected option

        Args:
            func_name: Lambda function name
            option: Log option selected (1-4)
            query: Custom query for filtering (only for option 4)

        Returns:
            True if command executed successfully
        """
        log_group = self._get_log_group_name(func_name)

        # Build base command
        command = ["aws", "logs", "tail", log_group, "--profile", AWS_PROFILE]

        # Add options based on selection
        if option == "1":
            # Logs (last 30 minutes)
            command.extend(["--format", "short", "--since", "30m"])
            log_info(f"Getting logs from the last 30 minutes for {func_name}")
        elif option == "2":
            # Logs (last 5 minutes)
            command.extend(["--format", "short", "--since", "5m"])
            log_info(f"Getting logs with short format for {func_name}")
        elif option == "3":
            # Logs with --follow
            command.extend(["--follow", "--since", "5m"])
            log_info(f"Following logs in real-time for {func_name} (Ctrl+C to stop)")
        elif option == "4":
            # Logs with custom query
            if query:
                command.extend(["--filter-pattern", query, "--since", "30m"])
                log_info(f"Filtering logs with pattern '{query}' for {func_name}")
            else:
                log_error("A query is required for this option")
                return False

        print(f"\n{Colors.CYAN}Executing: {' '.join(command)}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}{'─' * 80}{Colors.RESET}\n")

        # Determine if we should capture output (don't capture for --follow mode)
        capture_output = option != "3"

        try:
            if capture_output:
                # Capture output for saving to file
                result = run_in_project_root(
                    command, check=False, capture_output=True, text=True
                )

                # Display output
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr)

                print(f"\n{Colors.YELLOW}{'─' * 80}{Colors.RESET}")

                # Save to file
                combined_output = result.stdout if result.stdout else ""
                if result.stderr:
                    combined_output += "\n" + result.stderr

                if combined_output.strip():
                    self._save_logs_to_file(func_name, combined_output)

                if result.returncode == 0:
                    log_success("Command executed successfully")
                    return True
                else:
                    log_error(f"Command failed with exit code {result.returncode}")
                    self._log_aws_error_hint(result.stderr)
                    return False
            else:
                # Stream output in real-time for --follow mode
                # We DON'T capture output here to allow real-time streaming to the terminal
                result = run_in_project_root(command, check=False)

                print(f"\n{Colors.YELLOW}{'─' * 80}{Colors.RESET}")

                if result.returncode == 0:
                    log_success("Command executed successfully")
                    print(
                        f"{Colors.YELLOW}Note: --follow mode output not saved to file{Colors.RESET}"
                    )
                    return True
                else:
                    # Command failed (log group doesn't exist, access denied, etc.)
                    log_error(
                        f"Real-time logs failed with exit code {result.returncode}"
                    )
                    self._log_aws_error_hint(
                        "ResourceNotFoundException"
                    )  # Hint for common failure
                    return False

        except subprocess.CalledProcessError as e:
            log_error(f"Error executing command: {e}")
            return False
        except FileNotFoundError:
            log_error("AWS CLI is not installed or not found in PATH")
            log_info("Install with: pip install awscli or brew install awscli")
            return False
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Command interrupted by user{Colors.RESET}")
            return True

    def _log_aws_error_hint(self, stderr: str) -> None:
        """
        Parse AWS error messages and provide helpful hints

        Args:
            stderr: Error output from AWS CLI
        """
        if not stderr:
            return

        stderr_lower = stderr.lower()

        if "resourcenotfoundexception" in stderr_lower or "not found" in stderr_lower:
            log_info(
                f"Hint: Log group may not exist. Check that SERVICE_NAME='{SERVICE_NAME}' "
                f"and SERVERLESS_STAGE='{SERVERLESS_STAGE}' are correct."
            )
        elif "accessdenied" in stderr_lower or "access denied" in stderr_lower:
            log_info(
                f"Hint: Access denied. Check AWS credentials and IAM permissions for "
                f"logs:DescribeLogGroups and logs:FilterLogEvents"
            )
        elif "invalidparameter" in stderr_lower:
            log_info(
                "Hint: Invalid parameter. Check the log group name and filter pattern."
            )

    def _select_log_option_with_fzf(self, func_name: str) -> Optional[str]:
        """
        Use fzf to select a log viewing option

        Args:
            func_name: Lambda function name

        Returns:
            Option number (1-4) or None if cancelled/back
        """
        # Build menu options
        options = []
        option_map = {}  # Map display text to option number

        options.append(f"{Emoji.DOCUMENT} Last 30 minutes")
        option_map[options[-1]] = "1"

        options.append(f"{Emoji.LIST} Last 5 minutes")
        option_map[options[-1]] = "2"

        options.append(f"{Emoji.CIRCULAR}  Real time")
        option_map[options[-1]] = "3"

        options.append(f"{Emoji.SEARCH} Filter logs with custom query")
        option_map[options[-1]] = "4"

        # Create fzf input
        options_text = "\n".join(options)

        try:
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    "40%",
                    "--reverse",
                    "--border",
                    "--prompt",
                    "Select log option: ",
                    "--header",
                    f"Log options for: {func_name}",
                ],
                input=options_text,
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = result.stdout.strip()
                return option_map.get(selected)

            return None

        except FileNotFoundError:
            log_error("fzf is not installed")
            return None
        except KeyboardInterrupt:
            return None
        except Exception as e:
            log_error(f"Error using fzf: {e}")
            return None

    def _show_logs_submenu(self, func_name: str) -> bool:
        """
        Show log options submenu for a specific function using fzf.

        Presents the time-range/mode selector once, executes the chosen option,
        then returns control to the caller (MenuRenderer handles back-navigation).

        Args:
            func_name: Selected Lambda function name

        Returns:
            True when the selected option completes (or user cancels)
        """
        option = self._select_log_option_with_fzf(func_name)

        if option is None or option == "0":
            # User cancelled or pressed ESC — return to parent menu
            return True

        # Execute the selected option
        if option in ["1", "2", "3"]:
            self._execute_logs_command(func_name, option)
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
        elif option == "4":
            # Custom query - prompt for input
            query = input(
                f"\n{Colors.BOLD}Enter filter/query (e.g., ERROR, WARN, etc.): {Colors.RESET}"
            ).strip()
            if query:
                self._execute_logs_command(func_name, option, query)
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            else:
                log_warning("Empty query, operation cancelled")

        return True

    def _select_function_with_fzf(self) -> Optional[str]:
        """
        Use fzf to select a function interactively with fuzzy search

        Returns:
            Selected function name or None if cancelled
        """
        try:
            # Create function list for fzf
            functions_list = "\n".join(GO_FUNCTIONS)

            # Execute fzf with function list
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    "50%",
                    "--reverse",
                    "--border",
                    "--prompt",
                    "🔍 Search function: ",
                    "--header",
                    f"Total: {len(GO_FUNCTIONS)} functions",
                ],
                input=functions_list,
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = result.stdout.strip()
                if selected in GO_FUNCTIONS:
                    return selected

            return None

        except FileNotFoundError:
            log_error("fzf is not installed on the system")
            return None
        except KeyboardInterrupt:
            return None
        except Exception as e:
            log_error(f"Error using fzf: {e}")
            return None

    def _logs_menu(self) -> bool:
        """
        Show logs menu with fzf function selection

        Returns:
            True if executed correctly
        """
        log_header("LOGS MENU - LAMBDA FUNCTIONS")

        while True:
            print(
                f"\n{Colors.BOLD}{Colors.CYAN}🔍 Use fzf to search and select a function{Colors.RESET}"
            )
            print(f"{Colors.CYAN}Press ESC or Ctrl+C to exit{Colors.RESET}\n")

            selected_func = self._select_function_with_fzf()

            if selected_func:
                self._show_logs_submenu(selected_func)
            else:
                log_info("Exiting logs menu")
                break

        return True
