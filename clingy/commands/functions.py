"""Functions menu - Build, Zip, Deploy, Clean Lambda functions"""

from argparse import ArgumentParser, Namespace
from typing import Optional

from commands.core_commands.build import BuildCommand
from commands.core_commands.clean import CleanCommand
from commands.core_commands.deploy import DeployCommand
from commands.core_commands.zip import ZipCommand
from config import GO_FUNCTIONS

from clingy.commands.base import BaseCommand
from clingy.core.emojis import Emoji
from clingy.core.logger import log_error, log_info, log_section, log_success
from clingy.core.menu import MenuNode, fzf_select_items


class FunctionsCommand(BaseCommand):
    """Manage Lambda functions (Build, Zip, Deploy, Clean)"""

    name = "functions"
    help = "Manage Lambda functions"
    description = "Build, zip, deploy, and clean Go Lambda functions"

    def execute(self, args: Namespace) -> bool:
        """Execute functions command (not used in interactive mode)"""
        log_info("Use interactive menu to manage functions")
        return True

    def add_arguments(self, parser: ArgumentParser):
        return super().add_arguments(parser)

    def get_menu_tree(self) -> MenuNode:
        """Interactive menu for functions management"""
        return MenuNode(
            label="Functions",
            emoji=Emoji.LAMBDA,
            children=[
                MenuNode(
                    label="Build Functions",
                    emoji=Emoji.BUILD,
                    children=[
                        MenuNode(
                            label="Build All",
                            action=self._build_all,
                        ),
                        MenuNode(
                            label="Select Functions to Build",
                            action=self._build_selected,
                        ),
                    ],
                ),
                MenuNode(
                    label="Zip Functions",
                    emoji=Emoji.ZIP,
                    children=[
                        MenuNode(
                            label="Zip All",
                            action=self._zip_all,
                        ),
                        MenuNode(
                            label="Select Functions to Zip",
                            action=self._zip_selected,
                        ),
                    ],
                ),
                MenuNode(
                    label="Deploy Functions",
                    emoji=Emoji.DEPLOY,
                    children=[
                        MenuNode(
                            label="Deploy All",
                            action=self._deploy_all,
                        ),
                        MenuNode(
                            label="Select Functions to Deploy",
                            action=self._deploy_selected,
                        ),
                    ],
                ),
                MenuNode(
                    label="Full Pipeline (Build → Zip → Deploy)",
                    emoji=Emoji.ALL,
                    children=[
                        MenuNode(
                            label="Full Pipeline - All Functions",
                            action=self._full_pipeline_all,
                        ),
                        MenuNode(
                            label="Full Pipeline - Select Functions",
                            action=self._full_pipeline_selected,
                        ),
                    ],
                ),
                MenuNode(
                    label="Clean Build Artifacts",
                    emoji=Emoji.TRASH,
                    children=[
                        MenuNode(
                            label="Clean All",
                            action=self._clean_all,
                        ),
                        MenuNode(
                            label="Select Functions to Clean",
                            action=self._clean_selected,
                        ),
                    ],
                ),
            ],
        )

    # ========================================================================
    # Build Actions
    # ========================================================================

    def _build_all(self) -> bool:
        """Build all functions"""
        log_section("BUILD ALL FUNCTIONS")
        build_cmd = BuildCommand()
        return build_cmd.execute(Namespace(function=None))

    def _build_selected(self) -> bool:
        """Build selected functions"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select functions to build: ",
            include_all=False,
        )
        if not functions:
            log_info("No functions selected")
            return False

        log_section(f"BUILD {len(functions)} FUNCTIONS")
        build_cmd = BuildCommand()
        success = True
        for func in functions:
            if not build_cmd.execute(Namespace(function=func)):
                success = False
        return success

    # ========================================================================
    # Zip Actions
    # ========================================================================

    def _zip_all(self) -> bool:
        """Zip all functions"""
        log_section("ZIP ALL FUNCTIONS")
        zip_cmd = ZipCommand()
        return zip_cmd.execute(Namespace(function=None))

    def _zip_selected(self) -> bool:
        """Zip selected functions"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select functions to zip: ",
            include_all=False,
        )
        if not functions:
            log_info("No functions selected")
            return False

        log_section(f"ZIP {len(functions)} FUNCTIONS")
        zip_cmd = ZipCommand()
        success = True
        for func in functions:
            if not zip_cmd.execute(Namespace(function=func)):
                success = False
        return success

    # ========================================================================
    # Deploy Actions
    # ========================================================================

    def _deploy_all(self) -> bool:
        """Deploy all functions"""
        log_section("DEPLOY ALL FUNCTIONS")
        deploy_cmd = DeployCommand()
        return deploy_cmd.execute(Namespace(function=None, skip_build=False))

    def _deploy_selected(self) -> bool:
        """Deploy selected functions"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select functions to deploy: ",
            include_all=False,
        )
        if not functions:
            log_info("No functions selected")
            return False

        log_section(f"DEPLOY {len(functions)} FUNCTIONS")
        deploy_cmd = DeployCommand()
        success = True
        for func in functions:
            if not deploy_cmd.execute(Namespace(function=func, skip_build=False)):
                success = False
        return success

    # ========================================================================
    # Full Pipeline Actions
    # ========================================================================

    def _full_pipeline_all(self) -> bool:
        """Run full pipeline (Build → Zip → Deploy) for all functions"""
        log_section("FULL PIPELINE - ALL FUNCTIONS")

        # Build
        log_info("Step 1/3: Building...")
        build_cmd = BuildCommand()
        if not build_cmd.execute(Namespace(function=None)):
            log_error("Build failed, aborting pipeline")
            return False

        # Zip
        log_info("Step 2/3: Zipping...")
        zip_cmd = ZipCommand()
        if not zip_cmd.execute(Namespace(function=None)):
            log_error("Zip failed, aborting pipeline")
            return False

        # Deploy
        log_info("Step 3/3: Deploying...")
        deploy_cmd = DeployCommand()
        if not deploy_cmd.execute(Namespace(function=None, skip_build=True)):
            log_error("Deploy failed")
            return False

        log_success("Full pipeline completed successfully")
        return True

    def _full_pipeline_selected(self) -> bool:
        """Run full pipeline (Build → Zip → Deploy) for selected functions"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select functions for full pipeline: ",
            include_all=False,
        )
        if not functions:
            log_info("No functions selected")
            return False

        log_section(f"FULL PIPELINE - {len(functions)} FUNCTIONS")

        build_cmd = BuildCommand()
        zip_cmd = ZipCommand()
        deploy_cmd = DeployCommand()

        success = True
        for func in functions:
            log_info(f"Processing {func}...")

            # Build
            if not build_cmd.execute(Namespace(function=func)):
                log_error(f"Build failed for {func}, skipping")
                success = False
                continue

            # Zip
            if not zip_cmd.execute(Namespace(function=func)):
                log_error(f"Zip failed for {func}, skipping")
                success = False
                continue

            # Deploy
            if not deploy_cmd.execute(Namespace(function=func, skip_build=True)):
                log_error(f"Deploy failed for {func}")
                success = False

        if success:
            log_success("Full pipeline completed successfully")
        return success

    # ========================================================================
    # Clean Actions
    # ========================================================================

    def _clean_all(self) -> bool:
        """Clean all build artifacts"""
        log_section("CLEAN ALL BUILD ARTIFACTS")
        clean_cmd = CleanCommand()
        return clean_cmd.execute(Namespace(function=None))

    def _clean_selected(self) -> bool:
        """Clean selected functions"""
        functions = fzf_select_items(
            items=GO_FUNCTIONS,
            prompt="Select functions to clean: ",
            include_all=False,
        )
        if not functions:
            log_info("No functions selected")
            return False

        log_section(f"CLEAN {len(functions)} FUNCTIONS")
        clean_cmd = CleanCommand()
        success = True
        for func in functions:
            if not clean_cmd.execute(Namespace(function=func)):
                success = False
        return success
