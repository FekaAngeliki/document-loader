#!/usr/bin/env python3
"""
Check dashboard component for visibility issues
"""

import os
import re

def analyze_dashboard_component():
    """Analyze the dashboard component for potential visibility issues"""
    
    print("🔍 Analyzing Dashboard Component...")
    
    dashboard_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/components/dashboard/dashboard.component.ts"
    
    if not os.path.exists(dashboard_path):
        print("❌ Dashboard component file not found!")
        return False
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("\n📊 Analysis Results:")
    
    # Check for scheduler status section
    if "Scheduler Status" in content:
        print("✅ Scheduler Status section found in template")
    else:
        print("❌ Scheduler Status section NOT found in template")
        return False
    
    # Check for Manage Scheduler button
    if "Manage Scheduler" in content:
        print("✅ 'Manage Scheduler' button found in template")
    else:
        print("❌ 'Manage Scheduler' button NOT found in template")
        return False
    
    # Check for conditional rendering on scheduler section
    scheduler_section_match = re.search(r'<!-- Scheduler Status Row -->(.*?)<!-- Quick Actions -->', content, re.DOTALL)
    
    if scheduler_section_match:
        scheduler_section = scheduler_section_match.group(1)
        if '*ngIf' in scheduler_section:
            ngif_matches = re.findall(r'\*ngIf="([^"]*)"', scheduler_section)
            print(f"⚠️  Scheduler section has conditional rendering: {ngif_matches}")
        else:
            print("✅ Scheduler section has NO conditional rendering - should always be visible")
    
    # Check for toggleSchedulerManagement function
    if "toggleSchedulerManagement" in content:
        print("✅ toggleSchedulerManagement function found")
    else:
        print("❌ toggleSchedulerManagement function NOT found")
        return False
    
    # Check for schedulerStatus property
    if "schedulerStatus" in content:
        print("✅ schedulerStatus property found")
    else:
        print("❌ schedulerStatus property NOT found")
        return False
    
    # Check for API service import
    if "ApiService" in content:
        print("✅ ApiService imported")
    else:
        print("❌ ApiService NOT imported")
        return False
    
    # Check for getSchedulerStatus call
    if "getSchedulerStatus" in content:
        print("✅ getSchedulerStatus API call found")
    else:
        print("❌ getSchedulerStatus API call NOT found")
        return False
    
    print(f"\n📏 Component size: {len(content):,} characters")
    
    return True

def check_component_imports():
    """Check if the component properly imports dependencies"""
    
    print("\n🔗 Checking Component Imports...")
    
    dashboard_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/components/dashboard/dashboard.component.ts"
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_imports = [
        'CommonModule',
        'SchedulerComponent',
        'ApiService'
    ]
    
    for import_name in required_imports:
        if import_name in content:
            print(f"✅ {import_name} imported")
        else:
            print(f"❌ {import_name} NOT imported")

def check_html_structure():
    """Check the HTML structure for proper Bootstrap classes"""
    
    print("\n🎨 Checking HTML Structure...")
    
    dashboard_path = "/mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/src/app/components/dashboard/dashboard.component.ts"
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Extract template content
    template_match = re.search(r'template:\s*`(.*?)`', content, re.DOTALL)
    
    if template_match:
        template = template_match.group(1)
        
        # Check for Bootstrap classes
        bootstrap_checks = [
            ('row g-4 mb-4', 'Bootstrap row with spacing'),
            ('card border-dark', 'Dark bordered card'),
            ('btn btn-outline-primary', 'Primary outline button'),
            ('bi bi-gear', 'Bootstrap icon for gear'),
        ]
        
        for class_name, description in bootstrap_checks:
            if class_name in template:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} NOT found")
        
        # Check for the specific button structure
        if 'toggleSchedulerManagement()' in template:
            print("✅ Button click handler found")
        else:
            print("❌ Button click handler NOT found")
            
        return True
    else:
        print("❌ Could not extract template content")
        return False

def provide_troubleshooting_steps():
    """Provide troubleshooting steps"""
    
    print("\n🛠️  TROUBLESHOOTING STEPS:")
    print("=" * 50)
    
    print("\n1. 📂 Open the debug HTML file:")
    print("   Open: /mnt/c/Users/E41297/Documents/NBG/document-loader/frontend/debug-dashboard.html")
    print("   This should show you exactly what the scheduler section looks like")
    
    print("\n2. 🔍 Check Angular Console:")
    print("   - Open browser DevTools (F12)")
    print("   - Look for JavaScript errors in Console tab")
    print("   - Check if API calls are failing")
    
    print("\n3. 📡 Verify API Service:")
    print("   - Check if web service is running on http://localhost:8080")
    print("   - Test API endpoint: http://localhost:8080/api/v1/scheduler/status")
    
    print("\n4. 🔧 Angular Development Server:")
    print("   - Make sure Angular dev server is running: ng serve")
    print("   - Check for compilation errors in terminal")
    
    print("\n5. 🎯 Manual Browser Test:")
    print("   - Open: http://localhost:4200")
    print("   - Look for dark section titled 'Scheduler Status'")
    print("   - The 'Manage Scheduler' button should be in the 4th column")
    
    print("\n6. 📱 Responsive Design:")
    print("   - If on mobile/small screen, button might be stacked vertically")
    print("   - Try expanding browser window or using desktop view")

if __name__ == "__main__":
    print("=" * 60)
    print("   🔍 DASHBOARD VISIBILITY DIAGNOSTIC")
    print("=" * 60)
    
    success = analyze_dashboard_component()
    check_component_imports()
    check_html_structure()
    
    if success:
        print("\n✅ Component analysis complete - no obvious issues found")
        print("The 'Manage Scheduler' button SHOULD be visible")
    else:
        print("\n❌ Component analysis found issues")
    
    provide_troubleshooting_steps()