# Go Event Orders Microservice

> [!IMPORTANT]
> **Note:** This is a reduced version of a real system I designed and built, which I cannot publicly share because it belongs to my company. This repository serves as a demonstration of architecture and best practices.

---

## Overview

**Go Event Orders** is a production-grade, event-driven microservice built in **Go** that demonstrates modern backend architecture principles. It showcases how to design scalable, resilient, and maintainable systems using **Clean Architecture**, **Event-Driven Design**, and **AWS Serverless** technologies.

The system manages asynchronous order ingestion from mobile devices, ensuring high throughput, fault tolerance, and complete decoupling between producers and consumers through an elegant S3-based event bus pattern.

### Why This Architecture Matters

This project uses **separation of concerns** rather than a monolithic request-response cycle, the system splits the problem into two distinct phases:

1. **Fast Ingest** — Accept and queue orders instantly (sub-100ms response).
2. **Async Processing** — Validate business logic and persist data without blocking the client.

This pattern is battle-tested in high-scale systems and eliminates the need for traditional message queues while maintaining full event traceability and idempotent processing.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Go 1.23+ |
| **Compute** | AWS Lambda (Custom Go Runtime) |
| **Storage** | Amazon S3 (Event Bus) + Amazon RDS PostgreSQL (Persistence) |
| **Infrastructure as Code** | Serverless Framework v3 |
| **ORM** | GORM |
| **Architecture Pattern** | Event-Driven + Clean Architecture |

---

## System Architecture

The system implements a **Producer-Consumer** pattern with S3 as the event bus. This design decouples the mobile client from backend processing, enabling independent scaling and fault isolation.

### Data Flow Diagram

```mermaid
sequenceDiagram
    participant Mobile as App Móvil
    participant API as API Gateway / postOrders
    participant S3 as Amazon S3 Bucket
    participant Lambda as processOrders Lambda
    participant DB as PostgreSQL

    Mobile->>API: POST /orders (OrderPayload)
    Note right of Mobile: Envío de órdenes offline/online
    API->>S3: Upload JSON (orders/{timestamp}-{device}.json)
    API-->>Mobile: 202 Accepted (Order Queued)

    Note over S3,Lambda: S3 Event Trigger (ObjectCreated)
    S3->>Lambda: Invoca processOrders
    Lambda->>S3: Descarga JSON Payload
    Lambda->>Lambda: Validación de Negocio (Clientes, Stock)
    Lambda->>DB: Transacción ACID (Insertar Pedidos)
    Lambda-->>S3: (Opcional) Mover a 'processed/'
```

### Processing Phases

1. **Ingest Phase** — The `POST /orders` endpoint validates the payload structurally and uploads it to S3 immediately, returning a `202 Accepted` response. The client is freed from waiting for backend processing.

2. **Event Trigger** — The S3 upload automatically triggers an event that invokes the `processOrders` Lambda function.

3. **Business Logic Phase** — The processor downloads the payload, executes domain validations (customer existence, product stock), and persists data transactionally to PostgreSQL.

---

## Project Structure

The codebase follows a modular, layered architecture that enforces separation of concerns:

```
.
├── functions/
│   ├── apitypes/          # Domain Models (Clean Types)
│   │   ├── client.go
│   │   ├── order.go
│   │   ├── payload.go
│   │   └── product.go
│   ├── getArticulos/      # GET Endpoint (Direct Consumer)
│   ├── getClients/        # GET Endpoint (Direct Consumer)
│   ├── postOrders/        # POST Endpoint (Event Producer)
│   ├── processOrders/     # Event Processor (Async Consumer)
│   │   ├── main.go
│   │   └── validators/    # Pure Business Logic
│   └── utils/             # Cross-cutting Utilities (DB, Logging, Responses)
├── clingy/                # Interactive CLI for Lambda Testing & Deployment
├── serverless.yml         # AWS Infrastructure Definition
├── go.mod                 # Dependencies
└── readme.md              # This file
```

### Key Components

#### **`apitypes/`** — Domain Models
Pure Go structs with zero external dependencies. These types are the single source of truth for data contracts across the entire system. No database logic, no AWS SDK calls—just clean, serializable domain objects.

**Why it matters:** Enables easy testing, clear contracts, and reusability across functions.

#### **`validators/`** — Business Logic
Encapsulates all domain rules (customer validation, stock checks, order constraints). These are pure functions that take domain objects and return validation results.

**Why it matters:** Business logic is testable in isolation without spinning up databases or AWS services. Rules are centralized and versioned with the code.

#### **`postOrders/`** — Lightweight Producer
A thin HTTP handler that accepts the order payload, validates its structure, and uploads it to S3. Its single responsibility is to be fast and reliable.

**Why it matters:** Keeps the critical path short. Mobile clients get instant feedback. No database locks, no complex transactions.

#### **`processOrders/`** — Heavy Lifting Consumer
The workhorse function that handles all business complexity: validation, database transactions, error recovery, and idempotent retries.

**Why it matters:** Separates concerns. Complex logic runs asynchronously, isolated from the client request. Failures don't cascade to the mobile app.

#### **`utils/`** — Cross-cutting Concerns
Shared utilities for database connections, structured logging, HTTP response formatting (JSend pattern), and AWS SDK interactions.

**Why it matters:** Eliminates duplication. Ensures consistent error handling and logging across all functions.

---

## Design Patterns & Best Practices

### 1. **Clean Architecture**
The codebase strictly separates:
- **Entities** (`apitypes/`) — Domain objects, independent of frameworks.
- **Use Cases** (`postOrders/`, `processOrders/`) — Business logic orchestration.
- **Adapters** (`utils/`) — Database, HTTP, AWS integrations.

This layering makes the system testable, maintainable, and framework-agnostic.

### 2. **Event-Driven Design**
By using S3 as an event bus, the system achieves:
- **Decoupling** — Producers and consumers are completely independent.
- **Scalability** — Each component scales independently based on demand.
- **Resilience** — Failures in processing don't affect order ingestion.
- **Auditability** — Every event is persisted in S3 for compliance and debugging.

### 3. **Idempotent Processing**
The `processOrders` function is designed to be safely retried. If a Lambda invocation fails midway, re-running it produces the same result without duplicating data or side effects.

**Implementation:** Database constraints (unique keys) and transaction semantics ensure idempotency at the persistence layer.

### 4. **Structured Error Handling**
All functions return standardized HTTP responses using the **JSend pattern**:
```json
{
  "status": "success|fail|error",
  "data": { /* ... */ },
  "message": "Human-readable error description"
}
```

This ensures clients can reliably parse and handle errors.

### 5. **Security by Design**
- **Environment Variables** — All credentials (DB passwords, API keys) are injected at runtime, never hardcoded.
- **IAM Least Privilege** — Each Lambda function has minimal permissions (S3 read/write, RDS access only).
- **Input Validation** — All payloads are validated before processing.

---

## Clingy: Interactive Lambda Testing & Deployment

**Clingy** is a context-aware CLI framework purpose-built for testing and invoking AWS Lambda functions locally and remotely. It eliminates the friction of manual payload composition and deployment cycles.

### What Clingy Does

- **Composable Payloads** — Build Lambda events by mixing reusable YAML snippets instead of writing static JSON files.
- **Interactive Testing** — Invoke functions locally or remotely with a single command, with real-time feedback.
- **Automated Deployment** — Build, zip, and deploy Go functions in a single orchestrated workflow.
- **Live Monitoring** — Tail CloudWatch logs and run Insights queries directly from the CLI.
- **Environment Awareness** — Automatically switch between dev/staging/prod configurations.

### Why It Matters

Traditional Lambda development involves:
1. Write code → 2. Compile → 3. Zip → 4. Deploy → 5. Invoke via AWS Console → 6. Check logs in CloudWatch

Clingy collapses this into a single interactive flow, reducing iteration time from minutes to seconds. The composable payload system means you can test complex scenarios (auth headers, nested bodies, query parameters) without manually editing JSON files.

For more details, see the [Clingy documentation](./clingy/README.md).

---

## Getting Started

### Prerequisites

- Go 1.23+
- Node.js & Serverless Framework (`npm install -g serverless`)
- AWS account with appropriate IAM permissions
- Python 3.8+ (for Clingy)

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone [GITHUB_PROJECT_URL]
   cd go-event-orders
   ```

2. **Install dependencies:**
   ```bash
   go mod download
   npm install
   ```

3. **Configure AWS credentials:**
   ```bash
   aws configure --profile your-profile
   ```

4. **Deploy to AWS:**
   ```bash
   serverless deploy --aws-profile your-profile
   ```

5. **Test with Clingy:**
   ```bash
   cd clingy
   python3 -m clingy
   ```

---

## Demo & Visualization

> ![Deploy functions](docs/assets/deploy.gif)
> 
> Shows the buil, zip and deploy workflow with clingy.

> ![Invoke function](docs/assets/invoke.gif)
> 
> Shows the invoke workflow.

> ![Post Orders](docs/assets/post-orders.gif)
> 
> Shows the post orders workflow.

---

## Key Takeaways

This project demonstrates:

✅ **Scalable Architecture** — Handles high-volume order ingestion without bottlenecks.

✅ **Resilient Design** — Failures in processing don't affect order acceptance. Retries are safe and automatic.

✅ **Clean Code** — Business logic is separated from infrastructure. Easy to test, easy to modify.

✅ **Developer Experience** — Clingy makes local development and testing as fast as production deployment.

✅ **Production-Ready** — Structured logging, error handling, security, and monitoring built in from day one.

---

## Author

[@ncasatti](https://github.com/ncasatti)
