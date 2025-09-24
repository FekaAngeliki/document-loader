#!/bin/bash
# Environment setup script for Document Loader
# Usage: source setup_env.sh

# Load environment variables
if [ -f .env ]; then
    source .env
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  .env file not found"
fi

# Add document-loader to PATH if it exists
if [ -f "/home/e41297/.local/bin/document-loader" ]; then
    export PATH="/home/e41297/.local/bin:$PATH"
    echo "✅ Added document-loader to PATH"
else
    echo "⚠️  document-loader not found, please run: pip install -e . --break-system-packages"
fi

# Show available commands
echo ""
echo "🚀 Available multi-source commands:"
echo "  document-loader multi-source create-template <name> --container-name <name>"
echo "  document-loader multi-source create-multi-kb --config-file <config.json>"
echo "  document-loader multi-source list-multi-kb"
echo "  document-loader multi-source status-multi-kb --config-file <config.json>"
echo "  document-loader multi-source sync-multi-kb --config-file <config.json>"
echo "  document-loader multi-source delete-multi-kb --name <kb-name>"
echo "  document-loader multi-source delete-multi-kb --config-file <config.json>"
echo ""
echo "📚 For help: document-loader --help"
echo "📚 For multi-source help: document-loader multi-source --help"