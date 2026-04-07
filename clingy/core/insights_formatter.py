"""
CloudWatch Insights result formatting

Handles:
- Pretty-print results as tables (using rich)
- Save results to JSON/CSV files
- Format statistics
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from config import FUNCTIONS_DIR

# Try to import rich, fallback to simple formatting if not available
try:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def format_results_table(results: List[List[Dict]], statistics: Dict) -> str:
    """
    Format CloudWatch Insights results as pretty table

    Args:
        results: Query results from get-query-results
        statistics: Query statistics (recordsMatched, bytesScanned, etc.)

    Returns:
        Formatted table string
    """
    if not results:
        return "No results found"

    if RICH_AVAILABLE:
        return _format_with_rich(results, statistics)
    else:
        return _format_simple(results, statistics)


def _format_with_rich(results: List[List[Dict]], statistics: Dict) -> str:
    """Format using rich library (pretty tables)"""
    console = Console()

    # Extract field names from first result
    if not results or not results[0]:
        return "No results found"

    field_names = [item["field"] for item in results[0]]

    # Create table
    table = Table(
        title="📊 Query Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    # Add columns
    for field in field_names:
        table.add_column(field, style="white", no_wrap=False)

    # Add rows
    for row in results:
        values = [item["value"] for item in row]
        table.add_row(*values)

    # Print table to capture output
    with console.capture() as capture:
        console.print(table)

    output = capture.get()

    # Add statistics
    output += "\n\n" + _format_statistics(statistics)

    return output


def _format_simple(results: List[List[Dict]], statistics: Dict) -> str:
    """Fallback formatting without rich (plain text table)"""
    if not results or not results[0]:
        return "No results found"

    # Extract field names (exclude @ptr - it's noise)
    field_names = [item["field"] for item in results[0] if item["field"] != "@ptr"]

    # Calculate column widths with max limit
    MAX_COL_WIDTH = 60  # Prevent columns from being too wide
    col_widths = {}
    for field in field_names:
        col_widths[field] = len(field)

    for row in results:
        for item in row:
            field = item["field"]
            if field == "@ptr":  # Skip @ptr field
                continue
            value = str(item["value"])
            # Limit width to MAX_COL_WIDTH
            col_widths[field] = min(max(col_widths[field], len(value)), MAX_COL_WIDTH)

    # Build table
    output = []

    # Header
    header_parts = []
    separator_parts = []
    for field in field_names:
        width = col_widths[field]
        header_parts.append(field.ljust(width))
        separator_parts.append("-" * width)

    output.append(" | ".join(header_parts))
    output.append("-+-".join(separator_parts))

    # Rows
    for row in results:
        row_parts = []
        for item in row:
            field = item["field"]
            if field == "@ptr":  # Skip @ptr field
                continue
            value = str(item["value"])
            width = col_widths[field]

            # Truncate if too long
            if len(value) > MAX_COL_WIDTH:
                value = value[: MAX_COL_WIDTH - 3] + "..."

            row_parts.append(value.ljust(width))
        output.append(" | ".join(row_parts))

    # Statistics
    output.append("\n" + _format_statistics(statistics))

    return "\n".join(output)


def _format_statistics(statistics: Dict) -> str:
    """Format query statistics"""
    records_matched = statistics.get("recordsMatched", 0)
    records_scanned = statistics.get("recordsScanned", 0)
    bytes_scanned = statistics.get("bytesScanned", 0)

    # Format bytes
    if bytes_scanned >= 1024 * 1024:
        bytes_str = f"{bytes_scanned / (1024 * 1024):.2f} MB"
    elif bytes_scanned >= 1024:
        bytes_str = f"{bytes_scanned / 1024:.2f} KB"
    else:
        bytes_str = f"{bytes_scanned} bytes"

    return f"""Statistics:
  • Records matched: {int(records_matched):,}
  • Records scanned: {int(records_scanned):,}
  • Bytes scanned: {bytes_str}"""


def save_results_yaml(
    results: List[List[Dict]],
    statistics: Dict,
    func_name: str,
    query_name: str = "query",
) -> Optional[Path]:
    """
    Save query results to YAML file (more readable than JSON)

    Args:
        results: Query results
        statistics: Query statistics
        func_name: Function name (for determining save path)
        query_name: Query name (for metadata)

    Returns:
        Path to saved file or None if failed
    """
    try:
        from datetime import datetime

        # Create function folder if it doesn't exist
        func_folder = Path(FUNCTIONS_DIR) / func_name
        func_folder.mkdir(parents=True, exist_ok=True)

        # Convert CloudWatch results format to cleaner structure
        # From: [{"field": "@timestamp", "value": "..."}, ...]
        # To: {"@timestamp": "...", "event": "...", ...}
        clean_results = []
        for row in results:
            clean_row = {}
            for item in row:
                field = item["field"]
                value = item["value"]
                # Skip @ptr field (it's just noise)
                if field != "@ptr":
                    clean_row[field] = value
            clean_results.append(clean_row)

        # Prepare data with metadata
        output_data = {
            "query_metadata": {
                "query_name": query_name,
                "function": func_name,
                "executed_at": datetime.now().isoformat(),
                "records_matched": int(statistics.get("recordsMatched", 0)),
                "records_scanned": int(statistics.get("recordsScanned", 0)),
                "bytes_scanned": statistics.get("bytesScanned", 0),
            },
            "results": clean_results,
        }

        # Write to YAML file
        output_file = func_folder / "insights-result.yaml"

        # Try to use PyYAML if available, otherwise fallback to manual YAML
        try:
            import yaml

            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    output_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
        except ImportError:
            # Manual YAML formatting (fallback)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# CloudWatch Insights Query Results\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                f.write("query_metadata:\n")
                f.write(f"  query_name: {query_name}\n")
                f.write(f"  function: {func_name}\n")
                f.write(f"  executed_at: {datetime.now().isoformat()}\n")
                f.write(f"  records_matched: {int(statistics.get('recordsMatched', 0))}\n")
                f.write(f"  records_scanned: {int(statistics.get('recordsScanned', 0))}\n")
                f.write(f"  bytes_scanned: {statistics.get('bytesScanned', 0)}\n\n")
                f.write("results:\n")
                for row in clean_results:
                    f.write("  - ")
                    items = [f"{k}: {repr(v)}" for k, v in row.items()]
                    f.write("{" + ", ".join(items) + "}\n")

        return output_file.resolve()

    except Exception as e:
        print(f"Error saving results: {e}")
        import traceback

        traceback.print_exc()
        return None


def save_results_csv(results: List[List[Dict]], func_name: str) -> Optional[Path]:
    """
    Save query results to CSV file

    Args:
        results: Query results
        func_name: Function name (for determining save path)

    Returns:
        Path to saved file or None if failed
    """
    try:
        if not results or not results[0]:
            return None

        # Create function folder
        func_folder = Path(FUNCTIONS_DIR) / func_name
        func_folder.mkdir(parents=True, exist_ok=True)

        # Extract field names
        field_names = [item["field"] for item in results[0]]

        # Write CSV
        output_file = func_folder / "insights-result.csv"
        with open(output_file, "w", encoding="utf-8") as f:
            # Header
            f.write(",".join(field_names) + "\n")

            # Rows
            for row in results:
                values = [item["value"].replace(",", ";") for item in row]  # Escape commas
                f.write(",".join(values) + "\n")

        return output_file.resolve()

    except Exception as e:
        print(f"Error saving CSV: {e}")
        return None
