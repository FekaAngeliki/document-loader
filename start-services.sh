#!/bin/bash
# Start web service only

echo "🚀 Starting Document Loader Web Service..."
echo "=" * 50

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to handle cleanup on script exit
cleanup() {
    echo -e "\n🛑 Stopping web service..."
    # Kill background processes
    if [ ! -z "$WEB_SERVICE_PID" ]; then
        kill $WEB_SERVICE_PID 2>/dev/null
        echo "   ✓ Web service stopped"
    fi
    echo "👋 Service stopped. Goodbye!"
    exit 0
}

# Set up signal handlers for cleanup
trap cleanup SIGINT SIGTERM

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Start web service in background
echo "🌐 Starting web service on port 8080..."
cd web_service
python -m app.main &
WEB_SERVICE_PID=$!
cd ..

# Wait for service to be ready
echo "⏳ Waiting for service to start..."
sleep 5

# Test if service is running
echo "🔍 Testing service..."

# Test web service
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "   ✅ Web service running at: http://localhost:8080"
else
    echo "   ❌ Web service not responding"
fi

echo ""
echo "🎯 Service is ready!"
echo "=" * 50
echo "🌐 API Endpoints:"
echo "   • Health:     http://localhost:8080/health"
echo "   • Scheduler:  http://localhost:8080/api/v1/scheduler/status"
echo "   • Connectivity: http://localhost:8080/connectivity/systems"
echo "   • Docs:       http://localhost:8080/docs"
echo ""
echo "📋 CLI Commands:"
echo "   • document-loader scheduler status"
echo "   • document-loader scheduler start"
echo "   • document-loader connectivity check --rag-type mock"
echo ""
echo "🛑 Press Ctrl+C to stop the service"
echo "⏳ Service running..."

# Keep script running and wait for Ctrl+C
while true; do
    sleep 1
done