/**
 * Scheduler API Integration Examples
 * 
 * Use these functions to integrate scheduler features into your existing dashboard
 */

class SchedulerAPIClient {
    constructor(baseUrl = 'http://localhost:8080/api/v1') {
        this.baseUrl = baseUrl;
        this.token = null; // Set your JWT token here
    }

    // Set authentication token
    setAuthToken(token) {
        this.token = token;
    }

    // Helper method for API calls
    async apiCall(endpoint, method = 'GET', body = null) {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const config = {
            method,
            headers,
        };

        if (body) {
            config.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API call failed: ${endpoint}`, error);
            throw error;
        }
    }

    // 📊 Get Scheduler Status
    async getSchedulerStatus() {
        return await this.apiCall('/scheduler/status');
    }

    // 📋 Get Schedule Executions
    async getExecutions(configName = null, statusFilter = null, limit = 20) {
        let params = new URLSearchParams();
        if (configName) params.append('config_name', configName);
        if (statusFilter) params.append('status_filter', statusFilter);
        if (limit) params.append('limit', limit.toString());
        
        const query = params.toString() ? `?${params.toString()}` : '';
        return await this.apiCall(`/scheduler/executions${query}`);
    }

    // ⚡ Trigger Manual Sync
    async triggerSync(configName, force = false) {
        return await this.apiCall('/scheduler/trigger', 'POST', {
            config_name: configName,
            force: force
        });
    }

    // 🔄 Reload Configurations
    async reloadConfigurations() {
        return await this.apiCall('/scheduler/reload', 'POST');
    }

    // 📝 Get Schedule Details
    async getScheduleInfo(configName) {
        return await this.apiCall(`/scheduler/schedule/${configName}`);
    }
}

// 🎯 Usage Examples

// Initialize the client
const schedulerAPI = new SchedulerAPIClient();

// Example 1: Add scheduler status to your dashboard
async function addSchedulerStatusToExistingDashboard() {
    try {
        const response = await schedulerAPI.getSchedulerStatus();
        const status = response.data;
        
        // Update your existing dashboard elements
        document.getElementById('scheduler-running').textContent = status.running ? 'Running' : 'Stopped';
        document.getElementById('active-schedules').textContent = status.active_schedules;
        document.getElementById('running-executions').textContent = status.running_executions;
        
        console.log('✅ Scheduler status updated in dashboard');
        
    } catch (error) {
        console.error('❌ Failed to load scheduler status:', error);
        // Handle error - show fallback UI
        document.getElementById('scheduler-status').innerHTML = '<span class="text-danger">Scheduler Unavailable</span>';
    }
}

// Example 2: Add "Manage Scheduler" button to your dashboard
function addSchedulerButton() {
    const buttonHTML = `
        <button class="btn btn-outline-primary" onclick="openSchedulerManagement()">
            <i class="bi bi-gear me-2"></i>
            Manage Scheduler
        </button>
    `;
    
    // Insert into your existing quick actions or toolbar
    document.getElementById('dashboard-actions').insertAdjacentHTML('beforeend', buttonHTML);
}

// Example 3: Open scheduler management modal/panel
async function openSchedulerManagement() {
    try {
        // Load scheduler data
        const [statusResponse, executionsResponse] = await Promise.all([
            schedulerAPI.getSchedulerStatus(),
            schedulerAPI.getExecutions()
        ]);
        
        // Create scheduler management UI
        const modalHTML = createSchedulerModal(statusResponse.data, executionsResponse.data);
        
        // Show modal (using your existing modal system)
        showModal('Scheduler Management', modalHTML);
        
    } catch (error) {
        console.error('❌ Failed to open scheduler management:', error);
        alert('Failed to load scheduler data. Please check if the web service is running.');
    }
}

// Example 4: Create scheduler management modal content
function createSchedulerModal(statusData, executionsData) {
    return `
        <div class="scheduler-management">
            <!-- Status Cards -->
            <div class="row g-3 mb-4">
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <i class="bi bi-${statusData.running ? 'play-circle text-success' : 'pause-circle text-secondary'} fs-2"></i>
                            <h6>Scheduler</h6>
                            <span class="badge bg-${statusData.running ? 'success' : 'secondary'}">${statusData.running ? 'Running' : 'Stopped'}</span>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <i class="bi bi-calendar-check text-info fs-2"></i>
                            <h6>Active Schedules</h6>
                            <span class="display-6 fw-bold">${statusData.active_schedules}</span>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <i class="bi bi-arrow-repeat text-warning fs-2"></i>
                            <h6>Running</h6>
                            <span class="display-6 fw-bold">${statusData.running_executions}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Control Buttons -->
            <div class="row g-2 mb-4">
                <div class="col-3">
                    <button class="btn btn-outline-secondary w-100" onclick="refreshSchedulerData()">
                        <i class="bi bi-arrow-clockwise"></i> Refresh
                    </button>
                </div>
                <div class="col-3">
                    <button class="btn btn-outline-info w-100" onclick="reloadSchedulerConfigs()">
                        <i class="bi bi-cloud-download"></i> Reload
                    </button>
                </div>
                <div class="col-3">
                    <button class="btn btn-outline-primary w-100" onclick="toggleAutoRefresh()">
                        <i class="bi bi-play"></i> Auto-Refresh
                    </button>
                </div>
                <div class="col-3">
                    <button class="btn btn-outline-warning w-100" onclick="showTriggerDialog()">
                        <i class="bi bi-lightning"></i> Trigger
                    </button>
                </div>
            </div>
            
            <!-- Recent Executions Table -->
            <h6>Recent Executions</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th>Status</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${executionsData.executions.map(exec => `
                            <tr>
                                <td>${exec.config_name}</td>
                                <td><span class="badge bg-${getStatusColor(exec.status)}">${exec.status}</span></td>
                                <td>${new Date(exec.scheduled_time).toLocaleString()}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// Example 5: Trigger sync with confirmation
async function triggerSyncWithConfirmation(configName) {
    if (confirm(`Are you sure you want to trigger sync for "${configName}"?`)) {
        try {
            const response = await schedulerAPI.triggerSync(configName);
            alert(`✅ ${response.message}`);
            
            // Refresh the scheduler data
            refreshSchedulerData();
            
        } catch (error) {
            console.error('❌ Failed to trigger sync:', error);
            alert('❌ Failed to trigger sync. Please try again.');
        }
    }
}

// Helper functions
function getStatusColor(status) {
    const colors = {
        'completed': 'success',
        'running': 'primary', 
        'pending': 'warning',
        'failed': 'danger'
    };
    return colors[status] || 'secondary';
}

function refreshSchedulerData() {
    console.log('🔄 Refreshing scheduler data...');
    // Reload the modal or update the data
    openSchedulerManagement();
}

async function reloadSchedulerConfigs() {
    try {
        const response = await schedulerAPI.reloadConfigurations();
        alert(`✅ ${response.message}`);
        refreshSchedulerData();
    } catch (error) {
        console.error('❌ Failed to reload configs:', error);
        alert('❌ Failed to reload configurations.');
    }
}

// Example 6: Auto-refresh functionality
let autoRefreshInterval = null;

function toggleAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('⏹️ Auto-refresh stopped');
    } else {
        autoRefreshInterval = setInterval(refreshSchedulerData, 30000); // 30 seconds
        console.log('▶️ Auto-refresh started (30s interval)');
    }
}

// 🚀 Quick Integration: Add to your existing dashboard
function quickIntegrateScheduler() {
    // 1. Add scheduler status section to your dashboard
    const dashboardContainer = document.getElementById('dashboard-main'); // Your dashboard container
    
    if (dashboardContainer) {
        const schedulerSection = `
            <div class="card mb-4" id="scheduler-section">
                <div class="card-header bg-dark text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-clock me-2"></i>
                        Scheduler Status
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-3 text-center">
                            <span id="scheduler-running">Loading...</span>
                        </div>
                        <div class="col-md-3 text-center">
                            <span id="active-schedules">0</span> Active Schedules
                        </div>
                        <div class="col-md-3 text-center">
                            <span id="running-executions">0</span> Running
                        </div>
                        <div class="col-md-3">
                            <button class="btn btn-outline-primary w-100" onclick="openSchedulerManagement()">
                                <i class="bi bi-gear"></i> Manage Scheduler
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        dashboardContainer.insertAdjacentHTML('afterbegin', schedulerSection);
        
        // 2. Load initial data
        addSchedulerStatusToExistingDashboard();
        
        // 3. Set up periodic refresh
        setInterval(addSchedulerStatusToExistingDashboard, 60000); // Every minute
        
        console.log('✅ Scheduler integrated into dashboard');
    }
}

// Export for use in your dashboard
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SchedulerAPIClient,
        quickIntegrateScheduler,
        addSchedulerStatusToExistingDashboard,
        openSchedulerManagement
    };
}