# DevOps Setup Instructions for RAG Knowledge Base System

This document provides manual setup instructions for DevOps teams to prepare PostgreSQL for the RAG document-loader application.

## Overview

The application needs:
- A PostgreSQL database instance (without application schema)
- An application user with schema management privileges
- The application will create schemas dynamically for different RAG use cases

## PostgreSQL Setup Commands

### 1. Create Database (Empty, No Schema)

```sql
-- Connect as postgres superuser
psql -U postgres -h localhost

-- Create the database
CREATE DATABASE rag_kb_manage;

-- Exit
\q
```

### 2. Create Application User with Schema Management Privileges

```sql
-- Connect as postgres superuser to the new database
psql -U postgres -h localhost -d rag_kb_manage

-- Create application user
CREATE USER ragkbuser WITH PASSWORD 'SecureAppPassword123!';

-- Grant database connection
GRANT CONNECT ON DATABASE rag_kb_manage TO ragkbuser;

-- Grant schema creation privileges
GRANT CREATE ON DATABASE rag_kb_manage TO ragkbuser;

-- Grant usage on public schema (if needed for temporary operations)
GRANT USAGE ON SCHEMA public TO ragkbuser;

-- Allow the user to create/drop schemas
ALTER USER ragkbuser CREATEDB;

-- Exit
\q
```

### 3. Application User Capabilities

The `ragkbuser` can now:
- ✅ Create new schemas for different RAG use cases
- ✅ Drop schemas when no longer needed  
- ✅ Create tables, indexes, sequences within their schemas
- ✅ Read, write, update, delete data in their schemas
- ✅ Grant/revoke permissions on their schemas

### 4. Verify Setup

```sql
-- Test connection as application user
psql -U ragkbuser -h localhost -d rag_kb_manage

-- Test schema creation
CREATE SCHEMA test_kb_schema;
CREATE TABLE test_kb_schema.test_table (id SERIAL PRIMARY KEY, name TEXT);
INSERT INTO test_kb_schema.test_table (name) VALUES ('test');
SELECT * FROM test_kb_schema.test_table;

-- Cleanup test
DROP SCHEMA test_kb_schema CASCADE;

-- Exit
\q
```

## Environment Configuration

Create `.env` file for the application:

```bash
# Database Configuration - Application User
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=rag_kb_manage
DOCUMENT_LOADER_DB_USER=ragkbuser
DOCUMENT_LOADER_DB_PASSWORD=SecureAppPassword123!
DOCUMENT_LOADER_DB_MIN_POOL_SIZE=10
DOCUMENT_LOADER_DB_MAX_POOL_SIZE=20
```

## Security Notes

1. **Schema Isolation**: Each RAG use case gets its own schema
2. **Limited Privileges**: User cannot access other schemas unless explicitly granted
3. **No Superuser Access**: Application user has minimal required privileges
4. **Password Security**: Use strong passwords and consider rotation

## Application Usage

After setup, the application can:

1. **Test Connection**: `document-loader check-connection`
2. **Create Schema for RAG Use Case**: `document-loader create-schema --name finance_docs`
3. **List Schemas**: `document-loader list-schemas`
4. **Drop Schema**: `document-loader drop-schema --name finance_docs`

## Monitoring

Monitor the following:
- Database connections from application user
- Schema creation/deletion events
- Table growth within schemas
- Query performance per schema

## Backup Strategy

- **Database Level**: Regular backups of `rag_kb_manage` database
- **Schema Level**: Individual schema backups for large RAG use cases
- **Configuration**: Backup application configuration files

---

**Contact**: Provide application team contact information for any issues.