// Main Application for Patient Vital Signs Monitoring System
// Real data only - no mock data

(function() {
    'use strict';
    
    // Global variables
    var healthcareDashboard;
    
    // Healthcare Dashboard Constructor Function
    function HealthcareDashboard() {
        this.api = window.healthcareAPI;
        this.currentView = 'dashboard';
        this.selectedPatientId = null;
        this.vitalSignsChart = null;
        this.refreshInterval = null;
        this.patients = [];
        this.alerts = [];
        
        // Bind methods to preserve 'this' context
        this.init = this.init.bind(this);
        this.loadInitialData = this.loadInitialData.bind(this);
        this.refreshData = this.refreshData.bind(this);
        
        // Initialize
        this.init();
    }
    
    // Initialize the dashboard
    HealthcareDashboard.prototype.init = function() {
        var self = this;
        console.log('Initializing Healthcare Dashboard with real data...');
        
        try {
            self.showLoading();
            
            // Check if API is available
            if (!window.healthcareAPI) {
                console.error('Healthcare API not available');
                self.showSystemStatus('Healthcare API not available. Please check system configuration.', 'error');
                return;
            }
            
            // Load real data
            self.loadInitialData().then(function() {
                self.setupEventListeners();
                self.startAutoRefresh();
                self.showSystemStatus('Healthcare system connected successfully', 'success');
            }).catch(function(error) {
                console.error('Failed to load initial data:', error);
                self.showSystemStatus('Failed to connect to healthcare system: ' + error.message, 'error');
                self.setupEventListeners();
            });
            
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            self.showSystemStatus('System initialization failed: ' + error.message, 'error');
        }
    };
    
    // Load initial data from real APIs
    HealthcareDashboard.prototype.loadInitialData = function() {
        var self = this;
        
        return new Promise(function(resolve, reject) {
            console.log('Loading data from healthcare APIs...');
            
            // Load patients and dashboard stats
            Promise.all([
                self.api.getAllPatients(),
                self.api.getDashboardStats()
            ]).then(function(responses) {
                var patientsResponse = responses[0];
                var statsResponse = responses[1];
                
                console.log('Patients response:', patientsResponse);
                console.log('Stats response:', statsResponse);
                
                self.patients = patientsResponse.patients || [];
                
                if (self.patients.length === 0) {
                    self.showSystemStatus('No patients found in system. IoT simulator may be starting up...', 'warning');
                }
                
                self.updateDashboardStats(statsResponse);
                self.updatePatientsTable();
                self.updatePatientSelect();
                
                // Load recent alerts
                return self.api.getRecentAlerts(1);
                
            }).then(function(alertsResponse) {
                console.log('Alerts response:', alertsResponse);
                
                self.alerts = alertsResponse.alerts || [];
                self.updateAlertsDisplay();
                
                if (self.alerts.length === 0) {
                    self.showSystemStatus('No recent alerts. System monitoring normally.', 'info');
                }
                
                resolve();
                
            }).catch(function(error) {
                console.error('API error:', error);
                self.showSystemStatus('API connection error: ' + error.message, 'error');
                reject(error);
            });
        });
    };
    
    // Update dashboard stats
    HealthcareDashboard.prototype.updateDashboardStats = function(stats) {
        var patients = stats.patients || {};
        
        var totalEl = document.getElementById('totalPatients');
        var normalEl = document.getElementById('normalPatients');
        var warningEl = document.getElementById('warningPatients');
        var criticalEl = document.getElementById('criticalPatients');
        
        if (totalEl) totalEl.textContent = patients.total || 0;
        if (normalEl) normalEl.textContent = patients.normal || 0;
        if (warningEl) warningEl.textContent = patients.warning || 0;
        if (criticalEl) criticalEl.textContent = patients.critical || 0;
    };
    
    // Update patients table
    HealthcareDashboard.prototype.updatePatientsTable = function() {
        var tbody = document.getElementById('patientsTableBody');
        if (!tbody) return;
        
        if (!this.patients || this.patients.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">' +
                '<i class="fas fa-clock fa-2x mb-2"></i>' +
                '<p class="mb-0">Waiting for patient data...</p>' +
                '<small class="text-muted">IoT simulator generates data every 5 minutes</small>' +
                '</td></tr>';
            return;
        }

        var html = '';
        for (var i = 0; i < this.patients.length; i++) {
            var patient = this.patients[i];
            html += '<tr>' +
                '<td><strong>' + patient.PatientId + '</strong></td>' +
                '<td>' + patient.Name + '</td>' +
                '<td><span class="badge bg-info">' + patient.RoomNumber + '</span></td>' +
                '<td><span class="status-badge status-' + (patient.Condition || 'normal').toLowerCase() + '">' + (patient.Condition || 'Normal') + '</span></td>' +
                '<td><small class="text-muted">Live</small></td>' +
                '<td>' +
                '<button class="btn btn-sm btn-outline-primary me-1" onclick="selectPatientFromButton(\'' + patient.PatientId + '\')">' +
                '<i class="fas fa-chart-line"></i> Monitor</button>' +
                '<button class="btn btn-sm btn-outline-info" onclick="showPatientDetails(\'' + patient.PatientId + '\')">' +
                '<i class="fas fa-info-circle"></i> Details</button>' +
                '</td>' +
                '</tr>';
        }
        tbody.innerHTML = html;
    };
    
    // Update patient select dropdown
    HealthcareDashboard.prototype.updatePatientSelect = function() {
        var select = document.getElementById('patientSelect');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select Patient...</option>';
        
        for (var i = 0; i < this.patients.length; i++) {
            var patient = this.patients[i];
            var option = document.createElement('option');
            option.value = patient.PatientId;
            option.textContent = patient.Name + ' (' + patient.RoomNumber + ')';
            select.appendChild(option);
        }
    };
    
    // Update alerts display
    HealthcareDashboard.prototype.updateAlertsDisplay = function() {
        var alertsList = document.getElementById('alertsList');
        if (!alertsList) return;
        
        if (!this.alerts || this.alerts.length === 0) {
            alertsList.innerHTML = '<div class="list-group list-group-flush">' +
                '<div class="list-group-item text-center text-muted">' +
                '<i class="fas fa-shield-alt fa-2x mb-2"></i>' +
                '<p class="mb-0">No recent alerts</p>' +
                '<small class="text-muted">System monitoring normally</small>' +
                '</div></div>';
            return;
        }

        var alertsHtml = '';
        var alertsToShow = this.alerts.slice(0, 10);
        
        for (var i = 0; i < alertsToShow.length; i++) {
            var alert = alertsToShow[i];
            alertsHtml += '<div class="list-group-item alert-item alert-' + (alert.AlertType || 'info').toLowerCase() + '">' +
                '<div class="d-flex justify-content-between align-items-start">' +
                '<div class="flex-grow-1">' +
                '<h6 class="mb-1"><i class="fas fa-' + this.getAlertIcon(alert.AlertType) + ' me-1"></i>' + (alert.AlertType || 'Alert') + '</h6>' +
                '<p class="mb-1">' + this.truncateMessage(alert.Message || 'No message', 60) + '</p>' +
                '<small class="text-muted">' + alert.PatientId + ' • ' + this.formatTime(alert.Timestamp) + '</small>' +
                '</div>' +
                '<div class="flex-shrink-0"><small class="text-muted">' + (alert.Status || 'SENT') + '</small></div>' +
                '</div></div>';
        }
        
        alertsList.innerHTML = '<div class="list-group list-group-flush">' + alertsHtml + '</div>';
    };
    
    // Select patient from button click
    HealthcareDashboard.prototype.selectPatientFromButton = function(patientId) {
        if (this.currentView !== 'dashboard') {
            this.showDashboard();
        }
        
        var select = document.getElementById('patientSelect');
        if (select) select.value = patientId;
        
        this.selectedPatientId = patientId;
        this.loadPatientVitalSigns(patientId);
        
        var patient = this.getPatientById(patientId);
        if (patient) {
            this.showSystemStatus('Now monitoring ' + patient.Name + ' (' + patientId + ')', 'success');
        }
    };
    
    // Select patient from dropdown
    HealthcareDashboard.prototype.selectPatient = function() {
        var select = document.getElementById('patientSelect');
        if (!select) return;
        
        var patientId = select.value;
        
        if (!patientId) {
            this.selectedPatientId = null;
            this.clearVitalSignsChart();
            return;
        }

        this.selectedPatientId = patientId;
        this.loadPatientVitalSigns(patientId);
    };
    
    // Load patient vital signs from real API
    HealthcareDashboard.prototype.loadPatientVitalSigns = function(patientId) {
        var self = this;
        
        console.log('Loading vital signs for patient:', patientId);
        self.showSystemStatus('Loading vital signs for patient ' + patientId + '...', 'info');
        
        // Try to get real data from API
        self.api.getVitalSigns(patientId, '1h').then(function(response) {
            console.log('Vital signs response:', response);
            
            var vitalSignsData = response.vitalSigns || [];
            
            if (vitalSignsData.length === 0) {
                self.showSystemStatus('No vital signs data found for this patient yet. Data generates every 5 minutes.', 'warning');
                self.clearVitalSignsChart();
                return;
            }
            
            self.updateVitalSignsChart(vitalSignsData);
            
            var patient = self.getPatientById(patientId);
            if (patient) {
                self.showSystemStatus('Displaying ' + vitalSignsData.length + ' vital signs records for ' + patient.Name, 'success');
            }
            
        }).catch(function(error) {
            console.error('Error loading vital signs:', error);
            self.showSystemStatus('Error loading vital signs: ' + error.message, 'error');
            self.clearVitalSignsChart();
        });
    };
    
    // Update vital signs chart with real data
    HealthcareDashboard.prototype.updateVitalSignsChart = function(vitalSignsData) {
        var canvas = document.getElementById('vitalSignsChart');
        if (!canvas) return;
        
        var ctx = canvas.getContext('2d');
        
        if (!vitalSignsData || vitalSignsData.length === 0) {
            this.clearVitalSignsChart();
            return;
        }
        
        // Prepare data
        var labels = [];
        var heartRateData = [];
        var systolicBPData = [];
        var temperatureData = [];
        var oxygenSatData = [];
        
        for (var i = 0; i < vitalSignsData.length; i++) {
            var vs = vitalSignsData[i];
            var date = new Date(vs.Timestamp);
            labels.push(date.toLocaleTimeString());
            heartRateData.push(vs.HeartRate);
            systolicBPData.push(vs.SystolicBP);
            temperatureData.push(vs.Temperature);
            oxygenSatData.push(vs.OxygenSaturation);
        }

        // Destroy existing chart
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
                scales: {
                    x: {
                        display: true,
                        title: { display: true, text: 'Time' }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Heart Rate / Blood Pressure' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Temperature (°F)' },
                        grid: { drawOnChartArea: false }
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
                        text: 'Real-time Vital Signs - ' + this.getPatientName(this.selectedPatientId)
                    },
                    legend: { display: true, position: 'top' }
                }
            }
        });
        
        console.log('Chart updated with', vitalSignsData.length, 'real data points');
    };
    
    // Clear vital signs chart
    HealthcareDashboard.prototype.clearVitalSignsChart = function() {
        if (this.vitalSignsChart) {
            this.vitalSignsChart.destroy();
            this.vitalSignsChart = null;
        }
        
        var canvas = document.getElementById('vitalSignsChart');
        if (!canvas) return;
        
        var ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#6c757d';
        ctx.textAlign = 'center';
        ctx.fillText('Select a patient to view vital signs', ctx.canvas.width / 2, ctx.canvas.height / 2);
        ctx.fillText('Data generates every 5 minutes', ctx.canvas.width / 2, ctx.canvas.height / 2 + 25);
    };
    
    // Setup event listeners
    HealthcareDashboard.prototype.setupEventListeners = function() {
        var self = this;
        
        // Auto-refresh
        document.addEventListener('keydown', function(e) {
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                self.refreshData();
            }
        });
    };
    
    // Start auto refresh
    HealthcareDashboard.prototype.startAutoRefresh = function() {
        var self = this;
        
        // Refresh every 30 seconds to get new data
        this.refreshInterval = setInterval(function() {
            console.log('Auto-refreshing data...');
            self.refreshData();
        }, 30000);
        
        console.log('Auto-refresh started (30 second intervals)');
    };
    
    // Refresh data from APIs
    HealthcareDashboard.prototype.refreshData = function() {
        var self = this;
        
        if (this.currentView === 'dashboard') {
            console.log('Refreshing dashboard data...');
            
            this.loadInitialData().then(function() {
                // Refresh chart if patient is selected
                if (self.selectedPatientId) {
                    self.loadPatientVitalSigns(self.selectedPatientId);
                }
            }).catch(function(error) {
                console.error('Error refreshing data:', error);
                self.showSystemStatus('Error refreshing data: ' + error.message, 'error');
            });
        }
    };
    
    // View management
    HealthcareDashboard.prototype.showDashboard = function() {
        this.currentView = 'dashboard';
        this.hideAllViews();
        var dashboardView = document.getElementById('dashboardView');
        if (dashboardView) dashboardView.style.display = 'block';
        this.setActiveNavItem('Dashboard');
        this.refreshData();
    };

    HealthcareDashboard.prototype.showPatients = function() {
        this.currentView = 'patients';
        this.hideAllViews();
        var patientsView = document.getElementById('patientsView');
        if (patientsView) patientsView.style.display = 'block';
        this.setActiveNavItem('Patients');
        this.updateAllPatientsTable();
    };

    HealthcareDashboard.prototype.showAlerts = function() {
        this.currentView = 'alerts';
        this.hideAllViews();
        var alertsView = document.getElementById('alertsView');
        if (alertsView) alertsView.style.display = 'block';
        this.setActiveNavItem('Alerts');
        this.loadAllAlerts();
    };

    // Update all patients table for patients view
    HealthcareDashboard.prototype.updateAllPatientsTable = function() {
        var tbody = document.getElementById('allPatientsTableBody');
        if (!tbody) return;
        
        if (!this.patients || this.patients.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">' +
                '<i class="fas fa-clock fa-2x mb-2"></i>' +
                '<p class="mb-0">Waiting for patient data...</p>' +
                '<small class="text-muted">IoT simulator generates data every 5 minutes</small>' +
                '</td></tr>';
            return;
        }

        var html = '';
        for (var i = 0; i < this.patients.length; i++) {
            var patient = this.patients[i];
            html += '<tr>' +
                '<td><strong>' + patient.PatientId + '</strong></td>' +
                '<td>' + patient.Name + '</td>' +
                '<td>' + (patient.Age || 'N/A') + '</td>' +
                '<td>' + (patient.Gender || 'N/A') + '</td>' +
                '<td><span class="badge bg-info">' + patient.RoomNumber + '</span></td>' +
                '<td><span class="status-badge status-' + (patient.Status || 'active').toLowerCase() + '">' + (patient.Status || 'Active') + '</span></td>' +
                '<td><span class="status-badge status-' + (patient.Condition || 'normal').toLowerCase() + '">' + (patient.Condition || 'Normal') + '</span></td>' +
                '<td>' +
                '<button class="btn btn-sm btn-outline-primary me-1" onclick="showPatientDetails(\'' + patient.PatientId + '\')">' +
                '<i class="fas fa-edit"></i> Edit</button>' +
                '<button class="btn btn-sm btn-outline-danger" onclick="deletePatient(\'' + patient.PatientId + '\')">' +
                '<i class="fas fa-trash"></i> Delete</button>' +
                '</td>' +
                '</tr>';
        }
        tbody.innerHTML = html;
    };

    // Load all alerts for alerts view
    HealthcareDashboard.prototype.loadAllAlerts = function() {
        var self = this;
        
        console.log('Loading all alerts...');
        
        self.api.getAllAlerts(100).then(function(response) {
            var allAlerts = response.alerts || [];
            var alertsContainer = document.getElementById('allAlertsList');
            
            if (!alertsContainer) return;
            
            if (allAlerts.length === 0) {
                alertsContainer.innerHTML = '<div class="text-center text-muted">' +
                    '<i class="fas fa-shield-alt fa-3x mb-3"></i>' +
                    '<h4>No Alerts Found</h4>' +
                    '<p>The system is running smoothly with no recent alerts.</p>' +
                    '</div>';
                return;
            }

            var alertsHtml = '';
            for (var i = 0; i < allAlerts.length; i++) {
                var alert = allAlerts[i];
                alertsHtml += '<div class="card mb-3 alert-item alert-' + (alert.AlertType || 'info').toLowerCase() + '">' +
                    '<div class="card-body">' +
                    '<div class="d-flex justify-content-between align-items-start">' +
                    '<div>' +
                    '<h5 class="card-title">' +
                    '<i class="fas fa-' + self.getAlertIcon(alert.AlertType) + ' me-2"></i>' +
                    (alert.AlertType || 'Alert') + ' - Patient ' + alert.PatientId +
                    '</h5>' +
                    '<p class="card-text">' + (alert.Message || 'No message') + '</p>' +
                    '<small class="text-muted">' +
                    '<i class="fas fa-clock me-1"></i>' +
                    self.formatDateTime(alert.Timestamp) +
                    '</small>' +
                    '</div>' +
                    '<div class="text-end">' +
                    '<span class="badge bg-' + self.getStatusBadgeColor(alert.Status) + '">' + (alert.Status || 'SENT') + '</span>' +
                    (alert.Status !== 'ACKNOWLEDGED' ? 
                        '<button class="btn btn-sm btn-outline-primary mt-2" onclick="acknowledgeAlert(\'' + alert.AlertId + '\')">' +
                        '<i class="fas fa-check"></i> Acknowledge</button>' : '') +
                    '</div>' +
                    '</div>' +
                    '</div>' +
                    '</div>';
            }
            
            alertsContainer.innerHTML = alertsHtml;

        }).catch(function(error) {
            console.error('Error loading all alerts:', error);
            var alertsContainer = document.getElementById('allAlertsList');
            if (alertsContainer) {
                alertsContainer.innerHTML = '<div class="text-center text-muted">' +
                    '<i class="fas fa-exclamation-triangle fa-3x mb-3"></i>' +
                    '<h4>Error Loading Alerts</h4>' +
                    '<p>Unable to load alerts: ' + error.message + '</p>' +
                    '</div>';
            }
        });
    };

    // Patient management functions
    HealthcareDashboard.prototype.showAddPatientModal = function() {
        var modal = document.getElementById('addPatientModal');
        if (modal && typeof bootstrap !== 'undefined') {
            var bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        }
    };

    HealthcareDashboard.prototype.addPatient = function() {
        var self = this;
        
        try {
            var patientData = {
                PatientId: document.getElementById('patientId').value,
                Name: document.getElementById('patientName').value,
                Age: parseInt(document.getElementById('patientAge').value),
                Gender: document.getElementById('patientGender').value,
                RoomNumber: document.getElementById('roomNumber').value,
                Status: 'Active',
                Condition: 'Stable'
            };

            self.api.createPatient(patientData).then(function(response) {
                // Close modal
                var modal = document.getElementById('addPatientModal');
                if (modal && typeof bootstrap !== 'undefined') {
                    var bootstrapModal = bootstrap.Modal.getInstance(modal);
                    if (bootstrapModal) bootstrapModal.hide();
                }
                
                self.showSystemStatus('Patient added successfully', 'success');
                self.refreshData();
                
                // Clear form
                var form = document.getElementById('addPatientForm');
                if (form) form.reset();

            }).catch(function(error) {
                console.error('Error adding patient:', error);
                self.showSystemStatus('Error adding patient: ' + error.message, 'error');
            });

        } catch (error) {
            console.error('Error in addPatient:', error);
            self.showSystemStatus('Error adding patient: ' + error.message, 'error');
        }
    };

    HealthcareDashboard.prototype.deletePatient = function(patientId) {
        var self = this;
        
        if (!confirm('Are you sure you want to deactivate this patient?')) {
            return;
        }

        self.api.deletePatient(patientId).then(function(response) {
            self.showSystemStatus('Patient deactivated successfully', 'success');
            self.refreshData();
        }).catch(function(error) {
            console.error('Error deleting patient:', error);
            self.showSystemStatus('Error deactivating patient: ' + error.message, 'error');
        });
    };

    // Alert management
    HealthcareDashboard.prototype.acknowledgeAlert = function(alertId) {
        var self = this;
        
        self.api.acknowledgeAlert(alertId).then(function(response) {
            self.showSystemStatus('Alert acknowledged successfully', 'success');
            self.loadAllAlerts(); // Refresh the alerts list
        }).catch(function(error) {
            console.error('Error acknowledging alert:', error);
            self.showSystemStatus('Error acknowledging alert: ' + error.message, 'error');
        });
    };
    
    HealthcareDashboard.prototype.hideAllViews = function() {
        var views = document.querySelectorAll('.view');
        for (var i = 0; i < views.length; i++) {
            views[i].style.display = 'none';
        }
    };
    
    HealthcareDashboard.prototype.setActiveNavItem = function(activeText) {
        var links = document.querySelectorAll('.nav-link');
        for (var i = 0; i < links.length; i++) {
            links[i].classList.remove('active');
            if (links[i].textContent.indexOf(activeText) !== -1) {
                links[i].classList.add('active');
            }
        }
    };
    
    // Utility functions
    HealthcareDashboard.prototype.getPatientById = function(patientId) {
        for (var i = 0; i < this.patients.length; i++) {
            if (this.patients[i].PatientId === patientId) {
                return this.patients[i];
            }
        }
        return null;
    };
    
    HealthcareDashboard.prototype.getPatientName = function(patientId) {
        var patient = this.getPatientById(patientId);
        return patient ? patient.Name : 'Unknown Patient';
    };
    
    HealthcareDashboard.prototype.getAlertIcon = function(alertType) {
        switch ((alertType || '').toLowerCase()) {
            case 'critical': return 'exclamation-triangle';
            case 'warning': return 'exclamation-circle';
            case 'info': return 'info-circle';
            default: return 'bell';
        }
    };
    
    HealthcareDashboard.prototype.formatTime = function(timestamp) {
        if (!timestamp) return 'Unknown';
        var date = new Date(timestamp);
        return date.toLocaleTimeString();
    };
    
    HealthcareDashboard.prototype.formatDateTime = function(timestamp) {
        if (!timestamp) return 'Unknown';
        var date = new Date(timestamp);
        return date.toLocaleString();
    };

    HealthcareDashboard.prototype.getStatusBadgeColor = function(status) {
        switch ((status || '').toLowerCase()) {
            case 'acknowledged': return 'success';
            case 'sent': return 'primary';
            default: return 'secondary';
        }
    };
    
    HealthcareDashboard.prototype.showSystemStatus = function(message, type) {
        var statusElement = document.getElementById('statusMessage');
        var alertElement = document.getElementById('systemStatus');
        
        if (!statusElement || !alertElement) return;
        
        statusElement.textContent = message;
        alertElement.className = 'alert alert-dismissible fade show';
        
        switch (type) {
            case 'success': alertElement.classList.add('alert-success'); break;
            case 'error': alertElement.classList.add('alert-danger'); break;
            case 'warning': alertElement.classList.add('alert-warning'); break;
            default: alertElement.classList.add('alert-info');
        }
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            if (alertElement.style.display !== 'none') {
                alertElement.style.display = 'none';
            }
        }, 5000);
    };
    
    HealthcareDashboard.prototype.showLoading = function() {
        this.showSystemStatus('Connecting to healthcare monitoring system...', 'info');
    };
    
    // Global functions for onclick handlers
    window.showDashboard = function() {
        if (healthcareDashboard) healthcareDashboard.showDashboard();
    };

    window.showPatients = function() {
        if (healthcareDashboard) healthcareDashboard.showPatients();
    };

    window.showAlerts = function() {
        if (healthcareDashboard) healthcareDashboard.showAlerts();
    };
    
    window.selectPatient = function() {
        if (healthcareDashboard) healthcareDashboard.selectPatient();
    };
    
    window.selectPatientFromButton = function(patientId) {
        if (healthcareDashboard) healthcareDashboard.selectPatientFromButton(patientId);
    };
    
    window.showPatientDetails = function(patientId) {
        console.log('Show patient details for:', patientId);
        if (healthcareDashboard) {
            healthcareDashboard.showSystemStatus('Patient details feature coming soon', 'info');
        }
    };

    window.showAddPatientModal = function() {
        if (healthcareDashboard) healthcareDashboard.showAddPatientModal();
    };

    window.addPatient = function() {
        if (healthcareDashboard) healthcareDashboard.addPatient();
    };

    window.deletePatient = function(patientId) {
        if (healthcareDashboard) healthcareDashboard.deletePatient(patientId);
    };

    window.acknowledgeAlert = function(alertId) {
        if (healthcareDashboard) healthcareDashboard.acknowledgeAlert(alertId);
    };
    
    // Initialize when DOM is ready
    function initializeDashboard() {
        console.log('DOM loaded, initializing healthcare dashboard with real data...');
        try {
            healthcareDashboard = new HealthcareDashboard();
            window.healthcareDashboard = healthcareDashboard;
            console.log('Healthcare dashboard initialized successfully');
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
        }
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeDashboard);
    } else {
        initializeDashboard();
    }
    
})();