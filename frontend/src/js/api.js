// API Service for Patient Vital Signs Monitoring System

class HealthcareAPI {
    constructor() {
        this.baseURL = window.HEALTHCARE_CONFIG?.API_BASE_URL || '';
        this.endpoints = window.HEALTHCARE_CONFIG?.ENDPOINTS || {};
    }

    // Generic API request method
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        };

        const requestOptions = { ...defaultOptions, ...options };

        try {
            console.log(`Making request to: ${url}`, requestOptions);
            
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log(`Response from ${endpoint}:`, data);
            return data;

        } catch (error) {
            console.error(`API Error for ${endpoint}:`, error);
            
            // Handle network errors
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Network error: Unable to connect to the healthcare system. Please check your connection.');
            }
            
            throw error;
        }
    }

    // Patient Management API calls
    async getAllPatients(roomNumber = null) {
        const queryParams = roomNumber ? `?room=${encodeURIComponent(roomNumber)}` : '';
        return await this.makeRequest(`${this.endpoints.PATIENTS}${queryParams}`);
    }

    async getPatient(patientId) {
        return await this.makeRequest(`${this.endpoints.PATIENTS}/${patientId}`);
    }

    async createPatient(patientData) {
        return await this.makeRequest(this.endpoints.PATIENTS, {
            method: 'POST',
            body: JSON.stringify(patientData)
        });
    }

    async updatePatient(patientId, updateData) {
        return await this.makeRequest(`${this.endpoints.PATIENTS}/${patientId}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
    }

    async deletePatient(patientId) {
        return await this.makeRequest(`${this.endpoints.PATIENTS}/${patientId}`, {
            method: 'DELETE'
        });
    }

    // Vital Signs API calls
    async getVitalSigns(patientId = null, timeRange = '1h') {
        let queryParams = `?timeRange=${timeRange}`;
        if (patientId) {
            queryParams += `&patientId=${encodeURIComponent(patientId)}`;
        }
        return await this.makeRequest(`${this.endpoints.VITAL_SIGNS}${queryParams}`);
    }

    async getLatestVitalSigns(patientId) {
        return await this.makeRequest(`${this.endpoints.VITAL_SIGNS}?patientId=${patientId}&latest=true`);
    }

    async getVitalSignsHistory(patientId, startTime, endTime) {
        const queryParams = `?patientId=${patientId}&startTime=${startTime}&endTime=${endTime}`;
        return await this.makeRequest(`${this.endpoints.VITAL_SIGNS}${queryParams}`);
    }

    // Alert Management API calls
    async getAllAlerts(limit = 50) {
        return await this.makeRequest(`${this.endpoints.ALERTS}?limit=${limit}`);
    }

    async getPatientAlerts(patientId, limit = 20) {
        return await this.makeRequest(`${this.endpoints.ALERTS}?patientId=${patientId}&limit=${limit}`);
    }

    async getRecentAlerts(hours = 24) {
        return await this.makeRequest(`${this.endpoints.ALERTS}?hours=${hours}`);
    }

    async acknowledgeAlert(alertId) {
        return await this.makeRequest(`${this.endpoints.ALERTS}/${alertId}/acknowledge`, {
            method: 'PUT'
        });
    }

    // Dashboard and Analytics API calls
    async getDashboardStats() {
        try {
            const [patientsResponse, alertsResponse] = await Promise.all([
                this.getAllPatients(),
                this.getRecentAlerts(1) // Last hour alerts
            ]);

            const patients = patientsResponse.patients || [];
            const alerts = alertsResponse.alerts || [];

            // Calculate patient status distribution
            const statusCounts = {
                total: patients.length,
                normal: 0,
                warning: 0,
                critical: 0,
                active: 0,
                inactive: 0
            };

            patients.forEach(patient => {
                // Count by condition
                const condition = patient.Condition?.toLowerCase() || 'normal';
                if (condition === 'stable' || condition === 'normal') {
                    statusCounts.normal++;
                } else if (condition === 'warning') {
                    statusCounts.warning++;
                } else if (condition === 'critical') {
                    statusCounts.critical++;
                }

                // Count by status
                const status = patient.Status?.toLowerCase() || 'active';
                if (status === 'active') {
                    statusCounts.active++;
                } else {
                    statusCounts.inactive++;
                }
            });

            return {
                patients: statusCounts,
                recentAlerts: alerts.length,
                systemStatus: 'operational'
            };

        } catch (error) {
            console.error('Error getting dashboard stats:', error);
            return {
                patients: { total: 0, normal: 0, warning: 0, critical: 0, active: 0, inactive: 0 },
                recentAlerts: 0,
                systemStatus: 'error'
            };
        }
    }

    // Health check for system status
    async healthCheck() {
        try {
            // Simple health check by getting patients count
            const response = await this.getAllPatients();
            return {
                status: 'healthy',
                timestamp: new Date().toISOString(),
                patientsCount: response.patients?.length || 0
            };
        } catch (error) {
            return {
                status: 'unhealthy',
                timestamp: new Date().toISOString(),
                error: error.message
            };
        }
    }

    // Utility methods
    formatPatientData(rawPatient) {
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
    }

    formatVitalSigns(rawVitalSigns) {
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
    }

    // Mock data for development/demo purposes
    generateMockVitalSigns(patientId) {
        const now = new Date();
        const mockData = [];

        for (let i = 0; i < 20; i++) {
            const timestamp = new Date(now.getTime() - (i * 30000)); // 30 second intervals
            mockData.unshift({
                PatientId: patientId,
                Timestamp: timestamp.toISOString(),
                HeartRate: 70 + Math.random() * 30,
                SystolicBP: 120 + Math.random() * 20,
                DiastolicBP: 80 + Math.random() * 15,
                Temperature: 98.6 + (Math.random() - 0.5) * 2,
                OxygenSaturation: 96 + Math.random() * 4,
                DeviceId: `${patientId}-monitor`,
                RoomNumber: 'ICU-101'
            });
        }

        return mockData;
    }

    generateMockAlerts() {
        const alertTypes = ['CRITICAL', 'WARNING', 'INFO'];
        const patientIds = ['PATIENT-001', 'PATIENT-002', 'PATIENT-003'];
        const messages = [
            'Heart rate above threshold',
            'Blood pressure critically high',
            'Oxygen saturation below normal',
            'Temperature spike detected',
            'Irregular vital signs pattern'
        ];

        const mockAlerts = [];
        const now = new Date();

        for (let i = 0; i < 10; i++) {
            const timestamp = new Date(now.getTime() - (i * 300000)); // 5 minute intervals
            mockAlerts.push({
                AlertId: `ALERT-${Date.now()}-${i}`,
                PatientId: patientIds[Math.floor(Math.random() * patientIds.length)],
                AlertType: alertTypes[Math.floor(Math.random() * alertTypes.length)],
                Message: messages[Math.floor(Math.random() * messages.length)],
                Timestamp: timestamp.toISOString(),
                Status: Math.random() > 0.3 ? 'SENT' : 'ACKNOWLEDGED'
            });
        }

        return mockAlerts;
    }
}

// Create global API instance
window.healthcareAPI = new HealthcareAPI();

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HealthcareAPI;
}