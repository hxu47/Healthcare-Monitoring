// API Service for Patient Vital Signs Monitoring System
// Real API calls only - no mock data

(function() {
    'use strict';
    
    // Healthcare API Constructor Function
    function HealthcareAPI() {
        this.baseURL = '';
        this.endpoints = {
            PATIENTS: '/patients',
            VITAL_SIGNS: '/vitalsigns',
            ALERTS: '/alerts'
        };
        
        // Get config from window
        if (window.HEALTHCARE_CONFIG) {
            this.baseURL = window.HEALTHCARE_CONFIG.API_BASE_URL || '';
            this.endpoints = window.HEALTHCARE_CONFIG.ENDPOINTS || this.endpoints;
        }
        
        console.log('HealthcareAPI initialized with baseURL:', this.baseURL);
    }

    // Generic API request method
    HealthcareAPI.prototype.makeRequest = function(endpoint, options) {
        var self = this;
        options = options || {};
        
        var url = this.baseURL + endpoint;
        
        var defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        };

        // Merge options
        var requestOptions = {};
        for (var key in defaultOptions) {
            requestOptions[key] = defaultOptions[key];
        }
        for (var key in options) {
            if (key === 'headers') {
                requestOptions.headers = {};
                for (var headerKey in defaultOptions.headers) {
                    requestOptions.headers[headerKey] = defaultOptions.headers[headerKey];
                }
                for (var headerKey in options.headers) {
                    requestOptions.headers[headerKey] = options.headers[headerKey];
                }
            } else {
                requestOptions[key] = options[key];
            }
        }

        return new Promise(function(resolve, reject) {
            console.log('Making API request to:', url);
            
            // Check if fetch is available
            if (typeof fetch === 'undefined') {
                console.error('Fetch API not available');
                reject(new Error('Fetch API not supported'));
                return;
            }
            
            fetch(url, requestOptions)
                .then(function(response) {
                    console.log('API response status:', response.status, 'for', endpoint);
                    
                    if (!response.ok) {
                        return response.json().then(function(errorData) {
                            throw new Error(errorData.error || 'HTTP ' + response.status + ': ' + response.statusText);
                        }).catch(function() {
                            throw new Error('HTTP ' + response.status + ': ' + response.statusText);
                        });
                    }
                    return response.json();
                })
                .then(function(data) {
                    console.log('API response data for ' + endpoint + ':', data);
                    resolve(data);
                })
                .catch(function(error) {
                    console.error('API Error for ' + endpoint + ':', error);
                    
                    // Handle network errors
                    if (error.name === 'TypeError' && error.message.indexOf('fetch') !== -1) {
                        reject(new Error('Network error: Unable to connect to the healthcare system. Please check your connection.'));
                    } else {
                        reject(error);
                    }
                });
        });
    };

    // Patient Management API calls
    HealthcareAPI.prototype.getAllPatients = function(roomNumber) {
        var queryParams = roomNumber ? '?room=' + encodeURIComponent(roomNumber) : '';
        return this.makeRequest(this.endpoints.PATIENTS + queryParams);
    };

    HealthcareAPI.prototype.getPatient = function(patientId) {
        return this.makeRequest(this.endpoints.PATIENTS + '/' + patientId);
    };

    HealthcareAPI.prototype.createPatient = function(patientData) {
        return this.makeRequest(this.endpoints.PATIENTS, {
            method: 'POST',
            body: JSON.stringify(patientData)
        });
    };

    HealthcareAPI.prototype.updatePatient = function(patientId, updateData) {
        return this.makeRequest(this.endpoints.PATIENTS + '/' + patientId, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
    };

    HealthcareAPI.prototype.deletePatient = function(patientId) {
        return this.makeRequest(this.endpoints.PATIENTS + '/' + patientId, {
            method: 'DELETE'
        });
    };

    // Vital Signs API calls
    HealthcareAPI.prototype.getVitalSigns = function(patientId, timeRange) {
        var queryParams = '?timeRange=' + (timeRange || '1h');
        if (patientId) {
            queryParams += '&patientId=' + encodeURIComponent(patientId);
        }
        return this.makeRequest(this.endpoints.VITAL_SIGNS + queryParams);
    };

    HealthcareAPI.prototype.getLatestVitalSigns = function(patientId) {
        return this.makeRequest(this.endpoints.VITAL_SIGNS + '?patientId=' + patientId + '&latest=true');
    };

    HealthcareAPI.prototype.getVitalSignsHistory = function(patientId, startTime, endTime) {
        var queryParams = '?patientId=' + patientId + '&startTime=' + startTime + '&endTime=' + endTime;
        return this.makeRequest(this.endpoints.VITAL_SIGNS + queryParams);
    };

    // Alert Management API calls
    HealthcareAPI.prototype.getAllAlerts = function(limit) {
        return this.makeRequest(this.endpoints.ALERTS + '?limit=' + (limit || 50));
    };

    HealthcareAPI.prototype.getPatientAlerts = function(patientId, limit) {
        return this.makeRequest(this.endpoints.ALERTS + '?patientId=' + patientId + '&limit=' + (limit || 20));
    };

    HealthcareAPI.prototype.getRecentAlerts = function(hours) {
        return this.makeRequest(this.endpoints.ALERTS + '?hours=' + (hours || 24));
    };

    HealthcareAPI.prototype.acknowledgeAlert = function(alertId) {
        if (!alertId) {
            return Promise.reject(new Error('Alert ID is required'));
        }
        
        console.log('API: Acknowledging alert:', alertId);
        
        // Construct the correct URL path for acknowledgment
        var acknowledgeEndpoint = this.endpoints.ALERTS + '/' + alertId + '/acknowledge';
        console.log('API: Acknowledge endpoint:', acknowledgeEndpoint);
        
        return this.makeRequest(acknowledgeEndpoint, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    };

    // Dashboard and Analytics API calls
    HealthcareAPI.prototype.getDashboardStats = function() {
        var self = this;
        
        return new Promise(function(resolve, reject) {
            console.log('Getting dashboard stats from APIs...');
            
            Promise.all([
                self.getAllPatients(),
                self.getRecentAlerts(24) // Get alerts from last 24 hours
            ]).then(function(responses) {
                var patientsResponse = responses[0];
                var alertsResponse = responses[1];
                
                var patients = patientsResponse.patients || [];
                var alerts = alertsResponse.alerts || [];

                // Calculate patient status distribution
                var statusCounts = {
                    total: patients.length,
                    normal: 0,
                    warning: 0,
                    critical: 0,
                    active: 0,
                    inactive: 0
                };

                for (var i = 0; i < patients.length; i++) {
                    var patient = patients[i];
                    var condition = (patient.Condition || 'normal').toLowerCase();
                    
                    if (condition === 'stable' || condition === 'normal') {
                        statusCounts.normal++;
                    } else if (condition === 'warning') {
                        statusCounts.warning++;
                    } else if (condition === 'critical') {
                        statusCounts.critical++;
                    }

                    var status = (patient.Status || 'active').toLowerCase();
                    if (status === 'active') {
                        statusCounts.active++;
                    } else {
                        statusCounts.inactive++;
                    }
                }

                resolve({
                    patients: statusCounts,
                    recentAlerts: alerts.length,
                    systemStatus: 'operational'
                });
                
            }).catch(function(error) {
                console.error('Error getting dashboard stats:', error);
                reject(error);
            });
        });
    };

    // Health check for system status
    HealthcareAPI.prototype.healthCheck = function() {
        var self = this;
        
        return new Promise(function(resolve, reject) {
            self.getAllPatients().then(function(response) {
                resolve({
                    status: 'healthy',
                    timestamp: new Date().toISOString(),
                    patientsCount: (response.patients || []).length
                });
            }).catch(function(error) {
                resolve({
                    status: 'unhealthy',
                    timestamp: new Date().toISOString(),
                    error: error.message
                });
            });
        });
    };

    // Utility methods for data formatting
    HealthcareAPI.prototype.formatPatientData = function(rawPatient) {
        return {
            PatientId: rawPatient.PatientId,
            Name: rawPatient.Name,
            Age: parseInt(rawPatient.Age),
            Gender: rawPatient.Gender,
            RoomNumber: rawPatient.RoomNumber,
            Status: rawPatient.Status || 'Active',
            Condition: rawPatient.Condition || 'Stable',
            EmergencyContact: rawPatient.EmergencyContact || '',
            MedicalHistory: rawPatient.MedicalHistory || '',
            Allergies: rawPatient.Allergies || '',
            CurrentMedications: rawPatient.CurrentMedications || [],
            AdmissionDate: rawPatient.AdmissionDate || new Date().toISOString()
        };
    };

    HealthcareAPI.prototype.formatVitalSigns = function(rawVitalSigns) {
        return {
            PatientId: rawVitalSigns.PatientId,
            Timestamp: rawVitalSigns.Timestamp,
            HeartRate: parseFloat(rawVitalSigns.HeartRate),
            SystolicBP: parseFloat(rawVitalSigns.SystolicBP),
            DiastolicBP: parseFloat(rawVitalSigns.DiastolicBP),
            Temperature: parseFloat(rawVitalSigns.Temperature),
            OxygenSaturation: parseFloat(rawVitalSigns.OxygenSaturation),
            DeviceId: rawVitalSigns.DeviceId,
            RoomNumber: rawVitalSigns.RoomNumber
        };
    };

    // Create global API instance
    window.healthcareAPI = new HealthcareAPI();
    
    // For debugging
    console.log('HealthcareAPI loaded successfully - Real data mode');

    // Export for module usage if needed
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = HealthcareAPI;
    }

})();