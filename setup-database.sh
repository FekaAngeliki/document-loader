#!/bin/bash

# Database Setup Script for Document Loader RAG System
# This script installs PostgreSQL (if needed), sets up the database, admin user, and application user

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DB_NAME="rag_kb_manage"
ADMIN_USER="ragkbadmin"
APP_USER="ragkbuser"
POSTGRES_USER="postgres"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to generate secure password
generate_password() {
    openssl rand -base64 12 | tr -d "=+/" | cut -c1-16
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt &> /dev/null; then
            echo "ubuntu"
        elif command -v yum &> /dev/null; then
            echo "centos"
        elif command -v dnf &> /dev/null; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Install PostgreSQL
install_postgresql() {
    local os=$(detect_os)
    print_info "Installing PostgreSQL for $os..."
    
    case $os in
        ubuntu)
            sudo apt update
            sudo apt install -y postgresql postgresql-contrib
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        centos)
            sudo yum install -y postgresql postgresql-server postgresql-contrib
            sudo postgresql-setup initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        fedora)
            sudo dnf install -y postgresql postgresql-server postgresql-contrib
            sudo postgresql-setup --initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install postgresql
                brew services start postgresql
            else
                print_error "Homebrew not found. Please install Homebrew first:"
                print_info "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        windows)
            print_error "Windows detected. Please install PostgreSQL manually:"
            print_info "  Download from: https://www.postgresql.org/download/windows/"
            print_info "  Or use chocolatey: choco install postgresql"
            exit 1
            ;;
        *)
            print_error "Unsupported OS. Please install PostgreSQL manually"
            exit 1
            ;;
    esac
    
    print_success "PostgreSQL installed successfully"
}

# Check PostgreSQL service status
check_postgresql_service() {
    local os=$(detect_os)
    
    case $os in
        ubuntu|centos|fedora)
            if systemctl is-active --quiet postgresql; then
                print_success "PostgreSQL service is running"
                return 0
            else
                print_warning "PostgreSQL service is not running"
                return 1
            fi
            ;;
        macos)
            if brew services list | grep postgresql | grep started &> /dev/null; then
                print_success "PostgreSQL service is running"
                return 0
            else
                print_warning "PostgreSQL service is not running"
                return 1
            fi
            ;;
        *)
            print_warning "Cannot check service status on this OS"
            return 1
            ;;
    esac
}

# Start PostgreSQL service
start_postgresql_service() {
    local os=$(detect_os)
    print_info "Starting PostgreSQL service..."
    
    case $os in
        ubuntu|centos|fedora)
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        macos)
            brew services start postgresql
            ;;
        *)
            print_warning "Cannot start service automatically on this OS"
            print_info "Please start PostgreSQL service manually"
            return 1
            ;;
    esac
    
    print_success "PostgreSQL service started"
}

# Check if PostgreSQL is installed and offer to install
check_postgresql() {
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL is not installed"
        echo
        echo "Would you like to install PostgreSQL automatically? (y/n)"
        read -r response
        
        if [[ "$response" =~ ^[Yy]$ ]]; then
            install_postgresql
        else
            print_error "PostgreSQL installation cancelled"
            print_info "Please install PostgreSQL manually:"
            print_info "  Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
            print_info "  CentOS/RHEL: sudo yum install postgresql postgresql-server"
            print_info "  Fedora: sudo dnf install postgresql postgresql-server"
            print_info "  macOS: brew install postgresql"
            print_info "  Windows: Download from https://www.postgresql.org/download/windows/"
            exit 1
        fi
    else
        print_success "PostgreSQL is installed"
    fi
    
    # Check if service is running
    if ! check_postgresql_service; then
        echo
        echo "Would you like to start PostgreSQL service? (y/n)"
        read -r response
        
        if [[ "$response" =~ ^[Yy]$ ]]; then
            start_postgresql_service
        else
            print_warning "PostgreSQL service not started"
            print_info "Please start PostgreSQL service manually before continuing"
        fi
    fi
}

# Function to test connection
test_connection() {
    local user=$1
    local password=$2
    local database=${3:-postgres}
    
    PGPASSWORD="$password" psql -U "$user" -h localhost -d "$database" -c "SELECT 1;" &> /dev/null
}

# Function to find existing database users and reset postgres password
reset_postgres_password() {
    print_info "Attempting to reset postgres user password using alternative methods..."
    
    # Method 1: Try using existing users from .env file
    if [ -f ".env" ]; then
        print_info "Found existing .env file, trying to use existing database user..."
        
        # Extract credentials from .env
        existing_user=$(grep "DOCUMENT_LOADER_DB_USER=" .env | cut -d'=' -f2)
        existing_password=$(grep "DOCUMENT_LOADER_DB_PASSWORD=" .env | cut -d'=' -f2)
        existing_db=$(grep "DOCUMENT_LOADER_DB_NAME=" .env | cut -d'=' -f2)
        
        if [ -n "$existing_user" ] && [ -n "$existing_password" ]; then
            print_info "Trying to connect with existing user: $existing_user"
            
            if test_connection "$existing_user" "$existing_password" "$existing_db"; then
                print_success "Connected with existing user: $existing_user"
                
                echo "Enter new password for postgres user:"
                read -s new_postgres_password
                echo
                
                print_info "Resetting postgres password using existing user..."
                PGPASSWORD="$existing_password" psql -U "$existing_user" -h localhost -d "$existing_db" \
                    -c "ALTER USER postgres PASSWORD '$new_postgres_password';" &> /dev/null
                
                if [ $? -eq 0 ]; then
                    print_success "Successfully reset postgres password using existing user"
                    print_info "You can now use this password when prompted"
                    return 0
                else
                    print_warning "Failed to reset password using existing user (user may not have sufficient privileges)"
                fi
            fi
        fi
    fi
    
    # Method 2: Try system postgres user (peer authentication)
    print_info "Trying system postgres user authentication..."
    
    if sudo -u postgres psql -c "SELECT 1;" &> /dev/null; then
        print_success "Connected using system postgres user"
        
        echo "Enter new password for postgres user:"
        read -s new_postgres_password
        echo
        
        print_info "Setting postgres user password..."
        sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$new_postgres_password';" &> /dev/null
        
        if [ $? -eq 0 ]; then
            print_success "Successfully set postgres password using system authentication"
            print_info "You can now use this password when prompted"
            return 0
        else
            print_warning "Failed to set password using system authentication"
        fi
    fi
    
    # Method 3: Temporary trust authentication (advanced)
    print_warning "Attempting temporary trust authentication (requires sudo)..."
    
    echo "This will temporarily modify PostgreSQL configuration to allow password reset."
    echo "Continue? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        modify_pg_hba_for_reset
    else
        print_error "Cannot reset postgres password automatically"
        print_info "Please reset postgres password manually:"
        print_info "  1. Connect as system user: sudo -u postgres psql"
        print_info "  2. Set password: ALTER USER postgres PASSWORD 'newpassword';"
        print_info "  3. Exit and re-run this script"
        exit 1
    fi
}

# Function to temporarily modify pg_hba.conf for password reset
modify_pg_hba_for_reset() {
    print_info "Finding PostgreSQL configuration files..."
    
    # Find pg_hba.conf
    local pg_hba_path
    pg_hba_path=$(sudo find /etc -name "pg_hba.conf" 2>/dev/null | head -1)
    
    if [ -z "$pg_hba_path" ]; then
        print_error "Cannot find pg_hba.conf file"
        return 1
    fi
    
    print_info "Found pg_hba.conf at: $pg_hba_path"
    
    # Backup original file
    sudo cp "$pg_hba_path" "$pg_hba_path.backup.$(date +%s)"
    print_info "Created backup of pg_hba.conf"
    
    # Temporarily change authentication to trust for local postgres user
    print_info "Temporarily enabling trust authentication for postgres user..."
    
    sudo sed -i.tmp 's/^local.*postgres.*peer$/local   all             postgres                                trust/' "$pg_hba_path"
    sudo sed -i.tmp 's/^local.*postgres.*md5$/local   all             postgres                                trust/' "$pg_hba_path"
    
    # Reload PostgreSQL configuration
    local os=$(detect_os)
    case $os in
        ubuntu|centos|fedora)
            sudo systemctl reload postgresql
            ;;
        macos)
            brew services restart postgresql
            ;;
        *)
            print_warning "Cannot reload PostgreSQL automatically on this OS"
            print_info "Please reload PostgreSQL configuration manually"
            ;;
    esac
    
    sleep 2  # Give PostgreSQL time to reload
    
    # Test connection and set password
    print_info "Attempting to connect with trust authentication..."
    
    if psql -U postgres -h localhost -d postgres -c "SELECT 1;" &> /dev/null; then
        print_success "Connected with trust authentication"
        
        echo "Enter new password for postgres user:"
        read -s new_postgres_password
        echo
        
        psql -U postgres -h localhost -d postgres -c "ALTER USER postgres PASSWORD '$new_postgres_password';"
        
        if [ $? -eq 0 ]; then
            print_success "Successfully set postgres password"
        else
            print_error "Failed to set postgres password"
        fi
    else
        print_error "Trust authentication failed"
    fi
    
    # Restore original pg_hba.conf
    print_info "Restoring original pg_hba.conf..."
    sudo mv "$pg_hba_path.backup."* "$pg_hba_path"
    
    # Reload PostgreSQL configuration again
    case $os in
        ubuntu|centos|fedora)
            sudo systemctl reload postgresql
            ;;
        macos)
            brew services restart postgresql
            ;;
    esac
    
    print_success "PostgreSQL configuration restored"
    print_info "You can now use the new password when prompted"
}

# Main setup function
setup_postgresql() {
    print_info "Setting up PostgreSQL for Document Loader RAG System"
    print_info "Database: $DB_NAME"
    print_info "Admin User: $ADMIN_USER"
    print_info "Application User: $APP_USER"
    echo

    # Get postgres superuser password
    echo -n "Enter PostgreSQL superuser ($POSTGRES_USER) password: "
    read -s POSTGRES_PASSWORD
    echo
    
    # Test connection to postgres
    print_info "Testing connection to PostgreSQL..."
    if ! test_connection "$POSTGRES_USER" "$POSTGRES_PASSWORD" "postgres"; then
        print_warning "Failed to connect to PostgreSQL with user '$POSTGRES_USER'"
        print_info "This usually means the postgres user password is not set or incorrect"
        echo
        
        # Try to reset postgres password using alternative methods
        reset_postgres_password
        
        # Test connection again
        echo -n "Enter PostgreSQL superuser ($POSTGRES_USER) password (the one you just set): "
        read -s POSTGRES_PASSWORD
        echo
        
        if ! test_connection "$POSTGRES_USER" "$POSTGRES_PASSWORD" "postgres"; then
            print_error "Still cannot connect to PostgreSQL with user '$POSTGRES_USER'"
            print_info "Please check:"
            print_info "  - PostgreSQL is running"
            print_info "  - User '$POSTGRES_USER' exists"
            print_info "  - Password is correct"
            print_info "  - Connection settings in pg_hba.conf allow local connections"
            exit 1
        fi
    fi
    print_success "Connected to PostgreSQL successfully"

    # Generate passwords for new users
    ADMIN_PASSWORD=$(generate_password)
    APP_PASSWORD=$(generate_password)
    
    print_info "Generated secure passwords for new users"
    
    # Create admin user
    print_info "Creating admin user '$ADMIN_USER'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -h localhost -d postgres <<SQL
-- Create admin user
CREATE USER $ADMIN_USER WITH PASSWORD '$ADMIN_PASSWORD' CREATEDB;
SQL
    if [ $? -eq 0 ]; then
        print_success "Admin user '$ADMIN_USER' created successfully"
    else
        print_warning "Admin user '$ADMIN_USER' might already exist"
    fi
    
    # Create application user
    print_info "Creating application user '$APP_USER'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -h localhost -d postgres <<SQL
-- Create application user
CREATE USER $APP_USER WITH PASSWORD '$APP_PASSWORD';
SQL
    if [ $? -eq 0 ]; then
        print_success "Application user '$APP_USER' created successfully"
    else
        print_warning "Application user '$APP_USER' might already exist"
    fi
    
    # Create database
    print_info "Creating database '$DB_NAME'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -h localhost -d postgres <<SQL
-- Create database
CREATE DATABASE $DB_NAME;
-- Grant privileges to admin user
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $ADMIN_USER;
-- Grant connect privilege to application user
GRANT CONNECT ON DATABASE $DB_NAME TO $APP_USER;
SQL
    if [ $? -eq 0 ]; then
        print_success "Database '$DB_NAME' created successfully"
    else
        print_warning "Database '$DB_NAME' might already exist"
    fi
    
    # Grant schema privileges to application user
    print_info "Setting up application user privileges..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -h localhost -d "$DB_NAME" <<SQL
-- Grant schema usage
GRANT USAGE ON SCHEMA public TO $APP_USER;

-- Grant table privileges (for existing tables)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $APP_USER;

-- Grant sequence privileges (for existing sequences)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO $APP_USER;

-- Grant privileges on future tables and sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $APP_USER;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT USAGE, SELECT ON SEQUENCES TO $APP_USER;
SQL
    print_success "Application user privileges configured"
    
    # Create .env file with application user credentials
    print_info "Creating .env file with application user credentials..."
    cat > .env <<ENV
# Database Configuration - Application User (for runtime operations)
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
    print_success ".env file created with application user credentials"
    
    # Create .env.admin file with admin credentials (for schema management)
    print_info "Creating .env.admin file with admin user credentials..."
    cat > .env.admin <<ENV
# Database Configuration - Admin User (for schema management only)
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=$DB_NAME
DOCUMENT_LOADER_DB_USER=$ADMIN_USER
DOCUMENT_LOADER_DB_PASSWORD=$ADMIN_PASSWORD
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
    print_success ".env.admin file created with admin user credentials"
    
    # Save credentials to a secure file
    print_info "Saving credentials to credentials.txt (keep this file secure!)..."
    cat > credentials.txt <<CREDS
# Document Loader PostgreSQL Credentials
# Keep this file secure and do not commit to version control!

Database: $DB_NAME

Admin User (for schema management):
  Username: $ADMIN_USER
  Password: $ADMIN_PASSWORD

Application User (for runtime operations):
  Username: $APP_USER
  Password: $APP_PASSWORD

# Usage:
# 1. For schema creation/migration: cp .env.admin .env
# 2. For normal operations: cp .env.admin is not needed, use default .env
# 3. Always use application user for production runtime
CREDS
    chmod 600 credentials.txt  # Make it readable only by owner
    print_success "Credentials saved to credentials.txt (secure file permissions set)"
    
    echo
    print_success "PostgreSQL setup completed successfully!"
    echo
    print_info "Next steps:"
    echo "  1. Create database schema (uses admin credentials):"
    echo "     cp .env.admin .env && python -m document_loader.cli create-db && cp .env.admin.bak .env"
    echo
    echo "  2. Test connection with application user:"
    echo "     python -m document_loader.cli check-connection"
    echo
    echo "  3. Start using the document loader with application user credentials"
    echo
    print_warning "Security notes:"
    echo "  • .env file uses application user (limited privileges)"
    echo "  • .env.admin file uses admin user (full privileges) - use only for schema changes"
    echo "  • credentials.txt contains all passwords - keep secure!"
    echo "  • Consider adding .env.admin and credentials.txt to .gitignore"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --db-name NAME     Database name (default: $DB_NAME)"
    echo "  --admin-user NAME  Admin username (default: $ADMIN_USER)"  
    echo "  --app-user NAME    Application username (default: $APP_USER)"
    echo "  --postgres-user NAME PostgreSQL superuser (default: $POSTGRES_USER)"
    echo "  --help             Show this help message"
    echo
    echo "This script will:"
    echo "  1. Create PostgreSQL database and users"
    echo "  2. Set up proper permissions"
    echo "  3. Generate .env files with credentials"
    echo "  4. Save credentials to a secure file"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --db-name)
            DB_NAME="$2"
            shift 2
            ;;
        --admin-user)
            ADMIN_USER="$2"
            shift 2
            ;;
        --app-user)
            APP_USER="$2"
            shift 2
            ;;
        --postgres-user)
            POSTGRES_USER="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    check_postgresql
    setup_postgresql
}

# Run main function
main