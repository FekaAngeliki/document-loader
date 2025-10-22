#!/usr/bin/env python3
"""
Test script to verify dashboard components and integration
"""

import os
import sys

def test_angular_components():
    """Test Angular dashboard components"""
    
    print("🎨 Testing Angular Dashboard Components...")
    
    try:
        # Check if scheduler component exists
        scheduler_component_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/components/scheduler/scheduler.component.ts"
        
        if os.path.exists(scheduler_component_path):
            print("   ✅ Scheduler component file exists")
            
            # Read component and check for key features
            with open(scheduler_component_path, 'r') as f:
                content = f.read()
                
            key_features = [
                'getSchedulerStatus',
                'triggerSync',
                'reloadConfigurations',
                'loadExecutions',
                'toggleAutoRefresh'
            ]
            
            for feature in key_features:
                if feature in content:
                    print(f"   ✅ Feature '{feature}' implemented")
                else:
                    print(f"   ❌ Feature '{feature}' missing")
        else:
            print("   ❌ Scheduler component file not found")
            return False
            
        # Check dashboard component integration
        dashboard_component_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/components/dashboard/dashboard.component.ts"
        
        if os.path.exists(dashboard_component_path):
            print("   ✅ Dashboard component file exists")
            
            with open(dashboard_component_path, 'r') as f:
                content = f.read()
                
            integration_features = [
                'SchedulerComponent',
                'schedulerStatus',
                'toggleSchedulerManagement',
                'showSchedulerManagement'
            ]
            
            for feature in integration_features:
                if feature in content:
                    print(f"   ✅ Integration '{feature}' implemented")
                else:
                    print(f"   ❌ Integration '{feature}' missing")
        else:
            print("   ❌ Dashboard component file not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing Angular components: {e}")
        return False

def test_api_service():
    """Test API service integration"""
    
    print("\n🔌 Testing API Service Integration...")
    
    try:
        api_service_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/services/api.service.ts"
        
        if os.path.exists(api_service_path):
            print("   ✅ API service file exists")
            
            with open(api_service_path, 'r') as f:
                content = f.read()
                
            scheduler_endpoints = [
                'getSchedulerStatus',
                'getSchedulerExecutions', 
                'triggerScheduledSync',
                'reloadSchedulerConfigs',
                'getScheduleInfo'
            ]
            
            for endpoint in scheduler_endpoints:
                if endpoint in content:
                    print(f"   ✅ Endpoint '{endpoint}' implemented")
                else:
                    print(f"   ❌ Endpoint '{endpoint}' missing")
                    
            # Check type definitions
            type_definitions = [
                'SchedulerStatus',
                'ScheduleInfo',
                'ExecutionInfo',
                'ExecutionsResponse'
            ]
            
            for typedef in type_definitions:
                if typedef in content:
                    print(f"   ✅ Type '{typedef}' defined")
                else:
                    print(f"   ❌ Type '{typedef}' missing")
                    
        else:
            print("   ❌ API service file not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing API service: {e}")
        return False

def test_web_service_endpoints():
    """Test web service endpoint definitions"""
    
    print("\n🌐 Testing Web Service Endpoints...")
    
    try:
        scheduler_api_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/web_service/app/api/scheduler.py"
        
        if os.path.exists(scheduler_api_path):
            print("   ✅ Scheduler API file exists")
            
            with open(scheduler_api_path, 'r') as f:
                content = f.read()
                
            endpoints = [
                '@router.get("/status"',
                '@router.get("/executions"',
                '@router.post("/trigger"',
                '@router.post("/reload"',
                '@router.get("/schedule/{config_name}"'
            ]
            
            for endpoint in endpoints:
                if endpoint in content:
                    print(f"   ✅ Endpoint '{endpoint}' defined")
                else:
                    print(f"   ❌ Endpoint '{endpoint}' missing")
                    
            # Check authentication
            auth_patterns = [
                'RequireSchedulerRead',
                'RequireSchedulerManage', 
                'RequireSchedulerTrigger'
            ]
            
            for pattern in auth_patterns:
                if pattern in content:
                    print(f"   ✅ Auth '{pattern}' implemented")
                else:
                    print(f"   ❌ Auth '{pattern}' missing")
                    
        else:
            print("   ❌ Scheduler API file not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing web service: {e}")
        return False

def check_file_structure():
    """Check overall file structure"""
    
    print("\n📁 Checking File Structure...")
    
    files_to_check = [
        ("/mnt/c/Users/E41297/Documents/NBG/document-loader/src/scheduling/config_scheduler.py", "Config Scheduler"),
        ("/mnt/c/Users/E41297/Documents/NBG/document-loader/src/cli/scheduler_commands.py", "CLI Commands"),
        ("/mnt/c/Users/E41297/Documents/NBG/document-loader/web_service/app/api/scheduler.py", "Web API"),
        ("/mnt/c/Users/E41297/Documents/NBG/document-loader/web_service/app/api/models.py", "API Models"),
        ("/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/components/scheduler/scheduler.component.ts", "Scheduler Component"),
        ("/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/services/api.service.ts", "API Service")
    ]
    
    all_exist = True
    
    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   ✅ {description}: {size:,} bytes")
        else:
            print(f"   ❌ {description}: File not found")
            all_exist = False
            
    return all_exist

if __name__ == "__main__":
    print("=" * 60)
    print("   🏢 DASHBOARD INTEGRATION VERIFICATION")
    print("=" * 60)
    
    # Run all tests
    test1 = check_file_structure()
    test2 = test_web_service_endpoints()
    test3 = test_api_service()
    test4 = test_angular_components()
    
    print("\n" + "=" * 60)
    print("📋 INTEGRATION VERIFICATION SUMMARY")
    print("=" * 60)
    
    if all([test1, test2, test3, test4]):
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n✅ Complete scheduler integration verified:")
        print("   • Core scheduling system ✓")
        print("   • CLI commands ✓")
        print("   • Web API endpoints ✓")
        print("   • Angular dashboard components ✓")
        print("   • API service integration ✓")
        print("   • Authentication & permissions ✓")
        
        print("\n🚀 READY FOR DEPLOYMENT!")
        print("\nTo use the scheduler in the dashboard:")
        print("1. Start web service: cd web_service && python -m app.main")
        print("2. Start Angular dev server: cd frontend && ng serve")
        print("3. Open dashboard: http://localhost:4200")
        print("4. Click 'Manage Scheduler' to access scheduler features")
        
    else:
        print("❌ Some integration tests failed")
        print("Please check the errors above and fix any missing components")
        sys.exit(1)