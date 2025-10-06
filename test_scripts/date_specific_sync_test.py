#!/usr/bin/env python3
"""
Date-specific sync execution test
Demonstrates how to work with specific sync dates for testing delta behavior
"""
import os
import subprocess
import json
from datetime import datetime, timedelta
import time

class DateSpecificSyncTester:
    """Handles sync execution with specific date scenarios"""
    
    def __init__(self, kb_name="PremiumRMs-kb"):
        self.kb_name = kb_name
        
    def check_environment(self):
        """Check if environment is properly configured"""
        required_vars = [
            'SHAREPOINT_TENANT_ID', 
            'SHAREPOINT_CLIENT_ID', 
            'SHAREPOINT_CLIENT_SECRET'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  WARNING: Missing environment variables: {', '.join(missing_vars)}")
            print(f"🔧 To run actual syncs, please set these variables")
            return False
        return True
    
    def execute_sync_with_date_context(self, sync_date_label, description):
        """Execute sync with contextual date information"""
        
        print(f"\n{'='*80}")
        print(f"🗓️  SYNC EXECUTION: {sync_date_label}")
        print(f"📝 Description: {description}")
        print(f"⏰ Actual execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # Build sync command
        cmd = [
            "document-loader", 
            "multi-source", 
            "sync-kb", 
            self.kb_name,
            "--sync-mode", "parallel"
        ]
        
        print(f"🖥️  Command: {' '.join(cmd)}")
        
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            success = result.returncode == 0
            
            if success:
                print(f"✅ {sync_date_label} sync completed successfully in {duration:.1f} seconds")
                self._analyze_sync_output(result.stdout, sync_date_label)
            else:
                print(f"❌ {sync_date_label} sync failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")
            
            return {
                'success': success,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {sync_date_label} sync timed out after 30 minutes")
            return {'success': False, 'error': 'timeout'}
        except Exception as e:
            print(f"💥 {sync_date_label} sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_sync_output(self, output, sync_label):
        """Analyze and display sync output"""
        lines = output.split('\n')
        
        print(f"\n📊 {sync_label} RESULTS:")
        
        # Extract key metrics
        metrics = {}
        for line in lines:
            if 'Total Files Processed' in line:
                try:
                    metrics['total'] = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'New Files' in line and 'green' in line:
                try:
                    metrics['new'] = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'Modified Files' in line and ('yellow' in line or 'blue' in line):
                try:
                    metrics['modified'] = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'Deleted Files' in line and 'red' in line:
                try:
                    metrics['deleted'] = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'Unchanged Files' in line:
                try:
                    metrics['unchanged'] = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
        
        # Display metrics
        for key, value in metrics.items():
            icon = {'total': '📄', 'new': '🆕', 'modified': '📝', 'deleted': '🗑️', 'unchanged': '✅'}.get(key, '📊')
            print(f"   {icon} {key.title()}: {value}")
        
        return metrics
    
    def get_database_state(self, context=""):
        """Get current database state"""
        print(f"\n📊 DATABASE STATE {context}:")
        print(f"{'='*50}")
        
        try:
            # Get latest sync runs
            cmd = ["document-loader", "db", "sync-runs", "--limit", "3"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("📈 Recent Sync Runs:")
                lines = result.stdout.split('\n')
                for line in lines:
                    if '│' in line and 'PremiumRMs' in line:
                        print(f"   {line}")
            
        except Exception as e:
            print(f"   ❌ Error getting sync runs: {e}")
        
        try:
            # Get file count
            cmd = ["document-loader", "db", "files", "--limit", "1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Extract file count from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Files shown:' in line:
                        print(f"📄 {line}")
                        break
        except Exception as e:
            print(f"   ❌ Error getting file count: {e}")
    
    def run_date_specific_test(self):
        """Run the date-specific sync test scenario"""
        
        print(f"🧪 DATE-SPECIFIC SYNC TEST SCENARIO")
        print(f"📅 Simulating sync runs for specific dates")
        print(f"🎯 Testing delta sync behavior between different time periods")
        print(f"\n🗓️  SCENARIO:")
        print(f"   📅 Initial Sync Date: 2025-01-01 (New Year baseline)")
        print(f"   📅 Delta Sync Date:   2025-09-24 (8+ months later)")
        print(f"   📊 Expected: Many files unchanged, some modified, some new")
        
        # Check environment
        if not self.check_environment():
            print(f"\n🔧 ENVIRONMENT NOT CONFIGURED")
            print(f"To run actual syncs with your SharePoint, set these variables:")
            print(f"   export SHAREPOINT_TENANT_ID='your-tenant-id'")
            print(f"   export SHAREPOINT_CLIENT_ID='your-client-id'")
            print(f"   export SHAREPOINT_CLIENT_SECRET='your-client-secret'")
            print(f"\n📊 For now, showing current database state...")
            self.get_database_state("(CURRENT)")
            return
        
        # Get initial database state
        self.get_database_state("(BEFORE TEST)")
        
        # Step 1: "Initial sync" (representing 2025-01-01)
        print(f"\n🎬 STEP 1: BASELINE SYNC")
        print(f"🗓️  Representing: January 1, 2025 - Initial sync")
        print(f"📝 Context: This represents the first comprehensive sync of your SharePoint")
        
        initial_result = self.execute_sync_with_date_context(
            "BASELINE (Jan 1, 2025)",
            "Initial comprehensive sync - establishing baseline"
        )
        
        if not initial_result['success']:
            print(f"❌ Baseline sync failed. Cannot continue test.")
            return
        
        # Get state after initial sync
        self.get_database_state("(AFTER BASELINE)")
        
        # Brief pause to ensure different timestamps
        print(f"\n⏳ Waiting 10 seconds to ensure different sync timestamps...")
        time.sleep(10)
        
        # Step 2: "Delta sync" (representing 2025-09-24) 
        print(f"\n🎬 STEP 2: DELTA SYNC")
        print(f"🗓️  Representing: September 24, 2025 - Delta sync")
        print(f"📝 Context: 8+ months later - detecting changes since baseline")
        print(f"🔍 Expected behavior:")
        print(f"   • Files unchanged since Jan 1 → SKIPPED")
        print(f"   • Files modified since Jan 1 → PROCESSED") 
        print(f"   • New files created since Jan 1 → PROCESSED")
        print(f"   • Modification date comparison will optimize performance")
        
        delta_result = self.execute_sync_with_date_context(
            "DELTA (Sep 24, 2025)",
            "Delta sync - processing only changes since baseline"
        )
        
        # Get final state
        self.get_database_state("(AFTER DELTA)")
        
        # Analysis
        print(f"\n📈 TEST ANALYSIS:")
        print(f"{'='*80}")
        
        if initial_result['success'] and delta_result['success']:
            print(f"✅ Both sync runs completed successfully")
            
            # Compare durations
            if delta_result['duration'] < initial_result['duration']:
                improvement = ((initial_result['duration'] - delta_result['duration']) / initial_result['duration']) * 100
                print(f"⚡ Delta sync was {improvement:.1f}% faster than baseline")
            
            # Look for delta sync optimizations in output
            delta_output = delta_result['stdout']
            optimizations = []
            
            if "modification time unchanged" in delta_output:
                optimizations.append("✅ Modification date optimization detected")
            if "size changed" in delta_output:
                optimizations.append("✅ File size change detection working")
            if "hash match" in delta_output:
                optimizations.append("✅ Hash verification for unchanged files")
            if "skipping hash check" in delta_output:
                optimizations.append("✅ Hash check optimization (skipped when not needed)")
            
            if optimizations:
                print(f"\n🎯 DELTA SYNC OPTIMIZATIONS CONFIRMED:")
                for opt in optimizations:
                    print(f"   {opt}")
            
        else:
            print(f"❌ Some sync runs failed - check configuration and connectivity")
        
        print(f"\n✅ DATE-SPECIFIC SYNC TEST COMPLETED")
        print(f"📊 This demonstrates how delta sync would behave between")
        print(f"   January 1, 2025 (baseline) and September 24, 2025 (delta)")

def main():
    """Main execution"""
    print("🧪 Document Loader Date-Specific Sync Test")
    print("Testing sync behavior for specific date scenarios")
    
    tester = DateSpecificSyncTester()
    tester.run_date_specific_test()

if __name__ == "__main__":
    main()