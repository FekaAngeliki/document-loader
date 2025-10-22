# 🎯 Scheduler Integration Guide

## 📋 **Integration Options Overview**

You have **4 main ways** to integrate the scheduler with your existing dashboard:

---

## 🚀 **Option 1: API Integration (Recommended)**

**Best for:** Full control, custom UI, existing JavaScript dashboards

### **Quick Start:**
```javascript
// Include the API client
const schedulerAPI = new SchedulerAPIClient('http://localhost:8080/api/v1');

// Add to your existing dashboard
async function addSchedulerToMyDashboard() {
    const status = await schedulerAPI.getSchedulerStatus();
    
    // Update your existing elements
    document.getElementById('scheduler-status').textContent = 
        status.data.running ? 'Running' : 'Stopped';
    document.getElementById('active-schedules').textContent = 
        status.data.active_schedules;
}
```

### **Files to use:**
- `/integration_examples/api_integration.js` - Complete API client
- Copy the `SchedulerAPIClient` class to your project
- Call `quickIntegrateScheduler()` to add scheduler section

### **What you get:**
- ✅ Full control over UI/UX
- ✅ Seamless integration with existing code
- ✅ Real-time data from API
- ✅ Custom styling and layout

---

## 🖼️ **Option 2: iframe Integration**

**Best for:** Quick integration, separate scheduler interface

### **Quick Start:**
```html
<!-- Add to your existing dashboard -->
<div class="card">
    <div class="card-header">
        <h5>Scheduler Management</h5>
    </div>
    <div class="card-body p-0">
        <iframe 
            src="http://localhost:4200/real-dashboard.html" 
            width="100%" 
            height="600px"
            style="border: none;">
        </iframe>
    </div>
</div>
```

### **Files to use:**
- `/integration_examples/iframe_integration.html` - Complete example
- `/frontend/real-dashboard.html` - Scheduler interface

### **What you get:**
- ✅ Zero coding required
- ✅ Complete scheduler interface
- ✅ Isolated from your existing code
- ✅ Expandable/collapsible

---

## 🧩 **Option 3: Component Integration**

**Best for:** Native dashboard feel, modular approach

### **Quick Start:**
```html
<!-- Add scheduler widget to your dashboard -->
<div class="col-md-4">
    <div class="scheduler-widget">
        <h6>Scheduler Status</h6>
        <div id="scheduler-metrics"></div>
        <button onclick="openFullSchedulerView()">Manage Scheduler</button>
    </div>
</div>
```

### **Files to use:**
- `/integration_examples/component_integration.html` - Complete example
- Copy the JavaScript functions to your dashboard

### **What you get:**
- ✅ Small widget + expandable full view
- ✅ Matches your dashboard design
- ✅ Progressive disclosure
- ✅ Toast notifications

---

## 📱 **Option 4: Standalone Dashboard**

**Best for:** Dedicated scheduler management, testing

### **Access:**
- **URL:** `http://localhost:4200/real-dashboard.html`
- **Full Features:** Complete scheduler management interface

### **What you get:**
- ✅ Complete standalone interface
- ✅ All scheduler features
- ✅ Professional UI
- ✅ Ready to use immediately

---

## 🎯 **Quick Decision Matrix**

| Need | Best Option | Why |
|------|-------------|-----|
| **Quick test** | Standalone Dashboard | Zero setup, immediate access |
| **Existing JavaScript dashboard** | API Integration | Full control, seamless integration |
| **WordPress/CMS** | iframe Integration | Easy embed, no coding |
| **React/Vue/Angular** | Component Integration | Natural component approach |
| **Full control** | API Integration | Complete customization |

---

## 🚀 **Getting Started (5 minutes)**

### **Step 1: Start Services**
```bash
# Terminal 1: Start web service (API)
cd web_service
source ../.venv/bin/activate
python -m app.main

# Terminal 2: Start dashboard server
cd frontend
python3 -m http.server 4200
```

### **Step 2: Test Standalone Dashboard**
- Open: `http://localhost:4200/real-dashboard.html`
- Look for dark "Scheduler Status" section
- Click "🎯 Manage Scheduler" button
- Test all features

### **Step 3: Choose Integration Method**
- **API Integration:** Copy `/integration_examples/api_integration.js`
- **iframe Integration:** Copy code from `/integration_examples/iframe_integration.html`
- **Component Integration:** Copy code from `/integration_examples/component_integration.html`

### **Step 4: Customize**
- Update API endpoint URLs
- Modify styling to match your dashboard
- Add authentication headers if needed

---

## 🔌 **API Endpoints Available**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/scheduler/status` | Get scheduler status |
| `GET` | `/api/v1/scheduler/executions` | List recent executions |
| `POST` | `/api/v1/scheduler/trigger` | Trigger manual sync |
| `POST` | `/api/v1/scheduler/reload` | Reload configurations |
| `GET` | `/api/v1/scheduler/schedule/{name}` | Get schedule details |

---

## 🎨 **Customization Examples**

### **Change Colors:**
```css
.scheduler-widget {
    background: linear-gradient(135deg, #your-color-1, #your-color-2);
}
```

### **Update API URL:**
```javascript
const schedulerAPI = new SchedulerAPIClient('https://your-domain.com/api/v1');
```

### **Add Authentication:**
```javascript
schedulerAPI.setAuthToken('your-jwt-token-here');
```

---

## 🛠️ **Troubleshooting**

### **"Manage Scheduler" button not visible:**
1. Check if API is running: `curl http://localhost:8080/health`
2. Check browser console for JavaScript errors
3. Verify the scheduler status section exists in HTML
4. Try the standalone dashboard first: `http://localhost:4200/real-dashboard.html`

### **API calls failing:**
1. Ensure web service is running on port 8080
2. Check CORS settings in web service
3. Verify authentication tokens if required
4. Check network requests in browser DevTools

### **iframe not loading:**
1. Verify dashboard server is running on port 4200
2. Check iframe src URL is correct
3. Ensure no HTTPS/HTTP mixed content issues

---

## 📞 **Support & Next Steps**

### **Files Created:**
- ✅ `/integration_examples/api_integration.js` - API client
- ✅ `/integration_examples/iframe_integration.html` - iframe example
- ✅ `/integration_examples/component_integration.html` - component example
- ✅ `/frontend/real-dashboard.html` - standalone dashboard

### **CLI Commands Available:**
```bash
document-loader scheduler status
document-loader scheduler start
document-loader scheduler trigger <config>
```

### **Ready for Production:**
- ✅ Authentication & permissions implemented
- ✅ Audit logging for all operations
- ✅ Error handling and validation
- ✅ Real-time status updates
- ✅ Responsive design

**🎯 The scheduler is fully integrated and ready to use with your dashboard!**