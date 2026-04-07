"""Logs menu - View and Insights for Lambda logs"""

from argparse import ArgumentParser, Namespace

from commands.core_commands.insights import InsightsCommand
from commands.core_commands.logs import LogsCommand
from config import GO_FUNCTIONS

from clingy.commands.base import BaseCommand
from clingy.core.emojis import Emoji
from clingy.core.logger import log_info, log_section
from clingy.core.menu import MenuNode, fzf_select_items


class LogsMenuCommand(BaseCommand):
    """View and analyze Lambda function logs"""

    name = "logs"
    help = "View Lambda logs"
    description = "View CloudWatch logs and run Insights queries"

    def execute(self, args: Namespace) -> bool:
        """Execute logs command (not used in interactive mode)"""
        log_info("Use interactive menu to view logs")
        return True

    def add_arguments(self, parser: ArgumentParser):
        return super().add_arguments(parser)

    def get_menu_tree(self) -> MenuNode:
        """Interactive menu for logs management"""
        return MenuNode(
            label="Logs & Monitoring",
            emoji=Emoji.SEARCH,
            children=[
                MenuNode(
                    label="View Logs",
                    emoji=Emoji.LOG,
                    action=self._view_logs,
                ),
                MenuNode(
                    label="CloudWatch Insights",
                    emoji=Emoji.STATS,
                    children=[
                        MenuNode(
                            label="Run Insights Query",
                            action=self._run_insights,
                        ),
                    ],
                ),
            ],
        )

    # ========================================================================
    # View Logs Actions
    # ========================================================================

    def _view_logs(self) -> bool:
        """Select a function and open the logs submenu"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select function to view logs: ",
            include_all=False,
        )
        if not functions:
            log_info("No function selected")
            return False

        func = functions[0]  # Single selection
        log_section(f"VIEW LOGS - {func}")
        logs_cmd = LogsCommand()
        return logs_cmd.execute(Namespace(function=func))

    # ========================================================================
    # Insights Actions
    # ========================================================================

    def _run_insights(self) -> bool:
        """Run CloudWatch Insights query"""
        log_section("CLOUDWATCH INSIGHTS")
        insights_cmd = InsightsCommand()
        # Use interactive mode (no function specified)
        return insights_cmd.execute(Namespace(function=None, query=None))
