#!/bin/bash
# Configuration Admin Helper Script
# Provides convenient shortcuts for common config management tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/cli_config_admin.py"

# Helper functions
print_header() {
    echo -e "${BLUE}=====================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=====================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if CLI script exists
if [ ! -f "$CLI_SCRIPT" ]; then
    print_error "CLI script not found: $CLI_SCRIPT"
    exit 1
fi

# Main commands
case "${1:-help}" in
    "upload")
        print_header "UPLOAD CONFIGURATION"
        if [ -z "$2" ]; then
            print_error "Usage: $0 upload <config_file> [name] [description]"
            exit 1
        fi
        
        CONFIG_FILE="$2"
        CONFIG_NAME="${3:-$(basename "$CONFIG_FILE" .json)}"
        CONFIG_DESC="${4:-Uploaded via config_admin.sh}"
        
        if [ ! -f "$CONFIG_FILE" ]; then
            print_error "Configuration file not found: $CONFIG_FILE"
            exit 1
        fi
        
        echo "Uploading: $CONFIG_FILE"
        echo "Name: $CONFIG_NAME"
        echo "Description: $CONFIG_DESC"
        echo
        
        python3 "$CLI_SCRIPT" upload "$CONFIG_FILE" --name "$CONFIG_NAME" --description "$CONFIG_DESC"
        ;;
        
    "list"|"ls")
        print_header "STORED CONFIGURATIONS"
        python3 "$CLI_SCRIPT" list
        ;;
        
    "show")
        if [ -z "$2" ]; then
            print_error "Usage: $0 show <config_name> [--full]"
            exit 1
        fi
        
        print_header "CONFIGURATION DETAILS: $2"
        if [ "$3" = "--full" ]; then
            python3 "$CLI_SCRIPT" show "$2" --show-full
        else
            python3 "$CLI_SCRIPT" show "$2"
        fi
        ;;
        
    "deploy")
        if [ -z "$2" ]; then
            print_error "Usage: $0 deploy <config_name>"
            exit 1
        fi
        
        print_header "DEPLOYING CONFIGURATION: $2"
        echo -e "${YELLOW}This will create a new knowledge base from the configuration.${NC}"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "$CLI_SCRIPT" deploy "$2"
        else
            print_warning "Deployment cancelled"
        fi
        ;;
        
    "export")
        if [ -z "$2" ] || [ -z "$3" ]; then
            print_error "Usage: $0 export <config_name> <output_file>"
            exit 1
        fi
        
        print_header "EXPORTING CONFIGURATION: $2"
        python3 "$CLI_SCRIPT" export "$2" "$3"
        ;;
        
    "summary"|"stats")
        print_header "CONFIGURATION SUMMARY"
        python3 "$CLI_SCRIPT" summary
        ;;
        
    "delete"|"remove")
        if [ -z "$2" ]; then
            print_error "Usage: $0 delete <config_name>"
            exit 1
        fi
        
        print_header "DELETE CONFIGURATION: $2"
        echo -e "${RED}WARNING: This will archive the configuration.${NC}"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "$CLI_SCRIPT" delete "$2" --force
        else
            print_warning "Delete cancelled"
        fi
        ;;
        
    "bulk-upload")
        print_header "BULK UPLOAD CONFIGURATIONS"
        CONFIG_DIR="${2:-configs}"
        
        if [ ! -d "$CONFIG_DIR" ]; then
            print_error "Configuration directory not found: $CONFIG_DIR"
            exit 1
        fi
        
        echo "Uploading all JSON files from: $CONFIG_DIR"
        echo
        
        for config_file in "$CONFIG_DIR"/*.json; do
            if [ -f "$config_file" ]; then
                config_name=$(basename "$config_file" .json)
                echo "📤 Uploading: $config_name"
                python3 "$CLI_SCRIPT" upload "$config_file" --name "$config_name" --description "Bulk uploaded from $CONFIG_DIR"
                echo
            fi
        done
        
        print_success "Bulk upload completed"
        ;;
        
    "validate")
        if [ -z "$2" ]; then
            print_error "Usage: $0 validate <config_file>"
            exit 1
        fi
        
        CONFIG_FILE="$2"
        print_header "VALIDATING CONFIGURATION: $CONFIG_FILE"
        
        if [ ! -f "$CONFIG_FILE" ]; then
            print_error "Configuration file not found: $CONFIG_FILE"
            exit 1
        fi
        
        # Basic JSON validation
        if jq empty "$CONFIG_FILE" 2>/dev/null; then
            print_success "Valid JSON format"
            
            # Check required fields
            if jq -e '.name and .rag_type and .sources' "$CONFIG_FILE" >/dev/null; then
                print_success "Required fields present"
                
                # Count sources
                source_count=$(jq '.sources | length' "$CONFIG_FILE")
                print_success "Found $source_count sources"
                
                # List source types
                echo "Source types:"
                jq -r '.sources[] | "  - \(.source_id) (\(.source_type))"' "$CONFIG_FILE"
                
            else
                print_error "Missing required fields (name, rag_type, sources)"
                exit 1
            fi
        else
            print_error "Invalid JSON format"
            exit 1
        fi
        ;;
        
    "help"|"-h"|"--help")
        print_header "CONFIGURATION ADMIN HELPER"
        cat << EOF

Usage: $0 <command> [arguments]

Commands:
    upload <file> [name] [desc]  Upload configuration file to PostgreSQL
    list                         List all stored configurations  
    show <name> [--full]         Show configuration details
    deploy <name>                Deploy configuration to create KB
    export <name> <file>         Export configuration to file
    delete <name>                Delete (archive) configuration
    summary                      Show configuration statistics
    validate <file>              Validate configuration file format
    bulk-upload [dir]            Upload all JSON files from directory
    help                         Show this help message

Examples:
    $0 upload configs/production.json prod-kb "Production knowledge base"
    $0 list
    $0 show prod-kb --full
    $0 deploy prod-kb
    $0 export prod-kb backup.json
    $0 bulk-upload configs/
    $0 validate new_config.json

Configuration files are stored in PostgreSQL with version control,
deployment tracking, and audit trails.

EOF
        ;;
        
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac