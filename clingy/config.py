"""
Project-specific configuration for Serverless (AWS Lambda + Go)

CUSTOMIZE THIS FILE FOR YOUR PROJECT
This is the only file that needs to be modified when using clingy in your project.
"""

import os
from pathlib import Path

from clingy.core.dependency import Dependency

# ============================================================================
# Project Metadata
# ============================================================================
PROJECT_NAME = "Go Event Orders"
PROJECT_VERSION = "1.0.0"


# ============================================================================
# AWS Configuration
# ============================================================================
ENV = "dev"
AWS_PROFILE = "xsi"
SERVICE_NAME = "event-test"


# ============================================================================
# Build Settings
# ============================================================================
BUILD_SETTINGS = {
    "GOOS": "linux",
    "GOARCH": "amd64",
    "CGO_ENABLED": "0",
}

# Go build flags
BUILD_FLAGS = ["-ldflags", "-s -w"]


# ============================================================================
# Project Root Detection
# ============================================================================
# Root del proyecto serverless (donde están functions/, .bin/, serverless.yaml)
# Default: Parent directory of config.py location (standard structure)
# Override: Set environment variable PROJECT_ROOT=/custom/path
_config_dir = Path(__file__).parent
PROJECT_ROOT = os.getenv("PROJECT_ROOT", str(_config_dir.parent))


# ============================================================================
# Paths
# ============================================================================
FUNCTIONS_DIR = os.path.join(PROJECT_ROOT, "functions")
BIN_DIR = os.path.join(PROJECT_ROOT, ".bin")


# ============================================================================
# Deployment Settings
# ============================================================================
# Serverless Framework settings
SERVERLESS_STAGE = ENV
SERVERLESS_PROFILE = AWS_PROFILE


# ============================================================================
# Invoke Settings
# ============================================================================
# Method for remote invocation: "serverless" or "aws-cli"
# - "serverless": Use 'serverless invoke -f <function>' (requires serverless framework)
# - "aws-cli": Use 'aws lambda invoke' directly (requires AWS CLI)
INVOKE_REMOTE_METHOD = "serverless"

# AWS region for Lambda invocations (only used with aws-cli method)
INVOKE_AWS_REGION = "us-west-2"


# ============================================================================
# Payload Settings
# ============================================================================
# Payloads directory (same folder as config.py, not project root)
PAYLOADS_DIR = os.path.join(_config_dir, "payloads")

# Default stage for payload composition (uses current environment)
PAYLOAD_DEFAULT_STAGE = SERVERLESS_STAGE

# Enable legacy payload support (test-payloads/ and functions/*/payloads/)
PAYLOAD_LEGACY_SUPPORT = True

# Show merge sources in payload preview (useful for debugging)
PAYLOAD_SHOW_MERGE_SOURCES = True

# ============================================================================
# Results Settings
# ============================================================================
# Results directory for logs and outputs (centralized, not in functions/)
RESULTS_DIR = os.path.join(_config_dir, "results")
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")
OUTPUTS_DIR = os.path.join(RESULTS_DIR, "outputs")

# ============================================================================
# Function List
# ============================================================================
# List of Go functions to build/deploy
# UPDATE THIS LIST FOR YOUR PROJECT
# Example:
# GO_FUNCTIONS = [
#     "status",
#     "getUsers",
#     "createUser",
# ]
GO_FUNCTIONS = [
    "status",
    "getClients",
    "getProducts",
    "postOrders",
    "processOrders",
]


# ============================================================================
# Required Dependencies
# ============================================================================
DEPENDENCIES = [
    Dependency(
        name="fzf",
        command="fzf",
        description="Fuzzy finder for interactive menus",
        install_macos="brew install fzf",
        install_linux="sudo pacman -S fzf",  # Arch
        required=True,
    ),
    Dependency(
        name="serverless",
        command="serverless",
        description="Serverless Framework CLI",
        install_macos="npm install -g serverless",
        install_linux="npm install -g serverless",
        required=True,
    ),
    Dependency(
        name="aws",
        command="aws",
        description="AWS Command Line Interface",
        install_macos="brew install awscli",
        install_linux="sudo pacman -S aws-cli",  # Arch
        required=True,
    ),
    Dependency(
        name="go",
        command="go",
        description="Go programming language",
        install_macos="brew install go",
        install_linux="sudo pacman -S go",  # Arch
        required=True,
    ),
    Dependency(
        name="python",
        command="python",
        description="Python 3 interpreter",
        install_macos="brew install python3",
        install_linux="sudo pacman -S python3",  # Arch
        required=True,
    ),
]
