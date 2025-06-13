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
kinesis_client = boto3.client('kinesis')

# Environment variables
PATIENT_RECORDS_TABLE = os.environ['PATIENT_RECORDS_TABLE']
KINESIS_STREAM_NAME = "VitalSignsMonitoring-vital-signs-stream"

# Get DynamoDB table
patient_table = dynamodb.Table(PATIENT_RECORDS_TABLE)

def lambda_handler(event, context):
    """
    Lambda function to simulate IoT sensor data for patient vital signs.
    This function generates realistic vital signs data and sends it directly to Kinesis.
    Fixed version that bypasses IoT Core publishing issues.
    """
    
    try:
        # Get list of active patients
        patients = get_active_patients()
        
        if not patients:
            print("No active patients found. Creating sample patients...")
            create_sample_patients()
            patients = get_active_patients()
        
        records_sent = 0
        alerts_generated = 0
        
        # Generate and send vital signs for each patient
        for patient in patients:
            patient_id = patient['PatientId']
            
            # Generate realistic vital signs based on patient condition
            vital_signs = generate_vital_signs(patient)
            
            # Send directly to Kinesis (bypassing IoT Core)
            success = send_to_kinesis(patient_id, vital_signs)
            
            if success:
                records_sent += 1
                print(f"✅ Generated vital signs for patient {patient_id}: {vital_signs}")
                
                # Check if this would generate an alert
                patient_status = determine_patient_status(vital_signs)
                if patient_status in ['Critical', 'Warning']:
                    alerts_generated += 1
            else:
                print(f"❌ Failed to send vital signs for patient {patient_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully sent vital signs for {records_sent} patients to Kinesis',
                'patients_processed': len(patients),
                'records_sent': records_sent,
                'alerts_generated': alerts_generated,
                'method': 'direct_kinesis',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        }
        
    except Exception as e:
        print(f"Error in IoT simulator: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'method': 'direct_kinesis'
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
    device_types = ['monitor-1', 'monitor-2', 'pulse-ox', 'bp-cuff', 'telemetry']
    device_id = f"{patient['PatientId']}-{random.choice(device_types)}"
    
    return {
        'patientId': patient['PatientId'],
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

def send_to_kinesis(patient_id, vital_signs):
    """Send vital signs data directly to Kinesis"""
    
    try:
        # Create the payload
        payload = json.dumps(vital_signs, default=str)
        
        # Send to Kinesis
        response = kinesis_client.put_record(
            StreamName=KINESIS_STREAM_NAME,
            Data=payload,
            PartitionKey=patient_id
        )
        
        print(f"Sent to Kinesis - ShardId: {response.get('ShardId')}, SequenceNumber: {response.get('SequenceNumber')[:20]}...")
        return True
        
    except Exception as e:
        print(f"Error sending to Kinesis: {str(e)}")
        return False

def determine_patient_status(vital_signs):
    """Determine patient status based on vital signs"""
    
    try:
        heart_rate = float(vital_signs.get('heartRate', 0))
        systolic_bp = float(vital_signs.get('systolicBP', 0))
        temperature = float(vital_signs.get('temperature', 0))
        oxygen_sat = float(vital_signs.get('oxygenSaturation', 0))
        
        # Critical conditions (require immediate attention)
        critical_conditions = [
            heart_rate > 120 or heart_rate < 50,
            systolic_bp > 180 or systolic_bp < 90,
            temperature > 101.5 or temperature < 95.0,
            oxygen_sat < 90
        ]
        
        # Warning conditions (require monitoring)
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
            
    except Exception as e:
        print(f"Error determining patient status: {str(e)}")
        return 'Unknown'