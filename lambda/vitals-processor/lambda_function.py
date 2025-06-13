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
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Handle different types of invocations
        records = []
        
        if 'Records' in event:
            # This is from Kinesis or direct invocation
            for record in event['Records']:
                if 'kinesis' in record:
                    # From Kinesis stream
                    try:
                        # Decode base64 data from Kinesis
                        encoded_data = record['kinesis']['data']
                        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                        vital_signs_data = json.loads(decoded_data)
                        records.append(vital_signs_data)
                        print(f"Decoded Kinesis data: {vital_signs_data}")
                    except Exception as e:
                        print(f"Error decoding Kinesis record: {str(e)}")
                        continue
                else:
                    # Direct invocation - record is the data itself
                    records.append(record)
                    print(f"Direct invocation data: {record}")
        else:
            # Handle single record direct invocation
            records.append(event)
            print(f"Single record invocation: {event}")
        
        # Process each record
        for vital_signs_data in records:
            try:
                result = process_vital_signs_record(vital_signs_data)
                
                if result['processed']:
                    processed_records += 1
                    
                if result['alert_generated']:
                    alerts_generated += 1
                    
            except Exception as e:
                print(f"Error processing record: {str(e)}")
                continue
        
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
        # Get patient ID - handle different field names
        patient_id = data.get('patientId') or data.get('PatientId')
        if not patient_id:
            print("No patient ID found in data")
            return {'processed': False, 'alert_generated': False}
        
        print(f"Processing data for patient: {patient_id}")
        
        # Prepare data for DynamoDB storage
        timestamp = data.get('timestamp') or datetime.utcnow().isoformat() + 'Z'
        
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
        
        print(f"Storing vital signs item: {json.dumps(vital_signs_item, default=str)}")
        
        # Store in DynamoDB
        vital_signs_table.put_item(Item=vital_signs_item)
        
        print(f"✅ Successfully stored vital signs for patient {patient_id}")
        
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
    
    try:
        heart_rate = float(vital_signs.get('heartRate', 0))
        systolic_bp = float(vital_signs.get('systolicBP', 0))
        diastolic_bp = float(vital_signs.get('diastolicBP', 0))
        temperature = float(vital_signs.get('temperature', 0))
        oxygen_sat = float(vital_signs.get('oxygenSaturation', 0))
        
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
            
    except Exception as e:
        print(f"Error determining patient status: {str(e)}")
        return 'Unknown'

def check_and_generate_alerts(patient_id, vital_signs, patient_status):
    """Check for alert conditions and generate alerts if necessary"""
    
    try:
        # Always generate alerts for critical status
        if patient_status == 'Critical':
            alert_message = create_critical_alert_message(patient_id, vital_signs)
            send_alert(patient_id, 'CRITICAL', alert_message, vital_signs)
            return True
        
        # For demo purposes, also alert on Warning status
        if patient_status == 'Warning':
            alert_message = create_warning_alert_message(patient_id, vital_signs)
            send_alert(patient_id, 'WARNING', alert_message, vital_signs)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error checking alerts for patient {patient_id}: {str(e)}")
        return False

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

def create_warning_alert_message(patient_id, vital_signs):
    """Create alert message for warning patient status"""
    
    message = f"⚠️ WARNING ALERT - Patient {patient_id}\n\n"
    message += f"Room: {vital_signs.get('roomNumber', 'Unknown')}\n"
    message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    message += "Vital Signs:\n"
    message += f"• Heart Rate: {vital_signs.get('heartRate', 'N/A')} bpm\n"
    message += f"• Blood Pressure: {vital_signs.get('systolicBP', 'N/A')}/{vital_signs.get('diastolicBP', 'N/A')} mmHg\n"
    message += f"• Temperature: {vital_signs.get('temperature', 'N/A')}°F\n"
    message += f"• Oxygen Saturation: {vital_signs.get('oxygenSaturation', 'N/A')}%\n\n"
    message += "📋 Please review patient status"
    
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
        return True
        
    except Exception as e:
        print(f"Error sending alert: {str(e)}")
        return False