"""Invoke menu - Local and Remote Lambda invocation with payload composer"""

from argparse import ArgumentParser, Namespace

from commands.core_commands.invoke import InvokeCommand
from config import GO_FUNCTIONS

from clingy.commands.base import BaseCommand
from clingy.core.colors import Colors
from clingy.core.emojis import Emoji
from clingy.core.logger import log_error, log_info, log_section, log_success
from clingy.core.menu import MenuNode, fzf_select_items


class InvokeMenuCommand(BaseCommand):
    """Invoke Lambda functions locally or remotely"""

    name = "invoke"
    help = "Invoke Lambda functions"
    description = "Invoke Lambda functions locally or remotely with composable payloads"

    def execute(self, args: Namespace) -> bool:
        """Execute invoke command (not used in interactive mode)"""
        log_info("Use interactive menu to invoke functions")
        return True

    def add_arguments(self, parser: ArgumentParser):
        return super().add_arguments(parser)

    def get_menu_tree(self) -> MenuNode:
        """Interactive menu for function invocation"""
        return MenuNode(
            label="Invoke Functions",
            emoji=Emoji.RUN,
            children=[
                MenuNode(
                    label="Local Invocation",
                    emoji=Emoji.COMPUTER,
                    action=self._invoke_local_flow,
                ),
                MenuNode(
                    label="Remote Invocation (AWS)",
                    emoji=Emoji.CLOUD,
                    action=self._invoke_remote_flow,
                ),
                MenuNode(
                    label="Payload Navigator",
                    emoji=Emoji.DOCUMENT,
                    action=self._browse_payloads,
                ),
            ],
        )

    # ========================================================================
    # Local Invocation Actions
    # ========================================================================

    def _invoke_local_flow(self) -> bool:
        """Local invocation flow: select function → build payload → invoke"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select function to invoke locally: ",
            include_all=False,
        )
        if not functions:
            log_info("No function selected")
            return False

        func = functions[0]
        invoke_cmd = InvokeCommand()
        return invoke_cmd.invoke_with_builder(func, is_local=True)

    # ========================================================================
    # Remote Invocation Actions
    # ========================================================================

    def _invoke_remote_flow(self) -> bool:
        """Remote invocation flow: select function → build payload → invoke"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select function to invoke remotely: ",
            include_all=False,
        )
        if not functions:
            log_info("No function selected")
            return False

        func = functions[0]
        invoke_cmd = InvokeCommand()
        return invoke_cmd.invoke_with_builder(func, is_local=False)

    # ========================================================================
    # Payload Navigator Actions
    # ========================================================================

    def _browse_payloads(self) -> bool:
        """Browse and preview composed payloads without invoking"""
        from pathlib import Path

        from config import PAYLOAD_DEFAULT_STAGE, PAYLOADS_DIR
        from core.payload_builder import PayloadBuilder

        log_section("PAYLOAD NAVIGATOR")
        log_info("Quick payload visualization (no invocation)")

        # Create builder in navigator mode
        builder = PayloadBuilder(Path(PAYLOADS_DIR), PAYLOAD_DEFAULT_STAGE)

        # Run navigator loop (Add/Preview/Remove/Clear/Exit)
        return builder.navigate_interactive()
