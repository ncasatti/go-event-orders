# Lambda Payloads - Composable Structure

This directory contains composable YAML payloads for AWS Lambda HTTP API Gateway v2.

## Structure

```
payloads/
├── _base/              # Auto-merged base files
│   ├── general.yaml    # Always merged (lowest priority)
│   ├── context-dev.yaml    # Merged when stage=dev
│   └── context-prod.yaml   # Merged when stage=prod
│
├── auth/               # Authentication snippets
│   ├── no-auth.yaml
│   ├── cognito-latam.yaml
│   ├── cognito-xionico.yaml
│   └── cognito-testing.yaml
│
├── parameters/         # Query string parameters
│   ├── vendedor-207.yaml
│   ├── vendedor-1.yaml
│   └── vendedor-cuenta.yaml
│
├── bodies/             # Request body snippets
│   ├── empty.yaml
│   ├── vendedor-single.yaml
│   └── vendedor-array.yaml
│
└── examples/           # Complete payload examples
    ├── simple-no-auth.yaml
    ├── test-with-cognito.yaml
    ├── query-vendedor-207.yaml
    └── full-body-vendedor.yaml
```

## How It Works

### Merge Order (lowest to highest priority)
1. `_base/general.yaml` - Always merged first
2. `_base/context-{stage}.yaml` - Stage-specific (dev/prod)
3. Selected payload file - Highest priority (wins)

### Deep Merge Rules
- **Dictionaries**: Merged recursively
- **Lists**: Replaced (not concatenated)
- **Values**: Override wins
- **null values**: Remove the key

### Example: Composing a Payload

**Your file** (`examples/test-with-cognito.yaml`):
```yaml
routeKey: "GET /test"
requestContext:
  authorizer:
    lambda:
      xsi_client: "latam"
```

**Gets merged with** `_base/general.yaml`:
```yaml
version: "2.0"
routeKey: "GET /default"  # Overridden by your file
headers:
  Content-Type: "application/json"
requestContext:
  accountId: "123456"
  authorizer: {}  # Deep-merged with your auth
```

**Final result**:
```yaml
version: "2.0"
routeKey: "GET /test"  # From your file
headers:
  Content-Type: "application/json"  # From general.yaml
requestContext:
  accountId: "123456"  # From general.yaml
  authorizer:
    lambda:
      xsi_client: "latam"  # From your file
```

## Usage

### Via Interactive Menu
```bash
clingy
# Select: Invoke Functions → Local/Remote → Select function → Compose payload
# Navigate through folders and select your payload
```

### Via CLI
```bash
clingy invoke -f status --payload payloads/examples/simple-no-auth.yaml --local
```

### Via Payload Navigator
```bash
clingy
# Select: Payload Navigator → Select function → Browse payloads
# Preview composed payload without invoking
```

## Creating New Payloads

### Option 1: Composable (Recommended)
Create a minimal YAML file that extends base:

```yaml
# my-payload.yaml
routeKey: "POST /my-endpoint"
queryStringParameters:
  my_param: "value"
```

### Option 2: Standalone
Create a complete payload (no merging):

```yaml
# standalone.yaml
version: "2.0"
routeKey: "GET /standalone"
# ... all fields ...
```

## Tips

- **Use auth/ snippets**: Copy auth from `auth/` folder to your payload
- **Reuse parameters**: Copy from `parameters/` folder
- **Test first**: Use "Payload Navigator" to preview composed payload
- **Override stage**: Set `PAYLOAD_DEFAULT_STAGE` in `config.py`

## Validation

Payloads are validated before invocation:

**Required fields**: `version`, `routeKey`, `rawPath`  
**Recommended fields**: `requestContext`, `headers`

Validation errors prevent invocation. Warnings are shown but don't block.
