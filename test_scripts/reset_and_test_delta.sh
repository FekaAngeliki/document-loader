#!/bin/bash
# Script to reset database and test delta sync with specific date context

echo "🧪 DELTA SYNC DATE TESTING SCRIPT"
echo "=================================="
echo ""
echo "🗓️  SCENARIO:"
echo "   📅 Step 1: Reset database (clean slate for 2025-01-01 baseline)"
echo "   📅 Step 2: Execute 'Initial Sync' (represents 2025-01-01)"
echo "   📅 Step 3: Execute 'Delta Sync' (represents 2025-09-24)"
echo ""

# Check if environment variables are set
if [[ -z "$SHAREPOINT_TENANT_ID" || -z "$SHAREPOINT_CLIENT_ID" || -z "$SHAREPOINT_CLIENT_SECRET" ]]; then
    echo "⚠️  WARNING: SharePoint environment variables not set"
    echo "🔧 Required variables:"
    echo "   SHAREPOINT_TENANT_ID"
    echo "   SHAREPOINT_CLIENT_ID" 
    echo "   SHAREPOINT_CLIENT_SECRET"
    echo ""
    echo "📊 Current database state (showing recent sync runs):"
    source .venv/bin/activate
    document-loader db sync-runs --limit 3
    echo ""
    echo "💡 To run actual test:"
    echo "   1. Set environment variables"
    echo "   2. Run: bash test_scripts/reset_and_test_delta.sh"
    exit 1
fi

echo "✅ Environment variables are set"
echo ""

# Activate virtual environment
source .venv/bin/activate

echo "📊 CURRENT DATABASE STATE (before reset):"
echo "=========================================="
document-loader db sync-runs --limit 3
document-loader db stats
echo ""

read -p "⚠️  Do you want to RESET the database? This will delete all sync runs and file records. (y/N): " confirm

if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
    echo "❌ Database reset cancelled. Exiting."
    exit 1
fi

echo ""
echo "🗑️  RESETTING DATABASE..."
echo "=========================="

# Clean up existing records (using the cleanup command)
echo "🧹 Running database cleanup..."
document-loader db cleanup --force

echo ""
echo "📊 DATABASE STATE AFTER CLEANUP:"
echo "================================="
document-loader db sync-runs --limit 3
document-loader db stats
echo ""

echo "🎬 STEP 1: BASELINE SYNC (representing 2025-01-01)"
echo "=================================================="
echo "📅 Context: This sync represents the initial comprehensive sync on January 1, 2025"
echo "🔄 Executing sync..."
echo ""

start_time=$(date)
echo "⏰ Start time: $start_time"

# Execute the initial sync
if document-loader multi-source sync-multi-kb --config-name PremiumRMs-kb --sync-mode parallel; then
    echo ""
    echo "✅ BASELINE SYNC COMPLETED"
    echo "=========================="
    end_time=$(date)
    echo "⏰ End time: $end_time"
    
    echo ""
    echo "📊 Database state after baseline sync:"
    document-loader db sync-runs --limit 1
    document-loader db stats
    
    echo ""
    echo "⏳ Waiting 15 seconds before delta sync (to ensure different timestamps)..."
    sleep 15
    
    echo ""
    echo "🎬 STEP 2: DELTA SYNC (representing 2025-09-24)"
    echo "==============================================="
    echo "📅 Context: This sync represents delta changes detected on September 24, 2025"
    echo "🔍 Expected: Most files should be detected as UNCHANGED (modification date optimization)"
    echo "🔄 Executing delta sync..."
    echo ""
    
    delta_start_time=$(date)
    echo "⏰ Delta start time: $delta_start_time"
    
    # Execute the delta sync
    if document-loader multi-source sync-multi-kb --config-name PremiumRMs-kb --sync-mode parallel; then
        echo ""
        echo "✅ DELTA SYNC COMPLETED"
        echo "======================="
        delta_end_time=$(date)
        echo "⏰ Delta end time: $delta_end_time"
        
        echo ""
        echo "📊 FINAL DATABASE STATE:"
        echo "========================"
        document-loader db sync-runs --limit 2
        document-loader db stats
        
        echo ""
        echo "📈 ANALYSIS:"
        echo "============"
        echo "📊 Check the sync run results above to compare:"
        echo "   • Baseline sync: Should show all files as NEW"
        echo "   • Delta sync: Should show most files as UNCHANGED"
        echo "   • Delta sync should be significantly faster"
        echo ""
        echo "✅ DATE-SPECIFIC DELTA SYNC TEST COMPLETED"
        echo "🎯 This demonstrates delta sync efficiency between"
        echo "   2025-01-01 (baseline) and 2025-09-24 (delta)"
        
    else
        echo "❌ Delta sync failed"
        exit 1
    fi
    
else
    echo "❌ Baseline sync failed"
    exit 1
fi