#!/bin/bash

# Localhost PostgreSQL Setup for RAG Knowledge Base System
# Creates database and application user with schema management privileges

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Configuration
DB_NAME="rag_kb_manage"
APP_USER="ragkbuser"
APP_PASSWORD="SecureAppPassword123!"

echo "===========================================" 
echo "   RAG Knowledge Base - Localhost Setup"
echo "==========================================="
echo
print_info "Database: $DB_NAME"
print_info "Application User: $APP_USER"
echo

# Get postgres password
echo -n "Enter postgres superuser password: "
read -s POSTGRES_PASSWORD
echo
echo

# Test postgres connection
print_info "Testing postgres connection..."
if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -h localhost -c "SELECT 1;" &> /dev/null; then
    print_error "Cannot connect to PostgreSQL as postgres user"
    print_info "Please ensure:"
    print_info "  - PostgreSQL is running"
    print_info "  - postgres user exists"  
    print_info "  - Password is correct"
    exit 1
fi
print_success "Connected to PostgreSQL"

# Create database (without schema)
print_info "Creating database '$DB_NAME'..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -h localhost <<SQL
SELECT 'CREATE DATABASE $DB_NAME' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME');
\gexec
SQL

if [ $? -eq 0 ]; then
    print_success "Database '$DB_NAME' ready"
else
    print_error "Failed to create database"
    exit 1
fi

# Create application user with schema management privileges
print_info "Creating application user '$APP_USER'..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -h localhost -d "$DB_NAME" <<SQL
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$APP_USER') THEN
        CREATE USER $APP_USER WITH PASSWORD '$APP_PASSWORD';
    END IF;
END
\$\$;

-- Grant database connection
GRANT CONNECT ON DATABASE $DB_NAME TO $APP_USER;

-- Grant schema creation privileges  
GRANT CREATE ON DATABASE $DB_NAME TO $APP_USER;

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO $APP_USER;

-- Allow creating databases (needed for some schema operations)
ALTER USER $APP_USER CREATEDB;

SQL

if [ $? -eq 0 ]; then
    print_success "Application user '$APP_USER' created with schema management privileges"
else
    print_error "Failed to create application user"
    exit 1
fi

# Test application user connection
print_info "Testing application user connection..."
if PGPASSWORD="$APP_PASSWORD" psql -U "$APP_USER" -h localhost -d "$DB_NAME" -c "SELECT current_user, current_database();" &> /dev/null; then
    print_success "Application user can connect successfully"
else
    print_error "Application user connection failed"
    exit 1
fi

# Create .env file
print_info "Creating .env file..."
cat > .env <<ENV
# Database Configuration - Application User
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=$DB_NAME
DOCUMENT_LOADER_DB_USER=$APP_USER
DOCUMENT_LOADER_DB_PASSWORD=$APP_PASSWORD
DOCUMENT_LOADER_DB_MIN_POOL_SIZE=10
DOCUMENT_LOADER_DB_MAX_POOL_SIZE=20

# Add your specific source configurations here as needed
# Examples:
# SHAREPOINT_TENANT_ID=your-tenant-id
# SHAREPOINT_CLIENT_ID=your-client-id
# SHAREPOINT_CLIENT_SECRET=your-client-secret
# AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
# ONEDRIVE_CLIENT_ID=your-onedrive-client-id
ENV

print_success ".env file created"

# Test schema creation capability
print_info "Testing schema creation capability..."
PGPASSWORD="$APP_PASSWORD" psql -U "$APP_USER" -h localhost -d "$DB_NAME" <<SQL
-- Test schema creation
CREATE SCHEMA IF NOT EXISTS test_schema_creation;
CREATE TABLE test_schema_creation.test_table (id SERIAL PRIMARY KEY, name TEXT);
INSERT INTO test_schema_creation.test_table (name) VALUES ('schema_test');
SELECT 'Schema creation test: ' || name FROM test_schema_creation.test_table;
DROP SCHEMA test_schema_creation CASCADE;
SQL

if [ $? -eq 0 ]; then
    print_success "Application user can create/drop schemas successfully"
else
    print_warning "Schema creation test failed, but basic setup is complete"
fi

echo
print_success "Localhost setup completed successfully!"
echo
print_info "Next steps:"
echo "  1. Test connection: python -m document_loader.cli check-connection"
echo "  2. Create schema for RAG use case: python -m document_loader.cli create-schema --name my_rag_case"
echo "  3. List schemas: python -m document_loader.cli list-schemas"
echo
print_info "Application user credentials:"
echo "  User: $APP_USER"
echo "  Password: $APP_PASSWORD"
echo "  Database: $DB_NAME"
echo
print_warning "Security note: Change the default password in production!"