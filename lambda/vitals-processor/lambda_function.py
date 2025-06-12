# lambda/vitals-processor/lambda_function.py
import json
import boto3
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import os
import base64

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables
VITAL_SIGNS_TABLE = os.environ['VITAL_SIGNS_TABLE']
ALERT_CONFIG_TABLE = os.environ['ALERT_CONFIG_TABLE']
ALERT_HISTORY_TABLE = os.environ['ALERT_HISTORY_TABLE']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

# Get DynamoDB tables
vital_signs_table = dynamodb.Table(VITAL_SIGNS_TABLE)
alert_config_table = dynamodb.Table(ALERT_CONFIG_TABLE)
alert_history_table = dynamodb.Table(ALERT_HISTORY_TABLE)

def lambda_handler(event, context):
    """
    Process incoming vital signs data from Kinesis stream.
    Store data in DynamoDB and check for alert conditions.
    """
    
    processed_records = 0
    alerts_generated = 0
    
    try:
        # Process each record from Kinesis
        for record in event['Records']:
            # Decode Kinesis data
            if 'kinesis' in record:
                # Data from Kinesis stream
                encoded_data = record['kinesis']['data']
                decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                vital_signs_data = json.loads(decoded_data)
            else:
                # Direct invocation for testing
                vital_signs_data = record
            
            # Process the vital signs data
            result = process_vital_signs_record(vital_signs_data)
            
            if result['processed']:
                processed_records += 1
                
            if result['alert_generated']:
                alerts_generated += 1
        
        print(f"Processed {processed_records} records, generated {alerts_generated} alerts")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'records_processed': processed_records,
                'alerts_generated': alerts_generated
            })
        }
        
    except Exception as e:
        print(f"Error processing vital signs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def process_vital_signs_record(data):
    """Process a single vital signs record"""
    
    try:
        patient_id = data.get('patientId')
        if not patient_id:
            print("No patient ID found in data")
            return {'processed': False, 'alert_generated': False}
        
        # Prepare data for DynamoDB storage
        timestamp = data.get('timestamp', datetime.utcnow().isoformat() + 'Z')
        
        # Convert all numeric values to Decimal for DynamoDB
        vital_signs_item = {
            'PatientId': patient_id,
            'Timestamp': timestamp,
            'DeviceId': data.get('deviceId', 'unknown'),
            'HeartRate': Decimal(str(data.get('heartRate', 0))),
            'SystolicBP': Decimal(str(data.get('systolicBP', 0))),
            'DiastolicBP': Decimal(str(data.get('diastolicBP', 0))),
            'Temperature': Decimal(str(data.get('temperature', 0))),
            'OxygenSaturation': Decimal(str(data.get('oxygenSaturation', 0))),
            'RoomNumber': data.get('roomNumber', 'UNKNOWN'),
            'PatientCondition': data.get('patientCondition', 'Unknown'),
            'ProcessedAt': datetime.utcnow().isoformat() + 'Z',
            # Set TTL for automatic data cleanup (30 days)
            'TTL': int((datetime.utcnow() + timedelta(days=30)).timestamp())
        }
        
        # Add optional sensor metadata
        if 'sensorBatteryLevel' in data:
            vital_signs_item['SensorBatteryLevel'] = Decimal(str(data['sensorBatteryLevel']))
        if 'signalStrength' in data:
            vital_signs_item['SignalStrength'] = Decimal(str(data['signalStrength']))
        if 'dataQuality' in data:
            vital_signs_item['DataQuality'] = data['dataQuality']
        
        # Store in DynamoDB
        vital_signs_table.put_item(Item=vital_signs_item)
        
        # Determine patient status based on vital signs
        patient_status = determine_patient_status(data)
        vital_signs_item['PatientStatus'] = patient_status
        
        # Log patient status for CloudWatch metrics
        print(f"Patient {patient_id} status: {patient_status}")
        
        # Check for alert conditions
        alert_generated = check_and_generate_alerts(patient_id, data, patient_status)
        
        return {'processed': True, 'alert_generated': alert_generated}
        
    except Exception as e:
        print(f"Error processing record for patient {patient_id}: {str(e)}")
        return {'processed': False, 'alert_generated': False}

def determine_patient_status(vital_signs):
    """Determine patient status based on vital signs thresholds"""
    
    heart_rate = vital_signs.get('heartRate', 0)
    systolic_bp = vital_signs.get('systolicBP', 0)
    diastolic_bp = vital_signs.get('diastolicBP', 0)
    temperature = vital_signs.get('temperature', 0)
    oxygen_sat = vital_signs.get('oxygenSaturation', 0)
    
    # Critical conditions (require immediate attention)
    critical_conditions = [
        heart_rate > 120 or heart_rate < 50,
        systolic_bp > 180 or systolic_bp < 90,
        diastolic_bp > 120 or diastolic_bp < 50,
        temperature > 101.5 or temperature < 95.0,
        oxygen_sat < 90
    ]
    
    # Warning conditions (require monitoring)
    warning_conditions = [
        heart_rate > 100 or heart_rate < 60,
        systolic_bp > 140 or systolic_bp < 100,
        diastolic_bp > 90 or diastolic_bp < 60,
        temperature > 99.5 or temperature < 97.0,
        oxygen_sat < 95
    ]
    
    if any(critical_conditions):
        return 'Critical'
    elif any(warning_conditions):
        return 'Warning'
    else:
        return 'Normal'

def check_and_generate_alerts(patient_id, vital_signs, patient_status):
    """Check for alert conditions and generate alerts if necessary"""
    
    try:
        # Always generate alerts for critical status
        if patient_status == 'Critical':
            alert_message = create_critical_alert_message(patient_id, vital_signs)
            send_alert(patient_id, 'CRITICAL', alert_message, vital_signs)
            return True
        
        # Check for specific alert configurations
        alert_configs = get_alert_configurations(patient_id)
        
        for config in alert_configs:
            vital_type = config['VitalType']
            threshold_min = config.get('ThresholdMin')
            threshold_max = config.get('ThresholdMax')
            
            # Get the corresponding vital sign value
            vital_value = get_vital_value(vital_signs, vital_type)
            
            if vital_value is not None:
                if (threshold_min and vital_value < threshold_min) or \
                   (threshold_max and vital_value > threshold_max):
                    
                    alert_message = create_threshold_alert_message(
                        patient_id, vital_type, vital_value, threshold_min, threshold_max
                    )
                    send_alert(patient_id, 'THRESHOLD', alert_message, vital_signs)
                    return True
        
        return False
        
    except Exception as e:
        print(f"Error checking alerts for patient {patient_id}: {str(e)}")
        return False

def get_alert_configurations(patient_id):
    """Get alert configurations for a specific patient"""
    
    try:
        response = alert_config_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('PatientId').eq(patient_id)
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting alert configurations: {str(e)}")
        return []

def get_vital_value(vital_signs, vital_type):
    """Get the vital sign value based on type"""
    
    vital_mapping = {
        'heart_rate': vital_signs.get('heartRate'),
        'systolic_bp': vital_signs.get('systolicBP'),
        'diastolic_bp': vital_signs.get('diastolicBP'),
        'temperature': vital_signs.get('temperature'),
        'oxygen_saturation': vital_signs.get('oxygenSaturation')
    }
    
    return vital_mapping.get(vital_type.lower())

def create_critical_alert_message(patient_id, vital_signs):
    """Create alert message for critical patient status"""
    
    message = f"🚨 CRITICAL ALERT - Patient {patient_id}\n\n"
    message += f"Room: {vital_signs.get('roomNumber', 'Unknown')}\n"
    message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    message += "Vital Signs:\n"
    message += f"• Heart Rate: {vital_signs.get('heartRate', 'N/A')} bpm\n"
    message += f"• Blood Pressure: {vital_signs.get('systolicBP', 'N/A')}/{vital_signs.get('diastolicBP', 'N/A')} mmHg\n"
    message += f"• Temperature: {vital_signs.get('temperature', 'N/A')}°F\n"
    message += f"• Oxygen Saturation: {vital_signs.get('oxygenSaturation', 'N/A')}%\n\n"
    message += "⚡ IMMEDIATE MEDICAL ATTENTION REQUIRED"
    
    return message

def create_threshold_alert_message(patient_id, vital_type, vital_value, threshold_min, threshold_max):
    """Create alert message for threshold violations"""
    
    message = f"⚠️ THRESHOLD ALERT - Patient {patient_id}\n\n"
    message += f"Vital Sign: {vital_type.replace('_', ' ').title()}\n"
    message += f"Current Value: {vital_value}\n"
    
    if threshold_min and vital_value < threshold_min:
        message += f"Below minimum threshold: {threshold_min}\n"
    elif threshold_max and vital_value > threshold_max:
        message += f"Above maximum threshold: {threshold_max}\n"
    
    message += f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "Please review patient status."
    
    return message

def send_alert(patient_id, alert_type, message, vital_signs):
    """Send alert via SNS and store in alert history"""
    
    try:
        alert_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Store alert in history table
        alert_item = {
            'AlertId': alert_id,
            'Timestamp': timestamp,
            'PatientId': patient_id,
            'AlertType': alert_type,
            'Message': message,
            'VitalSigns': {
                'HeartRate': Decimal(str(vital_signs.get('heartRate', 0))),
                'SystolicBP': Decimal(str(vital_signs.get('systolicBP', 0))),
                'DiastolicBP': Decimal(str(vital_signs.get('diastolicBP', 0))),
                'Temperature': Decimal(str(vital_signs.get('temperature', 0))),
                'OxygenSaturation': Decimal(str(vital_signs.get('oxygenSaturation', 0)))
            },
            'RoomNumber': vital_signs.get('roomNumber', 'Unknown'),
            'Status': 'SENT',
            # Set TTL for automatic cleanup (90 days for alerts)
            'TTL': int((datetime.utcnow() + timedelta(days=90)).timestamp())
        }
        
        alert_history_table.put_item(Item=alert_item)
        
        # Send SNS notification
        sns_message = {
            'default': message,
            'email': message,
            'sms': f"ALERT: Patient {patient_id} - {alert_type} condition detected. Check dashboard immediately."
        }
        
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(sns_message),
            MessageStructure='json',
            Subject=f"Patient Alert - {patient_id} ({alert_type})"
        )
        
        print(f"Alert sent for patient {patient_id}: {alert_type}")
        print(f"CRITICAL" if alert_type == 'CRITICAL' else f"WARNING")
        
        return True
        
    except Exception as e:
        print(f"Error sending alert: {str(e)}")
        return False

def create_default_alert_config(patient_id):
    """Create default alert configurations for a patient"""
    
    default_configs = [
        {
            'PatientId': patient_id,
            'VitalType': 'heart_rate',
            'ThresholdMin': Decimal('50'),
            'ThresholdMax': Decimal('120'),
            'AlertEnabled': True
        },
        {
            'PatientId': patient_id,
            'VitalType': 'systolic_bp',
            'ThresholdMin': Decimal('90'),
            'ThresholdMax': Decimal('180'),
            'AlertEnabled': True
        },
        {
            'PatientId': patient_id,
            'VitalType': 'temperature',
            'ThresholdMin': Decimal('95.0'),
            'ThresholdMax': Decimal('101.5'),
            'AlertEnabled': True
        },
        {
            'PatientId': patient_id,
            'VitalType': 'oxygen_saturation',
            'ThresholdMin': Decimal('90'),
            'ThresholdMax': Decimal('100'),
            'AlertEnabled': True
        }
    ]
    
    for config in default_configs:
        try:
            alert_config_table.put_item(Item=config)
        except Exception as e:
            print(f"Error creating default config: {str(e)}")