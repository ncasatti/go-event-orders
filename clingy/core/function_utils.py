"""Utility functions for Lambda function management"""

from argparse import Namespace
from typing import List

from config import GO_FUNCTIONS

from clingy.core.logger import log_error, log_info


def resolve_function_list(args: Namespace) -> List[str]:
    """
    Resolve function list from args (supports CLI and interactive modes)

    Args:
        args: Parsed arguments with optional 'function' attribute

    Returns:
        List of function names to process

    Examples:
        >>> # CLI mode with specific function
        >>> args = Namespace(function="status")
        >>> resolve_function_list(args)
        ['status']

        >>> # CLI mode without function (all)
        >>> args = Namespace(function=None)
        >>> resolve_function_list(args)
        ['func1', 'func2', ...]  # All functions from GO_FUNCTIONS
    """
    # CLI mode: specific function via --function flag
    if hasattr(args, "function") and args.function:
        if args.function in GO_FUNCTIONS:
            return [args.function]
        else:
            log_error(f"Function '{args.function}' not found in GO_FUNCTIONS")
            log_info(f"Available: {', '.join(GO_FUNCTIONS[:5])}...")
            return []

    # Default: all functions
    return GO_FUNCTIONS
