# Database Schema Migrator

> **Note:** This tool is part of the Go Event Orders microservice architecture.

______________________________________________________________________

## Overview

This tool is responsible for managing the database schema for the **Go Event Orders** microservice. It connects to the PostgreSQL database and automatically creates or updates tables based on the domain models defined in the application.

## Architecture

Unlike traditional migration tools that use raw SQL files, this migrator uses **GORM's AutoMigrate** feature. It directly imports the domain models from `internal/domain/` (e.g., `Client`, `Product`, `Order`, `OrderItem`) and ensures the database schema is always perfectly synchronized with the Go structs.

This approach guarantees a single source of truth for the data structure across the entire system.

______________________________________________________________________

## Usage

### 1. Configure Environment Variables
The migrator reads database credentials from the `.env` file located in the root of the project. Ensure your `.env` file is populated:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_NAME=orders_db
```

### 2. Run the Migrator
Execute the migrator from the root of the project:

```bash
go run migrator/main.go
```

The script will connect to the database, apply the necessary schema changes, and output the migration logs to the console and a local `logs/` directory.

### Workflow for Schema Changes
When you need to modify the database structure (e.g., add a new column):
1. Update the corresponding Go struct in `internal/domain/orders/`.
2. Run the migrator (`go run migrator/main.go`).
3. GORM will automatically detect the changes and alter the tables safely without dropping existing data.
