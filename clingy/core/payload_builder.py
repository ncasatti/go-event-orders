"""
Interactive multi-snippet payload builder

Allows building Lambda payloads by selecting and combining multiple YAML snippets.
"""

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from core.payload_composer import PayloadComposer, PayloadError

from clingy.core.emojis import Emoji

# ============================================================================
# Simple logging functions (no external dependencies)
# ============================================================================


def log_info(msg: str):
    """Print info message"""
    print(f"ℹ️  {msg}")


def log_success(msg: str):
    """Print success message"""
    print(f"✅ {msg}")


def log_error(msg: str):
    """Print error message"""
    print(f"❌ {msg}")


def log_warning(msg: str):
    """Print warning message"""
    print(f"⚠️  {msg}")


# ============================================================================
# ANSI Colors (simple implementation)
# ============================================================================


class Colors:
    """ANSI color codes"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GREEN = "\033[32m"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class SnippetSelection:
    """A selected snippet with metadata"""

    path: Path
    relative_path: str  # Relative to payloads_dir for display
    order: int  # Selection order (for display)


class PayloadBuilder:
    """
    Interactive payload builder with multi-snippet selection.

    Features:
    - Add snippets from different folders
    - Preview composed payload at any time
    - Remove individual snippets
    - Clear all selections
    - Merge order matters (last selection wins on conflicts)
    """

    def __init__(self, payloads_dir: Path, stage: str):
        """
        Initialize builder.

        Args:
            payloads_dir: Root payloads directory
            stage: Current stage (dev/prod) for base context merging
        """
        self.payloads_dir = Path(payloads_dir)
        self.stage = stage
        self.composer = PayloadComposer(payloads_dir)
        self.selections: List[SnippetSelection] = []

    def build_interactive(self) -> Optional[Path]:
        """
        Interactive builder loop.

        Returns:
            Path to composed payload file (temp file) or None if cancelled
        """
        while True:
            action = self._show_builder_menu()

            if action is None:
                # User cancelled (ESC)
                log_info("Builder cancelled")
                return None

            if action == "add":
                self._add_snippet()
            elif action == "preview":
                self._preview_current()
            elif action == "remove":
                self._remove_snippet()
            elif action == "clear":
                self._clear_all()
            elif action == "done":
                return self._compose_and_save()
            elif action == "cancel":
                log_info("Builder cancelled")
                return None

    def navigate_interactive(self) -> bool:
        """
        Interactive navigator loop (visualization only, no invocation).

        Returns:
            True when user exits
        """
        while True:
            action = self._show_navigator_menu()

            if action is None or action == "exit":
                # User cancelled or selected exit
                log_info("Payload Navigator closed")
                return True

            if action == "add":
                self._add_snippet()
            elif action == "preview":
                self._preview_current()
            elif action == "remove":
                self._remove_snippet()
            elif action == "clear":
                self._clear_all()

    def _show_builder_menu(self) -> Optional[str]:
        """
        Show builder menu with current selections visible.

        Uses fzf --header-lines to display selections as non-selectable header.

        Returns:
            Action string or None if cancelled
        """
        lines = []

        # Header: Current selections (non-selectable)
        if self.selections:
            lines.append("=== Current Selections (merge order) ===")
            for i, sel in enumerate(self.selections, 1):
                lines.append(f"{i}. ✓ {sel.relative_path}")
            lines.append("=" * 50)
        else:
            lines.append("=== No snippets selected yet ===")
            lines.append("=" * 50)

        header_lines_count = len(lines)

        # Actions (selectable)
        actions = []
        actions.append(f"{Emoji.PLUS} Add snippet")

        if self.selections:
            actions.append(f"{Emoji.PREVIEW} Preview payload")
            actions.append(f"{Emoji.SUBTRACT} Remove snippet")
            actions.append(f"{Emoji.TRASH} Clear all")
            actions.append(f"{Emoji.SUCCESS} Done (compose and use)")

        actions.append(f"{Emoji.CANCEL} Cancel")

        lines.extend(actions)

        # Show fzf
        try:
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    "60%",
                    "--reverse",
                    "--border",
                    "--header-lines",
                    str(header_lines_count),
                    "--prompt",
                    "Action: ",
                    "--header",
                    "Payload Builder - Add snippets to compose payload",
                ],
                input="\n".join(lines),
                text=True,
                capture_output=True,
            )

            if result.returncode != 0:
                return None  # Cancelled

            selected = result.stdout.strip()

            # Parse action
            if "Add snippet" in selected:
                return "add"
            elif "Preview" in selected:
                return "preview"
            elif "Remove snippet" in selected:
                return "remove"
            elif "Clear all" in selected:
                return "clear"
            elif "Done" in selected:
                return "done"
            elif "Cancel" in selected:
                return "cancel"

            return None

        except FileNotFoundError:
            log_error("fzf is not installed")
            return None
        except Exception as e:
            log_error(f"Error showing menu: {e}")
            return None

    def _show_navigator_menu(self) -> Optional[str]:
        """
        Show navigator menu (visualization mode - no Done/Invoke option).

        Same as builder menu but with "Exit" instead of "Done".
        Used by Payload Navigator for quick visualization.

        Returns:
            Action string or None if cancelled
        """
        lines = []

        # Header: Current selections (non-selectable)
        if self.selections:
            lines.append("=== Current Selections (merge order) ===")
            for i, sel in enumerate(self.selections, 1):
                lines.append(f"{i}. ✓ {sel.relative_path}")
            lines.append("=" * 50)
        else:
            lines.append("=== No snippets selected yet ===")
            lines.append("=" * 50)

        header_lines_count = len(lines)

        # Actions (selectable) - No "Done", add "Exit" instead
        actions = []
        actions.append(f"{Emoji.PLUS} Add snippet")

        if self.selections:
            actions.append(f"{Emoji.PREVIEW} Preview payload")
            actions.append(f"{Emoji.SUBTRACT} Remove snippet")
            actions.append(f"{Emoji.TRASH} Clear all")

        actions.append(f"{Emoji.EXIT} Exit")

        lines.extend(actions)

        # Show fzf
        try:
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    "60%",
                    "--reverse",
                    "--border",
                    "--header-lines",
                    str(header_lines_count),
                    "--prompt",
                    "Action: ",
                    "--header",
                    "Payload Navigator - Visualize composed payloads",
                ],
                input="\n".join(lines),
                text=True,
                capture_output=True,
            )

            if result.returncode != 0:
                return None  # Cancelled

            selected = result.stdout.strip()

            # Parse action
            if "Add snippet" in selected:
                return "add"
            elif "Preview" in selected:
                return "preview"
            elif "Remove snippet" in selected:
                return "remove"
            elif "Clear all" in selected:
                return "clear"
            elif "Exit" in selected:
                return "exit"

            return None

        except FileNotFoundError:
            log_error("fzf is not installed")
            return None
        except Exception as e:
            log_error(f"Error showing menu: {e}")
            return None

    def _add_snippet(self) -> bool:
        """Navigate folders and select a snippet to add"""
        snippet_path = self._navigate_and_select()

        if snippet_path:
            # Check if already selected
            for sel in self.selections:
                if sel.path == snippet_path:
                    log_warning(f"Snippet already selected: {sel.relative_path}")
                    input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
                    return False

            # Add to selections
            rel_path = str(snippet_path.relative_to(self.payloads_dir))
            order = len(self.selections) + 1
            self.selections.append(
                SnippetSelection(path=snippet_path, relative_path=rel_path, order=order)
            )

            log_success(f"Added snippet {order}: {rel_path}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return True

        return False

    def _navigate_and_select(self) -> Optional[Path]:
        """
        Navigate folders and select a YAML file.

        Returns:
            Selected file path or None if cancelled
        """
        current_path = self.payloads_dir

        while True:
            items = []
            item_map = {}

            # Add back option if not at root
            if current_path != self.payloads_dir:
                back_text = f"{Emoji.BACK}  [BACK] ../"
                items.append(back_text)
                item_map[back_text] = ("back", current_path.parent)

            # List directories and YAML files
            try:
                entries = sorted(current_path.iterdir())

                for entry in entries:
                    # Skip _base and __pycache__
                    if entry.name.startswith("_") or entry.name == "__pycache__":
                        continue

                    if entry.is_dir():
                        display = f"{Emoji.FOLDER} {entry.name}/"
                        items.append(display)
                        item_map[display] = ("folder", entry)

                    elif entry.suffix in [".yaml", ".yml"]:
                        display = f"{Emoji.DOCUMENT} {entry.name}"
                        items.append(display)
                        item_map[display] = ("file", entry)

            except Exception as e:
                log_error(f"Error reading directory: {e}")
                return None

            if not items:
                log_warning("No snippets found in this directory")
                input(f"\n{Colors.CYAN}Press Enter to go back...{Colors.RESET}")
                if current_path == self.payloads_dir:
                    return None
                current_path = current_path.parent
                continue

            # Show fzf
            try:
                rel_path = current_path.relative_to(self.payloads_dir)
                header = f"{Emoji.FILE_LIST} {rel_path if str(rel_path) != '.' else 'payloads/'}"

                result = subprocess.run(
                    [
                        "fzf",
                        "--height",
                        "60%",
                        "--reverse",
                        "--border",
                        "--prompt",
                        "Select: ",
                        "--header",
                        header,
                    ],
                    input="\n".join(items),
                    text=True,
                    capture_output=True,
                )

                if result.returncode != 0:
                    return None  # Cancelled

                selected = result.stdout.strip()
                entry_type, entry_path = item_map.get(selected, (None, None))

                if entry_type == "back":
                    current_path = entry_path
                elif entry_type == "folder":
                    current_path = entry_path
                elif entry_type == "file":
                    return entry_path

            except FileNotFoundError:
                log_error("fzf is not installed")
                return None
            except Exception as e:
                log_error(f"Error: {e}")
                return None

    def _preview_current(self) -> bool:
        """Preview current composed payload"""
        if not self.selections:
            log_warning("No snippets selected yet. Add snippets first.")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return False

        try:
            # Compose payload from current selections
            snippet_paths = [sel.path for sel in self.selections]
            composed = self.composer.compose_from_snippets(snippet_paths, self.stage)

            # Show sources
            print(f"\n{Colors.CYAN}📦 Composed from:{Colors.RESET}")
            for i, source in enumerate(composed.sources, 1):
                try:
                    rel = source.relative_to(Path.cwd())
                except ValueError:
                    rel = source
                print(f"  {i}. {rel}")

            # Show warnings
            if composed.warnings:
                print(f"\n{Colors.YELLOW}⚠️  Warnings:{Colors.RESET}")
                for warning in composed.warnings:
                    print(f"  - {warning}")

            # Validate
            validation = self.composer.validate(composed.data)
            if validation.errors:
                print(f"\n{Colors.RED}❌ Validation Errors:{Colors.RESET}")
                for error in validation.errors:
                    print(f"  - {error}")
            elif validation.warnings:
                print(f"\n{Colors.YELLOW}⚠️  Validation Warnings:{Colors.RESET}")
                for warning in validation.warnings:
                    print(f"  - {warning}")
            else:
                log_success("Payload is valid")

            # Show preview
            print(f"\n{Colors.BOLD}{Colors.CYAN}📄 Payload Preview:{Colors.RESET}")
            print(f"{Colors.YELLOW}{'─' * 60}{Colors.RESET}")
            print(json.dumps(composed.data, indent=2, ensure_ascii=False))
            print(f"{Colors.YELLOW}{'─' * 60}{Colors.RESET}\n")

            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return True

        except PayloadError as e:
            log_error(f"Payload composition failed: {e}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return False

    def _remove_snippet(self) -> bool:
        """Remove a snippet from selections"""
        if not self.selections:
            log_warning("No snippets to remove")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return False

        # Build fzf list
        items = []
        for i, sel in enumerate(self.selections, 1):
            items.append(f"{i}. {sel.relative_path}")

        try:
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    "40%",
                    "--reverse",
                    "--border",
                    "--prompt",
                    "Remove: ",
                    "--header",
                    "Select snippet to remove",
                ],
                input="\n".join(items),
                text=True,
                capture_output=True,
            )

            if result.returncode != 0:
                return False  # Cancelled

            selected = result.stdout.strip()

            # Parse selection (format: "1. path/to/file.yaml")
            index = int(selected.split(".")[0]) - 1
            removed = self.selections.pop(index)

            log_success(f"Removed: {removed.relative_path}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return True

        except (ValueError, IndexError):
            log_error("Invalid selection")
            return False
        except Exception as e:
            log_error(f"Error: {e}")
            return False

    def _clear_all(self) -> bool:
        """Clear all selections"""
        if not self.selections:
            log_warning("No snippets to clear")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return False

        count = len(self.selections)
        self.selections.clear()
        log_success(f"Cleared {count} snippet(s)")
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
        return True

    def _compose_and_save(self) -> Optional[Path]:
        """
        Compose final payload and save to temp file.

        Returns:
            Path to temp file or None if failed
        """
        if not self.selections:
            log_warning("No snippets selected. Cannot compose empty payload.")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return None

        try:
            # Compose
            snippet_paths = [sel.path for sel in self.selections]
            composed = self.composer.compose_from_snippets(snippet_paths, self.stage)

            # Validate
            validation = self.composer.validate(composed.data)
            if validation.errors:
                print(f"\n{Colors.RED}❌ Validation Errors:{Colors.RESET}")
                for error in validation.errors:
                    print(f"  - {error}")
                log_error("Cannot compose: validation failed")
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
                return None

            # Convert body to JSON string if needed (Lambda requirement)
            payload_data = composed.data.copy()
            if "body" in payload_data and isinstance(
                payload_data["body"], (dict, list)
            ):
                payload_data["body"] = json.dumps(
                    payload_data["body"], ensure_ascii=False, separators=(",", ":")
                )

            # Save to temp file
            timestamp = int(time.time() * 1000)
            temp_path = Path(f"/tmp/clingy-payload-{timestamp}.json")

            with open(temp_path, "w") as f:
                json.dump(payload_data, f, indent=2, ensure_ascii=False)

            log_success(f"Payload composed from {len(self.selections)} snippet(s)")
            return temp_path

        except PayloadError as e:
            log_error(f"Composition failed: {e}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return None
        except Exception as e:
            log_error(f"Error saving payload: {e}")
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
            return None
