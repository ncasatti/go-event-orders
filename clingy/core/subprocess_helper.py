"""
Subprocess execution helper for running commands from PROJECT_ROOT.

This ensures that external tools (serverless, aws, go) always run from the
correct directory regardless of where clingy is invoked from.
"""

import subprocess
from typing import Any, List

from config import PROJECT_ROOT


def run_in_project_root(command: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """
    Execute subprocess command from PROJECT_ROOT.

    This ensures external tools (serverless, aws, go) run from the correct
    directory where serverless.yml, functions/, and other project files exist.

    Args:
        command: List of command and arguments (e.g., ["serverless", "invoke", ...])
        **kwargs: Additional arguments for subprocess.run()

    Returns:
        CompletedProcess instance from subprocess.run()

    Example:
        >>> result = run_in_project_root(
        ...     ["serverless", "invoke", "--function", "myFunc"],
        ...     capture_output=True,
        ...     text=True
        ... )

    Note:
        - cwd is set to PROJECT_ROOT by default
        - You can override with kwargs: run_in_project_root(cmd, cwd="/custom/path")
        - PROJECT_ROOT is imported from config.py
    """
    # Set cwd to PROJECT_ROOT (unless explicitly overridden)
    kwargs.setdefault("cwd", PROJECT_ROOT)

    return subprocess.run(command, **kwargs)
