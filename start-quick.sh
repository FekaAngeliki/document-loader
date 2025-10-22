#!/bin/bash
# Quick start script - web service only

cd /mnt/c/Users/E41297/Documents/NBG/document-loader

echo "🚀 Quick Start: Document Loader Web Service"
echo "🌐 Web Service: http://localhost:8080"  
echo "📋 API Docs: http://localhost:8080/docs"
echo ""

# Start web service in background
source .venv/bin/activate
cd web_service && python -m app.main &

echo "✅ Web service starting..."
echo "⏳ Wait 10 seconds then access: http://localhost:8080/docs"
echo "🛑 Press Ctrl+C to stop the service"

# Wait for user to stop
wait