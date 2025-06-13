// Configuration for Patient Vital Signs Monitoring System
// Simple, compatible version

(function() {
    'use strict';
    
    // Configuration object
    var CONFIG = {
        API_BASE_URL: '', // Will be populated by deployment script
        PROJECT_NAME: 'VitalSignsMonitoring',
        REGION: 'us-east-1',
        
        // API Endpoints
        ENDPOINTS: {
            PATIENTS: '/patients',
            VITAL_SIGNS: '/vitalsigns',
            ALERTS: '/alerts'
        },
        
        // Vital Signs Thresholds for Dashboard Visualization
        VITAL_THRESHOLDS: {
            HEART_RATE: { 
                min: 60, max: 100,
                critical_low: 50, critical_high: 120,
                warning_low: 55, warning_high: 110
            },
            SYSTOLIC_BP: { 
                min: 90, max: 140,
                critical_low: 80, critical_high: 180,
                warning_low: 85, warning_high: 160
            },
            DIASTOLIC_BP: { 
                min: 60, max: 90,
                critical_low: 50, critical_high: 120,
                warning_low: 55, warning_high: 100
            },
            TEMPERATURE: { 
                min: 97.0, max: 99.5,
                critical_low: 95.0, critical_high: 101.5,
                warning_low: 96.0, warning_high: 100.5
            },
            OXYGEN_SAT: { 
                min: 95, max: 100,
                critical_low: 85, critical_high: 100,
                warning_low: 90, warning_high: 100
            }
        },
        
        // Chart Configuration
        CHART_CONFIG: {
            UPDATE_INTERVAL: 30000, // 30 seconds
            MAX_DATA_POINTS: 50,
            ANIMATION_DURATION: 750,
            COLORS: {
                NORMAL: '#28a745',
                WARNING: '#ffc107', 
                CRITICAL: '#dc3545',
                PRIMARY: '#007bff'
            }
        },
        
        // Auto-refresh settings
        AUTO_REFRESH: {
            ENABLED: true,
            INTERVAL: 30000, // 30 seconds
            DASHBOARD_REFRESH: 60000, // 1 minute for dashboard stats
            CHART_REFRESH: 30000 // 30 seconds for charts
        },
        
        // Data generation info (for display purposes)
        DATA_GENERATION: {
            FREQUENCY: '5 minutes',
            PATIENTS_COUNT: 5,
            RECORDS_PER_CYCLE: 5,
            METHOD: 'Automated IoT Simulation'
        }
    };

    // Make CONFIG available globally
    window.HEALTHCARE_CONFIG = CONFIG;
    
    // Log for debugging
    console.log('Healthcare Config loaded:', CONFIG);

    // Export for module usage if needed
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = CONFIG;
    }

})();