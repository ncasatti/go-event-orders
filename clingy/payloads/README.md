# Clingy Payloads - Composable Structure

This directory contains composable YAML payloads for simulating AWS Lambda HTTP API Gateway v2 events.

## Directory Structure

```
payloads/
├── _base/              # Auto-merged base files (lowest priority)
├── auth/               # Authentication context snippets
├── parameters/         # Query string and path parameters
├── bodies/             # Request body snippets
└── examples/           # Complete, ready-to-use payload examples
```

## How It Works (Deep Merge)

Clingy uses a **Deep Merge** strategy to build the final JSON event sent to your Lambda function. This allows you to keep your payloads DRY (Don't Repeat Yourself).

### Merge Order (lowest to highest priority)
1. `_base/general.yaml` - Always merged first. Contains standard API Gateway headers and context.
2. `_base/context-{stage}.yaml` - Stage-specific overrides (e.g., `dev` or `prod`).
3. **Selected payload file(s)** - Highest priority. Overrides any base values.

### Merge Rules
- **Dictionaries**: Merged recursively.
- **Lists**: Replaced entirely (not concatenated).
- **Values**: The highest priority file wins.
- **Null values**: Setting a key to `null` removes it from the final payload.

## Usage

### 1. Interactive CLI (Recommended)
Run Clingy without arguments to open the interactive menu:
```bash
clingy
```
Navigate to **Invoke Functions** -> Select Local/Remote -> Select your function -> **Compose payload**. You can select multiple YAML snippets (e.g., an auth snippet + a body snippet) and Clingy will merge them on the fly.

### 2. Direct CLI Invocation
You can bypass the menu by passing the payload path directly:
```bash
clingy invoke -f <function_name> --payload payloads/examples/<your-payload>.yaml --local
```

### 3. Payload Navigator
Use the **Payload Navigator** option in the main menu to preview how your selected YAML files will be merged into the final JSON event *before* invoking the function.

## Creating New Payloads

Create minimal YAML files that only define what changes. You don't need to include standard API Gateway boilerplate.

**Required fields to override:**
- `routeKey` (e.g., `"GET /status"`)
- `rawPath` (e.g., `"/status"`)

**Optional fields to override:**
- `queryStringParameters`
- `body`
- `requestContext.authorizer`