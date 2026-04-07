# Serverless Manager Template

> **AWS Lambda + Go** management system for `clingy`. Optimized for high-velocity development, deployment, and interactive payload composition.

---

## Features

- ✅ **Full Pipeline** — Build, Zip, and Deploy Go functions in a single interactive flow.
- ✅ **Composable Payloads** — Build Lambda events by mixing reusable YAML snippets (Auth, Body, Params).
- ✅ **Live Monitoring** — Tail CloudWatch logs and run Insights queries directly from the CLI.
- ✅ **Payload Navigator** — Interactive browser to preview and validate composed payloads.
- ✅ **Contextual Config** — Environment-aware settings (dev/prod) for AWS profiles and regions.

---

## Quick Start

### 1. Initialize
```bash
clingy init --template serverless
```

### 2. Configure (`config.py`)
```python
ENV = "dev"
AWS_PROFILE = "my-profile"
SERVICE_NAME = "my-service"

# List of Go functions in functions/ directory
GO_FUNCTIONS = ["status", "getUsers", "createUser"]
```

### 3. Run
```bash
clingy
```

---

## Project Structure

- `commands/` — CLI orchestration (Functions, Logs, Invoke, Status).
- `core/` — Logic for payload composition and AWS integration.
- `functions/` — Your Go Lambda source code (one directory per function).
- `payloads/` — Reusable YAML snippets for testing.
- `.bin/` — Compiled binaries (auto-generated).
- `results/` — Output and logs from invocations.

---

## Composable Payload System

The core of this template is the **Snippet-based Payload Builder**. Instead of static JSON files, you compose events by selecting snippets from `payloads/`:

1. **Base:** `_base/general.yaml` (Always merged).
2. **Stage:** `_base/context-{ENV}.yaml` (Auto-selected).
3. **Snippets:** Your selections from `auth/`, `bodies/`, and `parameters/`.

**Merge Logic:** Deep merge for dictionaries, replacement for lists. Last snippet wins on conflicts.

---

## Dependencies

- **fzf** — Interactive menus.
- **go** — Compiler for Lambda functions.
- **aws-cli** — Remote invocation and logs.
- **serverless** — Deployment framework.

---

**License:** MIT
**Maintainer:** [@ncasatti](https://github.com/ncasatti)
