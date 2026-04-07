"""
CloudWatch Insights query management

Handles:
- Predefined query templates
- Query file discovery (global + function-specific)
- Query file loading/saving
- Time range parsing
"""

import glob
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import FUNCTIONS_DIR

# ============================================================================
# Predefined Query Templates
# ============================================================================

PREDEFINED_TEMPLATES = {
    "errors": {
        "name": "🔴 Recent Errors",
        "description": "Find all ERROR and Exception messages",
        "time_range": "30m",
        "query": """fields @timestamp, @message, @requestId
| filter @message like /ERROR/ or @message like /Exception/
| sort @timestamp desc
| limit 50""",
    },
    "performance": {
        "name": "⚡ Performance Stats",
        "description": "Analyze duration and memory usage",
        "time_range": "1h",
        "query": """fields @timestamp, @duration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| stats avg(@duration) as avg_ms,
        pct(@duration, 50) as p50_ms,
        pct(@duration, 95) as p95_ms,
        pct(@duration, 99) as p99_ms,
        max(@duration) as max_ms,
        avg(@maxMemoryUsed) as avg_memory_mb""",
    },
    "cold_starts": {
        "name": "🥶 Cold Starts",
        "description": "Find all cold starts with init duration",
        "time_range": "24h",
        "query": """fields @timestamp, @initDuration, @duration, @requestId
| filter @type = "REPORT" and ispresent(@initDuration)
| sort @initDuration desc
| limit 50""",
    },
    "slow_requests": {
        "name": "🐌 Slowest Requests",
        "description": "Top 20 slowest requests",
        "time_range": "1h",
        "query": """fields @timestamp, @duration, @requestId, @message
| filter @type = "REPORT"
| sort @duration desc
| limit 20""",
    },
    "error_rate_hourly": {
        "name": "📊 Error Rate by Hour",
        "description": "Count errors grouped by hour",
        "time_range": "24h",
        "query": """fields @timestamp
| filter @message like /ERROR/
| stats count(*) as error_count by bin(1h)
| sort bin(1h) desc""",
    },
    "memory_usage": {
        "name": "💾 Memory Usage Stats",
        "description": "Memory usage percentiles",
        "time_range": "1h",
        "query": """fields @maxMemoryUsed, @memorySize
| filter @type = "REPORT"
| stats avg(@maxMemoryUsed) as avg_mb,
        pct(@maxMemoryUsed, 50) as p50_mb,
        pct(@maxMemoryUsed, 95) as p95_mb,
        max(@maxMemoryUsed) as max_mb,
        max(@memorySize) as allocated_mb""",
    },
}


# ============================================================================
# Query File Management
# ============================================================================

GLOBAL_QUERIES_DIR = "insights-queries"


def ensure_queries_dir(func_name: Optional[str] = None) -> Path:
    """
    Ensure queries directory exists

    Args:
        func_name: Function name (creates function-specific dir if provided)

    Returns:
        Path to queries directory
    """
    if func_name:
        # Function-specific queries
        queries_dir = Path(FUNCTIONS_DIR) / func_name / "queries"
    else:
        # Global queries
        queries_dir = Path(GLOBAL_QUERIES_DIR)

    queries_dir.mkdir(parents=True, exist_ok=True)
    return queries_dir


def discover_queries(func_name: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Discover all query files (global + function-specific)

    Args:
        func_name: Function name (optional, if provided also searches function-specific)

    Returns:
        List of tuples: (query_path, label) where label is "SHARED" or "LOCAL"
    """
    queries = []

    # 1. Discover GLOBAL queries from insights-queries/
    global_dir = GLOBAL_QUERIES_DIR
    if os.path.isdir(global_dir):
        pattern = os.path.join(global_dir, "*.query")
        global_queries = sorted(glob.glob(pattern))
        for query_path in global_queries:
            queries.append((query_path, "SHARED"))

    # 2. Discover LOCAL queries from functions/{function}/queries/
    if func_name:
        local_dir = os.path.join(FUNCTIONS_DIR, func_name, "queries")
        if os.path.isdir(local_dir):
            pattern = os.path.join(local_dir, "*.query")
            local_queries = sorted(glob.glob(pattern))
            for query_path in local_queries:
                queries.append((query_path, "LOCAL"))

    return queries


def load_query(query_path: str) -> Optional[Dict]:
    """
    Load a query from file

    Args:
        query_path: Path to .query file

    Returns:
        {
            "name": "...",
            "description": "...",
            "time_range": "1h",
            "target": "single",
            "query": "fields @timestamp..."
        }
    """
    if not os.path.exists(query_path):
        return None

    try:
        with open(query_path, "r") as f:
            content = f.read()

        # Parse: metadata (YAML-like) + separator + query
        if "---" in content:
            metadata_part, query_part = content.split("---", 1)

            # Simple parsing (no PyYAML dependency needed)
            metadata = {}
            for line in metadata_part.strip().split("\n"):
                # Skip comments
                if line.strip().startswith("#"):
                    continue
                # Parse key: value
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

            return {**metadata, "query": query_part.strip()}

        # Fallback: entire content is query
        return {
            "name": os.path.basename(query_path).replace(".query", ""),
            "query": content.strip(),
            "time_range": "30m",
        }

    except Exception as e:
        print(f"Error loading query {query_path}: {e}")
        return None


def save_query(
    name: str,
    description: str,
    time_range: str,
    query: str,
    func_name: Optional[str] = None,
    target: str = "single",
) -> Optional[Path]:
    """
    Save a custom query to file

    Args:
        name: Query name
        description: Query description
        time_range: Default time range (e.g., "1h", "30m")
        query: CloudWatch Insights query string
        func_name: Function name (saves to function-specific dir if provided)
        target: Query target ("single", "all", "multi")

    Returns:
        Path to saved query file or None if failed
    """
    queries_dir = ensure_queries_dir(func_name)

    # Create filename from name (sanitize)
    filename = name.replace(" ", "-").lower()
    filename = "".join(c for c in filename if c.isalnum() or c == "-")
    query_file = queries_dir / f"{filename}.query"

    # Build content
    content = f"""# Created: {datetime.now().isoformat()}
name: {name}
description: {description}
time_range: {time_range}
target: {target}

---
{query.strip()}
"""

    try:
        query_file.write_text(content)
        return query_file
    except Exception as e:
        print(f"Error saving query: {e}")
        return None


def delete_query(query_path: str) -> bool:
    """
    Delete a saved query file

    Args:
        query_path: Path to .query file

    Returns:
        True if deleted successfully
    """
    try:
        if os.path.exists(query_path):
            os.remove(query_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting query: {e}")
        return False


# ============================================================================
# Time Range Utilities
# ============================================================================


def parse_time_range(time_str: str) -> Tuple[int, int]:
    """
    Parse time range string to Unix timestamps

    Args:
        time_str: Time range (e.g., "30m", "1h", "7d")

    Returns:
        (start_timestamp, end_timestamp)

    Raises:
        ValueError: If time range format is invalid
    """
    now = int(time.time())

    time_str = time_str.strip().lower()

    try:
        if time_str.endswith("m"):
            # Minutes
            minutes = int(time_str[:-1])
            start = now - (minutes * 60)
        elif time_str.endswith("h"):
            # Hours
            hours = int(time_str[:-1])
            start = now - (hours * 3600)
        elif time_str.endswith("d"):
            # Days
            days = int(time_str[:-1])
            start = now - (days * 86400)
        else:
            raise ValueError(f"Invalid time range format: {time_str}")
    except ValueError as e:
        raise ValueError(f"Invalid time range: {time_str} ({e})")

    return (start, now)


def format_time_range(time_str: str) -> str:
    """
    Format time range string for display

    Args:
        time_str: Time range (e.g., "30m", "1h", "7d")

    Returns:
        Human-readable format (e.g., "30 minutes", "1 hour", "7 days")
    """
    time_str = time_str.strip().lower()

    try:
        if time_str.endswith("m"):
            num = int(time_str[:-1])
            return f"{num} minute{'s' if num != 1 else ''}"
        elif time_str.endswith("h"):
            num = int(time_str[:-1])
            return f"{num} hour{'s' if num != 1 else ''}"
        elif time_str.endswith("d"):
            num = int(time_str[:-1])
            return f"{num} day{'s' if num != 1 else ''}"
    except ValueError:
        pass

    return time_str
