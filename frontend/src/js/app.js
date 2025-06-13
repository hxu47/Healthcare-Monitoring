// Main Application for Patient Vital Signs Monitoring System

class HealthcareDashboard {
    constructor() {
        this.api = window.healthcareAPI;
        this.currentView = 'dashboard';
        this.selectedPatientId = null;
        this.vitalSignsChart = null;
        this.refreshInterval = null;
        this.patients = [];
        this.alerts = [];
        
        // Initialize the application
        this.init();
    }

    async init() {
        try {
            this.showLoading();
            await this.loadInitialData();
            this.setupEventListeners();
            this.startAutoRefresh();
            this.showSystemStatus('System initialized successfully', 'success');
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showSystemStatus('Failed to initialize system: ' + error.message, 'error');
        }
    }

    async loadInitialData() {
        try {
            // Load patients and dashboard stats
            const [patientsResponse, statsResponse] = await Promise.all([
                this.api.getAllPatients(),
                this.api.getDashboardStats()
            ]);

            this.patients = patientsResponse.patients || [];
            this.updateDashboardStats(statsResponse);
            this.updatePatientsTable();
            this.updatePatientSelect();
            
            // Load initial alerts
            const alertsResponse = await this.api.getRecentAlerts(1);
            this.alerts = alertsResponse.alerts || [];
            this.updateAlertsDisplay();

        } catch (error) {
            console.error('Error loading initial data:', error);
            // Use mock data for demo if API fails
            this.loadMockData();
        }
    }

    loadMockData() {
        console.log('Loading mock data for demonstration...');
        
        // Mock patients data
        this.patients = [
            {
                PatientId: 'PATIENT-001',
                Name: 'John Smith',
                Age: 45,
                Gender: 'Male',
                RoomNumber: 'ICU-101',
                Status: 'Active',
                Condition: 'Stable'
            },
            {
                PatientId: 'PATIENT-002',
                Name: 'Sarah Johnson',
                Age: 67,
                Gender: 'Female',
                RoomNumber: 'ICU-102',
                Status: 'Active',
                Condition: 'Critical'
            },
            {
                PatientId: 'PATIENT-003',
                Name: 'Michael Brown',
                Age: 32,
                Gender: 'Male',
                RoomNumber: 'WARD-201',
                Status: 'Active',
                Condition: 'Stable'
            },
            {
                PatientId: 'PATIENT-004',
                Name: 'Emily Davis',
                Age: 28,
                Gender: 'Female',
                RoomNumber: 'WARD-202',
                Status: 'Active',
                Condition: 'Warning'
            },
            {
                PatientId: 'PATIENT-005',
                Name: 'Robert Wilson',
                Age: 78,
                Gender: 'Male',
                RoomNumber: 'ICU-103',
                Status: 'Active',
                Condition: 'Critical'
            }
        ];

        // Mock dashboard stats
        this.updateDashboardStats({
            patients: {
                total: 5,
                normal: 2,
                warning: 1,
                critical: 2
            }
        });

        this.updatePatientsTable();
        this.updatePatientSelect();
        
        // Mock alerts
        this.alerts = this.api.generateMockAlerts();
        this.updateAlertsDisplay();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = e.target.getAttribute('onclick');
                if (view) {
                    eval(view); // Execute the onclick function
                }
            });
        });

        // Auto-refresh toggle
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.refreshData();
            }
        });
    }

    startAutoRefresh() {
        // Refresh data every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async refreshData() {
        try {
            if (this.currentView === 'dashboard') {
                await this.loadInitialData();
                
                // Refresh chart if patient is selected
                if (this.selectedPatientId) {
                    await this.loadPatientVitalSigns(this.selectedPatientId);
                }
            }
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    }

    // View Management
    showDashboard() {
        this.currentView = 'dashboard';
        this.hideAllViews();
        document.getElementById('dashboardView').style.display = 'block';
        this.setActiveNavItem('Dashboard');
        this.refreshData();
    }

    showPatients() {
        this.currentView = 'patients';
        this.hideAllViews();
        document.getElementById('patientsView').style.display = 'block';
        this.setActiveNavItem('Patients');
        this.updateAllPatientsTable();
    }

    showAlerts() {
        this.currentView = 'alerts';
        this.hideAllViews();
        document.getElementById('alertsView').style.display = 'block';
        this.setActiveNavItem('Alerts');
        this.loadAllAlerts();
    }

    hideAllViews() {
        document.querySelectorAll('.view').forEach(view => {
            view.style.display = 'none';
        });
    }

    setActiveNavItem(activeText) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.textContent.trim().includes(activeText)) {
                link.classList.add('active');
            }
        });
    }

    // Dashboard Functions
    updateDashboardStats(stats) {
        const patients = stats.patients || {};
        
        document.getElementById('totalPatients').textContent = patients.total || 0;
        document.getElementById('normalPatients').textContent = patients.normal || 0;
        document.getElementById('warningPatients').textContent = patients.warning || 0;
        document.getElementById('criticalPatients').textContent = patients.critical || 0;
    }

    updatePatientsTable() {
        const tbody = document.getElementById('patientsTableBody');
        
        if (!this.patients || this.patients.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        <i class="fas fa-users fa-2x mb-2"></i>
                        <p class="mb-0">No patients found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.patients.map(patient => `
            <tr>
                <td><strong>${patient.PatientId}</strong></td>
                <td>${patient.Name}</td>
                <td><span class="badge bg-info">${patient.RoomNumber}</span></td>
                <td>
                    <span class="status-badge status-${patient.Condition?.toLowerCase() || 'normal'}">
                        ${patient.Condition || 'Normal'}
                    </span>
                </td>
                <td><small class="text-muted">Just now</small></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" 
                            onclick="healthcareDashboard.selectPatientFromButton('${patient.PatientId}')">
                        <i class="fas fa-chart-line"></i> Monitor
                    </button>
                    <button class="btn btn-sm btn-outline-info" 
                            onclick="healthcareDashboard.showPatientDetails('${patient.PatientId}')">
                        <i class="fas fa-info-circle"></i> Details
                    </button>
                </td>
            </tr>
        `).join('');
    }

    updateAllPatientsTable() {
        const tbody = document.getElementById('allPatientsTableBody');
        
        if (!this.patients || this.patients.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        <i class="fas fa-users fa-2x mb-2"></i>
                        <p class="mb-0">No patients found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.patients.map(patient => `
            <tr>
                <td><strong>${patient.PatientId}</strong></td>
                <td>${patient.Name}</td>
                <td>${patient.Age}</td>
                <td>${patient.Gender}</td>
                <td><span class="badge bg-info">${patient.RoomNumber}</span></td>
                <td>
                    <span class="status-badge status-${patient.Status?.toLowerCase() || 'active'}">
                        ${patient.Status || 'Active'}
                    </span>
                </td>
                <td>
                    <span class="status-badge status-${patient.Condition?.toLowerCase() || 'normal'}">
                        ${patient.Condition || 'Normal'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" 
                            onclick="healthcareDashboard.showPatientDetails('${patient.PatientId}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="healthcareDashboard.deletePatient('${patient.PatientId}')">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </td>
            </tr>
        `).join('');
    }

    updatePatientSelect() {
        const select = document.getElementById('patientSelect');
        
        select.innerHTML = '<option value="">Select Patient...</option>';
        
        this.patients.forEach(patient => {
            const option = document.createElement('option');
            option.value = patient.PatientId;
            option.textContent = `${patient.Name} (${patient.RoomNumber})`;
            select.appendChild(option);
        });
    }

    // Fixed function: Handle patient selection from Monitor button
    async selectPatientFromButton(patientId) {
        // Switch to dashboard view if not already there
        if (this.currentView !== 'dashboard') {
            this.showDashboard();
        }
        
        // Update dropdown selection
        const select = document.getElementById('patientSelect');
        select.value = patientId;
        
        // Set selected patient and load data
        this.selectedPatientId = patientId;
        await this.loadPatientVitalSigns(patientId);
        
        // Show success message
        const patient = this.patients.find(p => p.PatientId === patientId);
        if (patient) {
            this.showSystemStatus(`Now monitoring ${patient.Name} (${patientId})`, 'success');
        }
    }

    // Fixed function: Handle dropdown selection
    async selectPatient() {
        const select = document.getElementById('patientSelect');
        const patientId = select.value;
        
        if (!patientId) {
            this.selectedPatientId = null;
            this.clearVitalSignsChart();
            return;
        }

        this.selectedPatientId = patientId;
        await this.loadPatientVitalSigns(patientId);
    }

    async loadPatientVitalSigns(patientId) {
        try {
            this.showSystemStatus(`Loading vital signs for patient ${patientId}...`, 'info');
            
            // Try to get real data first, then fall back to mock data
            let vitalSignsData;
            
            try {
                const response = await this.api.getVitalSigns(patientId, '1h');
                vitalSignsData = response.vitalSigns || [];
                
                // If no real data, generate mock data
                if (vitalSignsData.length === 0) {
                    console.log('No real data found, generating mock data for', patientId);
                    vitalSignsData = this.api.generateMockVitalSigns(patientId);
                }
            } catch (error) {
                console.log('API error, using mock data for vital signs:', error);
                vitalSignsData = this.api.generateMockVitalSigns(patientId);
            }

            this.updateVitalSignsChart(vitalSignsData);
            
            const patient = this.patients.find(p => p.PatientId === patientId);
            if (patient) {
                this.showSystemStatus(`Displaying vital signs for ${patient.Name}`, 'success');
            }
            
        } catch (error) {
            console.error('Error loading vital signs:', error);
            this.showSystemStatus('Error loading vital signs: ' + error.message, 'error');
            
            // Fallback to mock data
            const mockData = this.api.generateMockVitalSigns(patientId);
            this.updateVitalSignsChart(mockData);
        }
    }

    updateVitalSignsChart(vitalSignsData) {
        const ctx = document.getElementById('vitalSignsChart').getContext('2d');
        
        // Ensure we have data
        if (!vitalSignsData || vitalSignsData.length === 0) {
            this.clearVitalSignsChart();
            return;
        }
        
        // Prepare data for Chart.js
        const labels = vitalSignsData.map(vs => {
            const date = new Date(vs.Timestamp);
            return date.toLocaleTimeString();
        });

        const heartRateData = vitalSignsData.map(vs => vs.HeartRate);
        const systolicBPData = vitalSignsData.map(vs => vs.SystolicBP);
        const temperatureData = vitalSignsData.map(vs => vs.Temperature);
        const oxygenSatData = vitalSignsData.map(vs => vs.OxygenSaturation);

        // Destroy existing chart if it exists
        if (this.vitalSignsChart) {
            this.vitalSignsChart.destroy();
        }

        // Create new chart
        this.vitalSignsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Heart Rate (bpm)',
                        data: heartRateData,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Systolic BP (mmHg)',
                        data: systolicBPData,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Temperature (°F)',
                        data: temperatureData,
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Oxygen Sat (%)',
                        data: oxygenSatData,
                        borderColor: '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y2'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Heart Rate / Blood Pressure'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Temperature (°F)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                    y2: {
                        type: 'linear',
                        display: false,
                        min: 90,
                        max: 100
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Real-time Vital Signs - ${this.getPatientName(this.selectedPatientId)}`
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
        
        console.log('Chart updated with', vitalSignsData.length, 'data points');
    }

    clearVitalSignsChart() {
        if (this.vitalSignsChart) {
            this.vitalSignsChart.destroy();
            this.vitalSignsChart = null;
        }
        
        const ctx = document.getElementById('vitalSignsChart').getContext('2d');
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#6c757d';
        ctx.textAlign = 'center';
        ctx.fillText('Select a patient to view vital signs', ctx.canvas.width / 2, ctx.canvas.height / 2);
    }

    // Alert Management
    updateAlertsDisplay() {
        const alertsList = document.getElementById('alertsList');
        
        if (!this.alerts || this.alerts.length === 0) {
            alertsList.innerHTML = `
                <div class="list-group list-group-flush">
                    <div class="list-group-item text-center text-muted">
                        <i class="fas fa-shield-alt fa-2x mb-2"></i>
                        <p class="mb

    async loadAllAlerts() {
        try {
            const response = await this.api.getAllAlerts(100);
            const allAlerts = response.alerts || [];
            
            const alertsContainer = document.getElementById('allAlertsList');
            
            if (allAlerts.length === 0) {
                alertsContainer.innerHTML = `
                    <div class="text-center text-muted">
                        <i class="fas fa-shield-alt fa-3x mb-3"></i>
                        <h4>No Alerts Found</h4>
                        <p>The system is running smoothly with no recent alerts.</p>
                    </div>
                `;
                return;
            }

            alertsContainer.innerHTML = allAlerts.map(alert => `
                <div class="card mb-3 alert-item alert-${alert.AlertType?.toLowerCase() || 'info'}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h5 class="card-title">
                                    <i class="fas fa-${this.getAlertIcon(alert.AlertType)} me-2"></i>
                                    ${alert.AlertType || 'Alert'} - Patient ${alert.PatientId}
                                </h5>
                                <p class="card-text">${alert.Message || 'No message'}</p>
                                <small class="text-muted">
                                    <i class="fas fa-clock me-1"></i>
                                    ${this.formatDateTime(alert.Timestamp)}
                                </small>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-${this.getStatusBadgeColor(alert.Status)}">${alert.Status || 'SENT'}</span>
                                ${alert.Status !== 'ACKNOWLEDGED' ? `
                                    <button class="btn btn-sm btn-outline-primary mt-2" 
                                            onclick="healthcareDashboard.acknowledgeAlert('${alert.AlertId}')">
                                        <i class="fas fa-check"></i> Acknowledge
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Error loading all alerts:', error);
            // Use mock alerts
            const mockAlerts = this.api.generateMockAlerts();
            this.displayMockAlerts(mockAlerts);
        }
    }

    async acknowledgeAlert(alertId) {
        try {
            await this.api.acknowledgeAlert(alertId);
            this.showSystemStatus('Alert acknowledged successfully', 'success');
            this.loadAllAlerts(); // Refresh the alerts list
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            this.showSystemStatus('Error acknowledging alert: ' + error.message, 'error');
        }
    }

    // Patient Management
    showAddPatientModal() {
        const modal = new bootstrap.Modal(document.getElementById('addPatientModal'));
        modal.show();
    }

    async addPatient() {
        try {
            const patientData = {
                PatientId: document.getElementById('patientId').value,
                Name: document.getElementById('patientName').value,
                Age: parseInt(document.getElementById('patientAge').value),
                Gender: document.getElementById('patientGender').value,
                RoomNumber: document.getElementById('roomNumber').value,
                Status: 'Active',
                Condition: 'Stable'
            };

            await this.api.createPatient(patientData);
            
            // Close modal and refresh data
            const modal = bootstrap.Modal.getInstance(document.getElementById('addPatientModal'));
            modal.hide();
            
            this.showSystemStatus('Patient added successfully', 'success');
            this.refreshData();
            
            // Clear form
            document.getElementById('addPatientForm').reset();

        } catch (error) {
            console.error('Error adding patient:', error);
            this.showSystemStatus('Error adding patient: ' + error.message, 'error');
        }
    }

    async showPatientDetails(patientId) {
        try {
            const response = await this.api.getPatient(patientId);
            const patient = response;
            
            // Show patient details modal (you can implement this)
            console.log('Show patient details for:', patient);
            
        } catch (error) {
            console.error('Error loading patient details:', error);
            this.showSystemStatus('Error loading patient details: ' + error.message, 'error');
        }
    }

    async deletePatient(patientId) {
        if (!confirm('Are you sure you want to deactivate this patient?')) {
            return;
        }

        try {
            await this.api.deletePatient(patientId);
            this.showSystemStatus('Patient deactivated successfully', 'success');
            this.refreshData();

        } catch (error) {
            console.error('Error deleting patient:', error);
            this.showSystemStatus('Error deactivating patient: ' + error.message, 'error');
        }
    }

    // Utility Functions
    getPatientName(patientId) {
        const patient = this.patients.find(p => p.PatientId === patientId);
        return patient ? patient.Name : 'Unknown Patient';
    }

    getAlertIcon(alertType) {
        switch (alertType?.toLowerCase()) {
            case 'critical': return 'exclamation-triangle';
            case 'warning': return 'exclamation-circle';
            case 'info': return 'info-circle';
            default: return 'bell';
        }
    }

    getStatusBadgeColor(status) {
        switch (status?.toLowerCase()) {
            case 'acknowledged': return 'success';
            case 'sent': return 'primary';
            default: return 'secondary';
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return 'Unknown';
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }

    formatDateTime(timestamp) {
        if (!timestamp) return 'Unknown';
        const date = new Date(timestamp);
        return date.toLocaleString();
    }

    truncateMessage(message, maxLength) {
        if (!message || message.length <= maxLength) return message;
        return message.substring(0, maxLength) + '...';
    }

    showSystemStatus(message, type = 'info') {
        const statusElement = document.getElementById('statusMessage');
        const alertElement = document.getElementById('systemStatus');
        
        statusElement.textContent = message;
        
        // Remove existing classes
        alertElement.className = 'alert alert-dismissible fade show';
        
        // Add appropriate class based on type
        switch (type) {
            case 'success':
                alertElement.classList.add('alert-success');
                break;
            case 'error':
                alertElement.classList.add('alert-danger');
                break;
            case 'warning':
                alertElement.classList.add('alert-warning');
                break;
            default:
                alertElement.classList.add('alert-info');
        }
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertElement.style.display = 'none';
        }, 5000);
    }

    showLoading() {
        this.showSystemStatus('Loading healthcare monitoring system...', 'info');
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.healthcareDashboard = new HealthcareDashboard();
});

// Global functions for onclick handlers
function showDashboard() {
    window.healthcareDashboard.showDashboard();
}

function showPatients() {
    window.healthcareDashboard.showPatients();
}

function showAlerts() {
    window.healthcareDashboard.showAlerts();
}

function selectPatient() {
    window.healthcareDashboard.selectPatient();
}

function showAddPatientModal() {
    window.healthcareDashboard.showAddPatientModal();
}

function addPatient() {
    window.healthcareDashboard.addPatient();
}