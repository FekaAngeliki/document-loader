#!/bin/bash
# Document Loader Environment Setup
# 
# Source this file to set up environment variables for document-loader
# Usage: source env_setup.sh

# Database configuration
export DOCUMENT_LOADER_DB_HOST="localhost"
export DOCUMENT_LOADER_DB_PORT="5432"
export DOCUMENT_LOADER_DB_NAME="document_loader"
export DOCUMENT_LOADER_DB_USER="postgres"
export DOCUMENT_LOADER_DB_PASSWORD="your_password_here"
export DOCUMENT_LOADER_DB_MIN_POOL_SIZE="10"
export DOCUMENT_LOADER_DB_MAX_POOL_SIZE="20"

# Logging configuration
export DOCUMENT_LOADER_LOG_LEVEL="INFO"

echo "Document Loader environment variables set."
echo "To use: document-loader --help"