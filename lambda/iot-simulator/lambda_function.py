# lambda/iot-simulator/lambda_function.py
import json
import boto3
import random
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import os

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
iot_client = boto3.client('iot-data')

# Environment variables
IOT_ENDPOINT = os.environ['IOT_ENDPOINT']
PATIENT_RECORDS_TABLE = os.environ['PATIENT_RECORDS_TABLE']

# Get DynamoDB table
patient_table = dynamodb.Table(PATIENT_RECORDS_TABLE)

def lambda_handler(event, context):
    """
    Lambda function to simulate IoT sensor data for patient vital signs.
    This function generates realistic vital signs data and publishes it to IoT Core.
    """
    
    try:
        # Get list of active patients
        patients = get_active_patients()
        
        if not patients:
            print("No active patients found. Creating sample patients...")
            create_sample_patients()
            patients = get_active_patients()
        
        # Generate and publish vital signs for each patient
        for patient in patients:
            patient_id = patient['PatientId']
            
            # Generate realistic vital signs based on patient condition
            vital_signs = generate_vital_signs(patient)
            
            # Publish to IoT Core
            publish_to_iot(patient_id, vital_signs)
            
            print(f"Generated vital signs for patient {patient_id}: {vital_signs}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully generated vital signs for {len(patients)} patients',
                'patients_processed': len(patients)
            })
        }
        
    except Exception as e:
        print(f"Error in IoT simulator: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def get_active_patients():
    """Get list of active patients from DynamoDB"""
    try:
        response = patient_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('Status').eq('Active')
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting active patients: {str(e)}")
        return []

def create_sample_patients():
    """Create sample patients for demonstration"""
    sample_patients = [
        {
            'PatientId': 'PATIENT-001',
            'Name': 'John Smith',
            'Age': Decimal('45'),
            'Gender': 'Male',
            'RoomNumber': 'ICU-101',
            'Status': 'Active',
            'Condition': 'Stable',
            'AdmissionDate': datetime.now().isoformat(),
            'EmergencyContact': '+1-555-0123'
        },
        {
            'PatientId': 'PATIENT-002',
            'Name': 'Sarah Johnson',
            'Age': Decimal('67'),
            'Gender': 'Female',
            'RoomNumber': 'ICU-102',
            'Status': 'Active',
            'Condition': 'Critical',
            'AdmissionDate': datetime.now().isoformat(),
            'EmergencyContact': '+1-555-0124'
        },
        {
            'PatientId': 'PATIENT-003',
            'Name': 'Michael Brown',
            'Age': Decimal('32'),
            'Gender': 'Male',
            'RoomNumber': 'WARD-201',
            'Status': 'Active',
            'Condition': 'Stable',
            'AdmissionDate': datetime.now().isoformat(),
            'EmergencyContact': '+1-555-0125'
        },
        {
            'PatientId': 'PATIENT-004',
            'Name': 'Emily Davis',
            'Age': Decimal('28'),
            'Gender': 'Female',
            'RoomNumber': 'WARD-202',
            'Status': 'Active',
            'Condition': 'Warning',
            'AdmissionDate': datetime.now().isoformat(),
            'EmergencyContact': '+1-555-0126'
        },
        {
            'PatientId': 'PATIENT-005',
            'Name': 'Robert Wilson',
            'Age': Decimal('78'),
            'Gender': 'Male',
            'RoomNumber': 'ICU-103',
            'Status': 'Active',
            'Condition': 'Critical',
            'AdmissionDate': datetime.now().isoformat(),
            'EmergencyContact': '+1-555-0127'
        }
    ]
    
    for patient in sample_patients:
        try:
            patient_table.put_item(Item=patient)
            print(f"Created sample patient: {patient['PatientId']}")
        except Exception as e:
            print(f"Error creating patient {patient['PatientId']}: {str(e)}")

def generate_vital_signs(patient):
    """Generate realistic vital signs based on patient condition"""
    
    condition = patient.get('Condition', 'Stable')
    age = int(patient.get('Age', 50))
    
    # Base vital signs with age adjustments
    base_heart_rate = 70 + (age - 40) * 0.2
    base_systolic_bp = 120 + (age - 40) * 0.5
    base_diastolic_bp = 80 + (age - 40) * 0.3
    base_temperature = 98.6
    base_oxygen_sat = 98
    
    # Adjust based on patient condition
    if condition == 'Critical':
        # Critical patients have more volatile and concerning vital signs
        heart_rate = max(40, min(150, base_heart_rate + random.randint(-20, 40)))
        systolic_bp = max(80, min(200, base_systolic_bp + random.randint(-30, 50)))
        diastolic_bp = max(50, min(120, base_diastolic_bp + random.randint(-20, 30)))
        temperature = round(base_temperature + random.uniform(-2.0, 3.0), 1)
        oxygen_sat = max(85, min(100, base_oxygen_sat + random.randint(-10, 2)))
        
    elif condition == 'Warning':
        # Warning patients have slightly abnormal vital signs
        heart_rate = max(50, min(120, base_heart_rate + random.randint(-15, 25)))
        systolic_bp = max(90, min(160, base_systolic_bp + random.randint(-20, 30)))
        diastolic_bp = max(60, min(100, base_diastolic_bp + random.randint(-15, 20)))
        temperature = round(base_temperature + random.uniform(-1.0, 2.0), 1)
        oxygen_sat = max(92, min(100, base_oxygen_sat + random.randint(-5, 2)))
        
    else:  # Stable
        # Stable patients have normal vital signs with small variations
        heart_rate = max(60, min(100, base_heart_rate + random.randint(-10, 15)))
        systolic_bp = max(100, min(140, base_systolic_bp + random.randint(-15, 20)))
        diastolic_bp = max(65, min(90, base_diastolic_bp + random.randint(-10, 15)))
        temperature = round(base_temperature + random.uniform(-0.5, 1.0), 1)
        oxygen_sat = max(95, min(100, base_oxygen_sat + random.randint(-2, 2)))
    
    # Generate timestamp
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Generate device ID (simulating multiple sensors per patient)
    device_types = ['monitor-1', 'monitor-2', 'pulse-ox', 'bp-cuff']
    device_id = f"{patient['PatientId']}-{random.choice(device_types)}"
    
    return {
        'deviceId': device_id,
        'timestamp': timestamp,
        'heartRate': int(heart_rate),
        'systolicBP': int(systolic_bp),
        'diastolicBP': int(diastolic_bp),
        'temperature': float(temperature),
        'oxygenSaturation': int(oxygen_sat),
        'patientCondition': condition,
        'roomNumber': patient.get('RoomNumber', 'UNKNOWN'),
        # Add some metadata
        'sensorBatteryLevel': random.randint(20, 100),
        'signalStrength': random.randint(70, 100),
        'dataQuality': random.choice(['Excellent', 'Good', 'Fair'])
    }

def publish_to_iot(patient_id, vital_signs):
    """Publish vital signs data to IoT Core"""
    
    topic = f"vitalsigns/{patient_id}/data"
    
    # Add patient ID to the payload
    payload = {
        'patientId': patient_id,
        **vital_signs
    }
    
    try:
        response = iot_client.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(payload, default=str)
        )
        print(f"Published to IoT topic {topic}: {response}")
        
    except Exception as e:
        print(f"Error publishing to IoT Core: {str(e)}")
        # For demo purposes, also log to CloudWatch if IoT publish fails
        print(f"VITAL_SIGNS_DATA: {json.dumps(payload, default=str)}")

def determine_patient_status(vital_signs):
    """Determine patient status based on vital signs"""
    
    heart_rate = vital_signs['heartRate']
    systolic_bp = vital_signs['systolicBP']
    temperature = vital_signs['temperature']
    oxygen_sat = vital_signs['oxygenSaturation']
    
    critical_conditions = [
        heart_rate > 120 or heart_rate < 50,
        systolic_bp > 180 or systolic_bp < 90,
        temperature > 101.5 or temperature < 95.0,
        oxygen_sat < 90
    ]
    
    warning_conditions = [
        heart_rate > 100 or heart_rate < 60,
        systolic_bp > 140 or systolic_bp < 100,
        temperature > 99.5 or temperature < 97.0,
        oxygen_sat < 95
    ]
    
    if any(critical_conditions):
        return 'Critical'
    elif any(warning_conditions):
        return 'Warning'
    else:
        return 'Normal'