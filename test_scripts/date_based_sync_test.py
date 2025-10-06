#!/usr/bin/env python3
"""
Date-based sync execution test script
Tests delta sync behavior by running sync at different dates
"""
import os
import subprocess
import json
from datetime import datetime, timedelta
import time

class DateBasedSyncTester:
    """Handles date-based sync testing"""
    
    def __init__(self, kb_name="PremiumRMs-kb"):
        self.kb_name = kb_name
        self.test_start_time = datetime.now()
        self.sync_results = []
    
    def run_sync_command(self, sync_type="full", additional_args=None):
        """Execute the sync command and capture results"""
        
        print(f"\n{'='*60}")
        print(f"🔄 EXECUTING {sync_type.upper()} SYNC")
        print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📚 Knowledge Base: {self.kb_name}")
        print(f"{'='*60}")
        
        # Build command
        cmd = [
            "document-loader", 
            "multi-source", 
            "sync-kb", 
            self.kb_name
        ]
        
        if additional_args:
            cmd.extend(additional_args)
        
        print(f"🖥️  Command: {' '.join(cmd)}")
        print("\n📊 SYNC EXECUTION:")
        
        start_time = datetime.now()
        
        try:
            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Parse and display results
            success = result.returncode == 0
            
            sync_result = {
                'sync_type': sync_type,
                'timestamp': start_time.isoformat(),
                'duration_seconds': duration,
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            self.sync_results.append(sync_result)
            
            if success:
                print(f"✅ Sync completed successfully in {duration:.1f} seconds")
                self._parse_sync_output(result.stdout)
            else:
                print(f"❌ Sync failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")
            
            return sync_result
            
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"⏰ Sync timed out after {duration:.1f} seconds")
            
            return {
                'sync_type': sync_type,
                'timestamp': start_time.isoformat(),
                'duration_seconds': duration,
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': 'Timeout after 30 minutes'
            }
        
        except Exception as e:
            print(f"💥 Sync failed with exception: {e}")
            return {
                'sync_type': sync_type,
                'timestamp': start_time.isoformat(),
                'duration_seconds': 0,
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def _parse_sync_output(self, output):
        """Parse and display key metrics from sync output"""
        lines = output.split('\n')
        
        # Look for key metrics in the output
        for line in lines:
            if 'Total Files Processed' in line:
                print(f"📄 {line.strip()}")
            elif 'New Files' in line and 'green' in line:
                print(f"🆕 {line.strip()}")
            elif 'Modified Files' in line and ('yellow' in line or 'blue' in line):
                print(f"📝 {line.strip()}")
            elif 'Deleted Files' in line and 'red' in line:
                print(f"🗑️  {line.strip()}")
            elif 'Total Errors' in line:
                print(f"⚠️  {line.strip()}")
            elif 'Duration' in line and 'seconds' in line:
                print(f"⏱️  {line.strip()}")
    
    def get_database_statistics(self):
        """Get current database statistics"""
        print(f"\n📊 DATABASE STATISTICS:")
        print(f"{'='*40}")
        
        try:
            # Get sync runs
            cmd = ["document-loader", "db", "sync-runs", "--limit", "3"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("📈 Recent Sync Runs:")
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('=') and 'Sync Runs' not in line:
                        print(f"   {line}")
            
        except Exception as e:
            print(f"   ❌ Error getting sync runs: {e}")
        
        try:
            # Get file statistics
            cmd = ["document-loader", "db", "files", "--limit", "5"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"\n📄 Recent Files:")
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('=') and 'File Records' not in line:
                        print(f"   {line}")
            
        except Exception as e:
            print(f"   ❌ Error getting file records: {e}")
    
    def wait_for_time_change(self, seconds=5):
        """Wait for time to change to ensure different timestamps"""
        print(f"\n⏳ Waiting {seconds} seconds to ensure different timestamps...")
        time.sleep(seconds)
    
    def run_date_based_test(self):
        """Run the complete date-based sync test"""
        
        print(f"🧪 DATE-BASED DELTA SYNC TEST")
        print(f"📅 Test started: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Testing delta sync behavior with time-based changes")
        
        # Step 1: Initial sync (full sync)
        print(f"\n" + "="*80)
        print(f"STEP 1: INITIAL FULL SYNC")
        print(f"="*80)
        
        initial_sync = self.run_sync_command("initial_full")
        
        if not initial_sync['success']:
            print(f"❌ Initial sync failed. Cannot continue test.")
            return
        
        # Get baseline statistics
        self.get_database_statistics()
        
        # Wait to ensure different timestamps
        self.wait_for_time_change(10)
        
        # Step 2: Delta sync (should detect changes based on modification dates)
        print(f"\n" + "="*80)
        print(f"STEP 2: DELTA SYNC")
        print(f"="*80)
        print(f"🔍 This will detect changes using:")
        print(f"   • File size comparison")
        print(f"   • SharePoint modification date comparison") 
        print(f"   • Hash calculation (only when needed)")
        
        delta_sync = self.run_sync_command("delta")
        
        # Get updated statistics
        self.get_database_statistics()
        
        # Step 3: Analysis and Summary
        print(f"\n" + "="*80)
        print(f"STEP 3: ANALYSIS AND SUMMARY")
        print(f"="*80)
        
        self.analyze_results()
    
    def analyze_results(self):
        """Analyze the test results"""
        
        if len(self.sync_results) < 2:
            print(f"❌ Insufficient sync results for analysis")
            return
        
        initial = self.sync_results[0]
        delta = self.sync_results[1]
        
        print(f"📊 SYNC COMPARISON:")
        print(f"   Initial Sync Duration: {initial['duration_seconds']:.1f}s")
        print(f"   Delta Sync Duration:   {delta['duration_seconds']:.1f}s")
        
        if delta['duration_seconds'] < initial['duration_seconds']:
            improvement = ((initial['duration_seconds'] - delta['duration_seconds']) / initial['duration_seconds']) * 100
            print(f"   ⚡ Performance Improvement: {improvement:.1f}% faster")
        
        print(f"\n🔍 DELTA SYNC BEHAVIOR:")
        if "modification time unchanged" in delta['stdout']:
            print(f"   ✅ Modification date optimization working")
        if "size changed" in delta['stdout']:
            print(f"   ✅ File size optimization working")
        if "hash match" in delta['stdout']:
            print(f"   ✅ Hash comparison working for unchanged files")
        if "hash mismatch" in delta['stdout']:
            print(f"   ✅ Hash comparison detected content changes")
        
        print(f"\n📈 EFFECTIVENESS:")
        # Look for unchanged file count in output
        unchanged_count = 0
        modified_count = 0
        
        for line in delta['stdout'].split('\n'):
            if 'Unchanged Files' in line:
                try:
                    unchanged_count = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'Modified Files' in line:
                try:
                    modified_count = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
        
        if unchanged_count > 0:
            print(f"   📄 {unchanged_count} files skipped (no changes detected)")
            print(f"   🚀 Bandwidth and processing saved for unchanged files")
        
        if modified_count > 0:
            print(f"   📝 {modified_count} files processed (changes detected)")
        
        print(f"\n✅ TEST COMPLETED")
        print(f"⏱️  Total test duration: {(datetime.now() - self.test_start_time).total_seconds():.1f} seconds")

def main():
    """Main execution function"""
    
    print("🧪 Document Loader Date-Based Delta Sync Test")
    print("=" * 60)
    
    # Check if environment is configured
    required_env_vars = [
        'SHAREPOINT_TENANT_ID', 
        'SHAREPOINT_CLIENT_ID', 
        'SHAREPOINT_CLIENT_SECRET'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  WARNING: Missing environment variables: {', '.join(missing_vars)}")
        print(f"🔧 Please set these variables to run the test")
        return
    
    # Create tester and run test
    tester = DateBasedSyncTester()
    tester.run_date_based_test()

if __name__ == "__main__":
    main()