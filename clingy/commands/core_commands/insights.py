"""Interactive CloudWatch Logs Insights menu"""

import json
import os
import subprocess
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import AWS_PROFILE, GO_FUNCTIONS, SERVERLESS_STAGE, SERVICE_NAME
from core.insights_formatter import (
    format_results_table,
    save_results_csv,
    save_results_yaml,
)
from core.insights_queries import (
    PREDEFINED_TEMPLATES,
    delete_query,
    discover_queries,
    format_time_range,
    load_query,
    parse_time_range,
    save_query,
)
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


class InsightsCommand(BaseCommand):
    """CloudWatch Logs Insights queries for Lambda functions"""

    name = "insights"
    help = "Run CloudWatch Insights queries"
    description = (
        "Query and analyze CloudWatch logs using Insights queries with templates and custom queries"
    )
    epilog = """Examples:
  manager.py insights                    # Open interactive insights menu
  manager.py insights -f getArticulos    # Query specific function
"""

    def add_arguments(self, parser: ArgumentParser):
        """Add command-specific arguments"""
        parser.add_argument(
            "-f",
            "--function",
            type=str,
            help="Specific function name (skips target selection)",
        )

    def execute(self, args: Namespace) -> bool:
        """Execute insights command"""
        # If function is pre-selected (from dev menu), skip to action menu
        if hasattr(args, "function") and args.function:
            if args.function in GO_FUNCTIONS:
                return self._show_action_menu([args.function]) or True
            else:
                log_error(f"Function '{args.function}' not found in available functions")
                return False

        # Otherwise, show interactive menu
        return self._insights_menu()

    def get_menu_tree(self) -> MenuNode:
        return super().get_menu_tree()

    # ========================================================================
    # Main Menu Flow
    # ========================================================================

    def _insights_menu(self) -> bool:
        """
        Show main insights menu

        Returns:
            True if executed correctly
        """
        log_header("CLOUDWATCH LOGS INSIGHTS - INTERACTIVE")

        while True:
            print(f"\n{Colors.BOLD}{Colors.CYAN}🔍 Select target for insights query{Colors.RESET}")
            print(f"{Colors.CYAN}Press ESC or Ctrl+C to exit{Colors.RESET}\n")

            # Select target (single, all, multi)
            target_functions = self._select_target_functions()

            if target_functions:
                self._show_action_menu(target_functions)
            else:
                log_info("Exiting insights menu")
                break

        return True

    def _show_action_menu(self, functions: List[str]) -> bool:
        """
        Show action menu for selected functions

        Args:
            functions: Selected function names

        Returns:
            True when exiting submenu
        """
        while True:
            action = self._select_action_with_fzf(functions)

            if action is None or action == "0":
                # User cancelled or selected back
                break

            # Execute the selected action
            if action == "1":
                # Run predefined template
                self._run_predefined_template(functions)
            elif action == "2":
                # Run saved query
                self._run_saved_query(functions)
            elif action == "3":
                # Write custom query (one-time)
                self._run_custom_query(functions, save=False)
            elif action == "4":
                # Create & save new query
                self._run_custom_query(functions, save=True)
            elif action == "5":
                # Manage saved queries
                self._manage_saved_queries(functions)

        return True

    # ========================================================================
    # Target Selection (Single / All / Multi)
    # ========================================================================

    def _select_target_functions(self) -> Optional[List[str]]:
        """
        Select target functions using fzf

        Returns:
            List of selected function names or None if cancelled
        """
        options = {
            f"{Emoji.DOCUMENT} Single function": "single",
            f"{Emoji.STATS} All functions": "all",
            f"{Emoji.PACKAGE} Multiple functions (multi-select)": "multi",
        }

        selected = self._fzf_select(
            list(options.keys()), prompt="Select target: ", header="Choose query target"
        )

        if not selected:
            return None

        target_type = options[selected]

        if target_type == "single":
            func = self._select_function_with_fzf()
            return [func] if func else None

        elif target_type == "all":
            return GO_FUNCTIONS

        elif target_type == "multi":
            return self._select_multiple_functions_with_fzf()

        return None

    # ========================================================================
    # Action Selection
    # ========================================================================

    def _select_action_with_fzf(self, functions: List[str]) -> Optional[str]:
        """
        Use fzf to select an action

        Args:
            functions: Selected function names

        Returns:
            Action number or None if cancelled
        """
        func_display = (
            ", ".join(functions) if len(functions) <= 3 else f"{len(functions)} functions"
        )

        options = []
        action_map = {}

        options.append(f"{Emoji.DOCUMENT} Run predefined template query")
        action_map[options[-1]] = "1"

        options.append(f"{Emoji.FLOPPY} Run saved query")
        action_map[options[-1]] = "2"

        options.append(f"{Emoji.PENCIL} Write custom query (one-time)")
        action_map[options[-1]] = "3"

        options.append(f"{Emoji.PLUS} Create & save new query")
        action_map[options[-1]] = "4"

        options.append(f"{Emoji.TRASH} Manage saved queries")
        action_map[options[-1]] = "5"

        options.append(f"{Emoji.EXIT} Back")
        action_map[options[-1]] = "0"

        selected = self._fzf_select(
            options,
            prompt="Select action: ",
            header=f"Insights menu for: {func_display}",
        )

        return action_map.get(selected) if selected else None

    # ========================================================================
    # Query Execution Flows
    # ========================================================================

    def _run_predefined_template(self, functions: List[str]) -> bool:
        """Run a predefined template query"""
        # Select template
        template_options = [f"{template['name']}" for template in PREDEFINED_TEMPLATES.values()]

        selected = self._fzf_select(
            template_options,
            prompt="Select template: ",
            header="Predefined query templates",
        )

        if not selected:
            return False

        # Find template by name
        template = None
        template_key = None
        for key, tmpl in PREDEFINED_TEMPLATES.items():
            if tmpl["name"] == selected:
                template = tmpl
                template_key = key
                break

        if not template:
            log_error("Template not found")
            return False

        # Select time range
        time_range = self._select_time_range_with_fzf(default=template.get("time_range", "30m"))
        if not time_range:
            return False

        # Execute query
        return self._execute_query(
            functions=functions,
            query_string=template["query"],
            query_name=template["name"],
            time_range=time_range,
        )

    def _run_saved_query(self, functions: List[str]) -> bool:
        """Run a saved query from file"""
        # Discover queries (only from first function if multiple selected)
        func_name = functions[0] if len(functions) == 1 else None
        queries = discover_queries(func_name)

        if not queries:
            log_warning("No saved queries found")
            log_info(
                f"Create queries in: insights-queries/ (global) or functions/<name>/queries/ (local)"
            )
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return False

        # Build fzf options with labels
        display_items = []
        query_map = {}

        for query_path, label in queries:
            filename = os.path.basename(query_path).replace(".query", "")
            display_text = f"[{label:^7}] {filename}"
            display_items.append(display_text)
            query_map[display_text] = query_path

        selected = self._fzf_select(
            display_items,
            prompt="Select query: ",
            header=f"Shared: {sum(1 for _, l in queries if l == 'SHARED')} | Local: {sum(1 for _, l in queries if l == 'LOCAL')}",
        )

        if not selected or selected not in query_map:
            return False

        # Load query
        query_path = query_map[selected]
        query_data = load_query(query_path)

        if not query_data:
            log_error(f"Failed to load query: {query_path}")
            return False

        # Select time range (use query default)
        time_range = self._select_time_range_with_fzf(default=query_data.get("time_range", "30m"))
        if not time_range:
            return False

        # Execute query
        return self._execute_query(
            functions=functions,
            query_string=query_data["query"],
            query_name=query_data.get("name", os.path.basename(query_path)),
            time_range=time_range,
        )

    def _run_custom_query(self, functions: List[str], save: bool = False) -> bool:
        """
        Write and execute a custom query

        Args:
            functions: Target functions
            save: If True, save the query to file
        """
        print(f"\n{Colors.BOLD}{Colors.YELLOW}✏️  Write Custom Query{Colors.RESET}\n")

        # Get query string from user (multiline input or editor)
        query_string = self._get_custom_query_input()
        if not query_string:
            log_warning("Empty query, operation cancelled")
            return False

        # Get time range
        time_range = self._select_time_range_with_fzf(default="30m")
        if not time_range:
            return False

        # If save=True, prompt for metadata
        if save:
            name = input(f"{Colors.BOLD}Query name: {Colors.RESET}").strip()
            if not name:
                log_warning("Empty name, query not saved")
                return False

            description = input(f"{Colors.BOLD}Description (optional): {Colors.RESET}").strip()

            # Ask if global or function-specific
            save_location = self._select_save_location(functions)
            if not save_location:
                return False

            # Save query
            func_name = save_location if save_location != "GLOBAL" else None
            saved_path = save_query(
                name=name,
                description=description,
                time_range=time_range,
                query=query_string,
                func_name=func_name,
                target="single" if len(functions) == 1 else "multi",
            )

            if saved_path:
                log_success(f"Query saved to: {saved_path}")
            else:
                log_error("Failed to save query")

        # Execute query
        return self._execute_query(
            functions=functions,
            query_string=query_string,
            query_name="Custom Query",
            time_range=time_range,
        )

    def _manage_saved_queries(self, functions: List[str]) -> bool:
        """Manage (view/delete) saved queries"""
        func_name = functions[0] if len(functions) == 1 else None
        queries = discover_queries(func_name)

        if not queries:
            log_warning("No saved queries found")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return False

        # Build fzf options
        display_items = []
        query_map = {}

        for query_path, label in queries:
            filename = os.path.basename(query_path).replace(".query", "")
            display_text = f"[{label:^7}] {filename}"
            display_items.append(display_text)
            query_map[display_text] = query_path

        display_items.append(f"{Emoji.EXIT} Back")

        selected = self._fzf_select(
            display_items,
            prompt="Select query to manage: ",
            header="Saved queries (select to view/delete)",
        )

        if not selected or Emoji.EXIT in selected:
            return False

        query_path = query_map[selected]

        # Show query details and ask to delete
        query_data = load_query(query_path)
        if query_data:
            print(f"\n{Colors.BOLD}{Colors.CYAN}Query Details:{Colors.RESET}")
            print(f"  Name: {query_data.get('name', 'N/A')}")
            print(f"  Description: {query_data.get('description', 'N/A')}")
            print(f"  Time range: {query_data.get('time_range', 'N/A')}")
            print(f"  File: {query_path}")
            print(f"\n{Colors.BOLD}Query:{Colors.RESET}")
            print(query_data["query"])

        confirm = (
            input(f"\n{Colors.YELLOW}Delete this query? (y/N): {Colors.RESET}").strip().lower()
        )
        if confirm == "y":
            if delete_query(query_path):
                log_success(f"Query deleted: {query_path}")
            else:
                log_error("Failed to delete query")

        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
        return True

    # ========================================================================
    # Query Execution
    # ========================================================================

    def _execute_query(
        self, functions: List[str], query_string: str, query_name: str, time_range: str
    ) -> bool:
        """
        Execute CloudWatch Insights query

        Args:
            functions: Target function names
            query_string: CloudWatch Insights query
            query_name: Query name (for display/saving)
            time_range: Time range string (e.g., "1h")

        Returns:
            True if executed successfully
        """
        try:
            # Parse time range
            start_time, end_time = parse_time_range(time_range)

            # Build log group names
            log_groups = [
                f"/aws/lambda/{SERVICE_NAME}-{SERVERLESS_STAGE}-{func}" for func in functions
            ]

            log_info(f"Executing query: {query_name}")
            log_info(f"Time range: {format_time_range(time_range)}")
            log_info(f"Target: {len(log_groups)} log group(s)")

            # Start query
            query_id = self._start_query(log_groups, query_string, start_time, end_time)
            if not query_id:
                log_error("Failed to start query")
                return False

            print(f"\n{Colors.CYAN}Query ID: {query_id}{Colors.RESET}")

            # Poll for results
            result_data = self._poll_query_results(query_id)
            if not result_data:
                log_error("Failed to get query results")
                return False

            # Format and display results
            results = result_data.get("results", [])
            statistics = result_data.get("statistics", {})

            print(f"\n{Colors.YELLOW}{'─' * 80}{Colors.RESET}\n")

            if results:
                formatted = format_results_table(results, statistics)
                print(formatted)

                # Save results (only for single function)
                if len(functions) == 1:
                    saved_file = save_results_yaml(
                        results=results,
                        statistics=statistics,
                        func_name=functions[0],
                        query_name=query_name,
                    )
                    if saved_file:
                        print(
                            f"\n{Colors.CYAN}💾 Results saved to: {Colors.BOLD}{saved_file}{Colors.RESET}"
                        )
            else:
                log_warning("No results found")

            print(f"\n{Colors.YELLOW}{'─' * 80}{Colors.RESET}")

            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return True

        except ValueError as e:
            log_error(f"Invalid time range: {e}")
            return False
        except Exception as e:
            log_error(f"Error executing query: {e}")
            return False

    def _start_query(
        self, log_groups: List[str], query_string: str, start_time: int, end_time: int
    ) -> Optional[str]:
        """
        Start CloudWatch Insights query

        Returns:
            Query ID or None if failed
        """
        try:
            command = (
                [
                    "aws",
                    "logs",
                    "start-query",
                    "--profile",
                    AWS_PROFILE,
                    "--log-group-names",
                ]
                + log_groups
                + [
                    "--start-time",
                    str(start_time),
                    "--end-time",
                    str(end_time),
                    "--query-string",
                    query_string,
                    "--query",
                    "queryId",
                    "--output",
                    "text",
                ]
            )

            result = run_in_project_root(command, capture_output=True, text=True, check=False)

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            log_error(f"AWS CLI error: {result.stderr}")
            return None

        except Exception as e:
            log_error(f"Error starting query: {e}")
            return None

    def _poll_query_results(self, query_id: str, max_wait: int = 60) -> Optional[Dict]:
        """
        Poll CloudWatch Insights query results until complete

        Args:
            query_id: Query ID from start-query
            max_wait: Max seconds to wait

        Returns:
            Query results dict or None if failed/timeout
        """
        elapsed = 0
        poll_interval = 2

        while elapsed < max_wait:
            try:
                command = [
                    "aws",
                    "logs",
                    "get-query-results",
                    "--profile",
                    AWS_PROFILE,
                    "--query-id",
                    query_id,
                    "--output",
                    "json",
                ]

                result = run_in_project_root(command, capture_output=True, text=True, check=False)

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    status = data.get("status")

                    if status == "Complete":
                        log_success("Query complete!")
                        return data
                    elif status in ["Failed", "Cancelled"]:
                        log_error(f"Query {status}")
                        return None
                    else:
                        # Still running
                        print(f"{Colors.YELLOW}⏳ Query running... ({elapsed}s){Colors.RESET}")

                time.sleep(poll_interval)
                elapsed += poll_interval

            except Exception as e:
                log_error(f"Error polling results: {e}")
                return None

        log_error(f"Query timed out after {max_wait}s")
        return None

    # ========================================================================
    # Helper: Time Range Selection
    # ========================================================================

    def _select_time_range_with_fzf(self, default: str = "30m") -> Optional[str]:
        """
        Select time range using fzf

        Args:
            default: Default time range

        Returns:
            Time range string or None if cancelled
        """
        presets = {
            "⚡ Last 5 minutes": "5m",
            "🕐 Last 15 minutes": "15m",
            "🕐 Last 30 minutes": "30m",
            "🕐 Last 1 hour": "1h",
            "🕐 Last 3 hours": "3h",
            "🕐 Last 6 hours": "6h",
            "🕐 Last 12 hours": "12h",
            "🕐 Last 24 hours": "24h",
            "🕐 Last 7 days": "7d",
            "✏️  Custom range": "custom",
        }

        selected = self._fzf_select(
            list(presets.keys()),
            prompt="Select time range: ",
            header=f"Default: {format_time_range(default)}",
        )

        if not selected:
            return None

        time_str = presets[selected]

        if time_str == "custom":
            time_str = input(
                f"{Colors.BOLD}Enter time range (e.g., 2h, 45m, 3d): {Colors.RESET}"
            ).strip()
            if not time_str:
                return None

        return time_str

    # ========================================================================
    # Helper: Custom Query Input
    # ========================================================================

    def _get_custom_query_input(self) -> Optional[str]:
        """Get custom query from user (multiline input)"""
        print(
            f"{Colors.CYAN}Enter your CloudWatch Insights query (end with Ctrl+D or empty line):{Colors.RESET}\n"
        )

        lines = []
        try:
            while True:
                line = input()
                if not line and lines:  # Empty line after content = done
                    break
                lines.append(line)
        except EOFError:
            # Ctrl+D pressed
            pass

        query = "\n".join(lines).strip()
        return query if query else None

    # ========================================================================
    # Helper: Save Location Selection
    # ========================================================================

    def _select_save_location(self, functions: List[str]) -> Optional[str]:
        """
        Select where to save query (global or function-specific)

        Returns:
            "GLOBAL" or function name, or None if cancelled
        """
        if len(functions) == 1:
            options = {
                f"{Emoji.STATS} Global (insights-queries/)": "GLOBAL",
                f"{Emoji.DOCUMENT} Function-specific (functions/{functions[0]}/queries/)": functions[
                    0
                ],
            }
        else:
            # Multiple functions = only global
            return "GLOBAL"

        selected = self._fzf_select(
            list(options.keys()),
            prompt="Save location: ",
            header="Choose where to save query",
        )

        return options[selected] if selected else None

    # ========================================================================
    # FZF Utilities
    # ========================================================================

    def _fzf_select(
        self, options: List[str], prompt: str = "Select: ", header: str = ""
    ) -> Optional[str]:
        """Generic fzf selector"""
        try:
            options_text = "\n".join(options)

            cmd = [
                "fzf",
                "--height",
                "50%",
                "--reverse",
                "--border",
                "--prompt",
                prompt,
            ]

            if header:
                cmd.extend(["--header", header])

            result = subprocess.run(cmd, input=options_text, text=True, capture_output=True)

            if result.returncode == 0:
                return result.stdout.strip()

            return None

        except FileNotFoundError:
            log_error("fzf is not installed")
            return None
        except KeyboardInterrupt:
            return None
        except Exception as e:
            log_error(f"Error using fzf: {e}")
            return None

    def _select_function_with_fzf(self) -> Optional[str]:
        """Select single function with fzf"""
        return self._fzf_select(
            GO_FUNCTIONS,
            prompt="🔍 Search function: ",
            header=f"Total: {len(GO_FUNCTIONS)} functions",
        )

    def _select_multiple_functions_with_fzf(self) -> Optional[List[str]]:
        """Select multiple functions with fzf (TAB to select)"""
        try:
            result = subprocess.run(
                [
                    "fzf",
                    "--multi",
                    "--height",
                    "50%",
                    "--reverse",
                    "--border",
                    "--prompt",
                    "🔍 Select functions (TAB to select, ENTER to confirm): ",
                    "--header",
                    f"Total: {len(GO_FUNCTIONS)} | TAB=toggle",
                ],
                input="\n".join(GO_FUNCTIONS),
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = [
                    line.strip() for line in result.stdout.strip().split("\n") if line.strip()
                ]
                return selected if selected else None

            return None

        except Exception as e:
            log_error(f"Error using fzf: {e}")
            return None
