# lambda/vitals-api/lambda_function.py
import json
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
import os
from boto3.dynamodb.conditions import Key, Attr

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
VITAL_SIGNS_TABLE = os.environ['VITAL_SIGNS_TABLE']
PATIENT_RECORDS_TABLE = os.environ['PATIENT_RECORDS_TABLE']

# Get DynamoDB tables
vital_signs_table = dynamodb.Table(VITAL_SIGNS_TABLE)
patient_table = dynamodb.Table(PATIENT_RECORDS_TABLE)

def lambda_handler(event, context):
    """
    Handle vital signs API requests for historical and real-time data
    """
    
    try:
        # Parse the API Gateway event
        http_method = event['httpMethod']
        query_params = event.get('queryStringParameters') or {}
        
        # Route based on HTTP method and parameters
        if http_method == 'GET':
            return handle_get_vital_signs(query_params)
        else:
            return create_error_response(405, f"Method {http_method} not allowed")
            
    except Exception as e:
        print(f"Error handling vital signs request: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")

def handle_get_vital_signs(query_params):
    """Handle GET requests for vital signs data"""
    
    patient_id = query_params.get('patientId')
    time_range = query_params.get('timeRange', '1h')
    latest = query_params.get('latest', 'false').lower() == 'true'
    start_time = query_params.get('startTime')
    end_time = query_params.get('endTime')
    limit = int(query_params.get('limit', '100'))
    
    try:
        if patient_id:
            if latest:
                return get_latest_vital_signs(patient_id)
            elif start_time and end_time:
                return get_vital_signs_range(patient_id, start_time, end_time, limit)
            else:
                return get_vital_signs_by_time_range(patient_id, time_range, limit)
        else:
            return get_all_recent_vital_signs(time_range, limit)
            
    except Exception as e:
        print(f"Error in handle_get_vital_signs: {str(e)}")
        return create_error_response(500, f"Error retrieving vital signs: {str(e)}")

def get_latest_vital_signs(patient_id):
    """Get the most recent vital signs for a specific patient"""
    
    try:
        # Query vital signs for patient, ordered by timestamp descending
        response = vital_signs_table.query(
            KeyConditionExpression=Key('PatientId').eq(patient_id),
            ScanIndexForward=False,  # Descending order
            Limit=1
        )
        
        vital_signs = response.get('Items', [])
        
        if not vital_signs:
            return create_error_response(404, f"No vital signs found for patient {patient_id}")
        
        # Get patient information
        patient_info = get_patient_info(patient_id)
        
        result = {
            'patientId': patient_id,
            'latestVitalSigns': convert_decimals(vital_signs[0]),
            'patientInfo': patient_info,
            'timestamp': vital_signs[0]['Timestamp']
        }
        
        return create_success_response(result)
        
    except Exception as e:
        print(f"Error getting latest vital signs for {patient_id}: {str(e)}")
        return create_error_response(500, f"Error retrieving latest vital signs: {str(e)}")

def get_vital_signs_by_time_range(patient_id, time_range, limit):
    """Get vital signs for a patient within a specific time range"""
    
    try:
        # Calculate start time based on time range
        end_time = datetime.utcnow()
        
        if time_range == '1h':
            start_time = end_time - timedelta(hours=1)
        elif time_range == '6h':
            start_time = end_time - timedelta(hours=6)
        elif time_range == '24h':
            start_time = end_time - timedelta(hours=24)
        elif time_range == '7d':
            start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(hours=1)  # Default to 1 hour
        
        start_time_str = start_time.isoformat() + 'Z'
        end_time_str = end_time.isoformat() + 'Z'
        
        return get_vital_signs_range(patient_id, start_time_str, end_time_str, limit)
        
    except Exception as e:
        print(f"Error getting vital signs by time range: {str(e)}")
        return create_error_response(500, f"Error retrieving vital signs: {str(e)}")

def get_vital_signs_range(patient_id, start_time, end_time, limit):
    """Get vital signs for a patient within a specific timestamp range"""
    
    try:
        # Query vital signs within time range
        response = vital_signs_table.query(
            KeyConditionExpression=Key('PatientId').eq(patient_id) & 
                                 Key('Timestamp').between(start_time, end_time),
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        vital_signs = response.get('Items', [])
        
        # Get patient information
        patient_info = get_patient_info(patient_id)
        
        # Calculate statistics
        stats = calculate_vital_signs_stats(vital_signs)
        
        result = {
            'patientId': patient_id,
            'vitalSigns': convert_decimals(vital_signs),
            'patientInfo': patient_info,
            'timeRange': {
                'startTime': start_time,
                'endTime': end_time
            },
            'statistics': stats,
            'count': len(vital_signs)
        }
        
        return create_success_response(result)
        
    except Exception as e:
        print(f"Error getting vital signs range: {str(e)}")
        return create_error_response(500, f"Error retrieving vital signs: {str(e)}")

def get_all_recent_vital_signs(time_range, limit):
    """Get recent vital signs for all patients"""
    
    try:
        # Calculate time threshold
        end_time = datetime.utcnow()
        
        if time_range == '1h':
            start_time = end_time - timedelta(hours=1)
        elif time_range == '6h':
            start_time = end_time - timedelta(hours=6)
        elif time_range == '24h':
            start_time = end_time - timedelta(hours=24)
        else:
            start_time = end_time - timedelta(hours=1)
        
        start_time_str = start_time.isoformat() + 'Z'
        
        # Use GSI to query by timestamp
        response = vital_signs_table.query(
            IndexName='TimestampIndex',
            KeyConditionExpression=Key('Timestamp').gte(start_time_str),
            ScanIndexForward=False,
            Limit=limit
        )
        
        vital_signs = response.get('Items', [])
        
        # Group by patient ID and get latest for each
        patients_vital_signs = {}
        for record in vital_signs:
            patient_id = record['PatientId']
            if patient_id not in patients_vital_signs:
                patients_vital_signs[patient_id] = []
            patients_vital_signs[patient_id].append(record)
        
        # Get latest vital signs for each patient
        result_data = []
        for patient_id, records in patients_vital_signs.items():
            # Sort by timestamp and get latest
            latest_record = max(records, key=lambda x: x['Timestamp'])
            
            # Get patient info
            patient_info = get_patient_info(patient_id)
            
            result_data.append({
                'patientId': patient_id,
                'latestVitalSigns': convert_decimals(latest_record),
                'patientInfo': patient_info,
                'recordCount': len(records)
            })
        
        result = {
            'timeRange': time_range,
            'patients': result_data,
            'totalRecords': len(vital_signs),
            'totalPatients': len(patients_vital_signs)
        }
        
        return create_success_response(result)
        
    except Exception as e:
        print(f"Error getting all recent vital signs: {str(e)}")
        return create_error_response(500, f"Error retrieving vital signs: {str(e)}")

def get_patient_info(patient_id):
    """Get basic patient information"""
    
    try:
        response = patient_table.get_item(
            Key={'PatientId': patient_id}
        )
        
        if 'Item' in response:
            patient = response['Item']
            return {
                'name': patient.get('Name', 'Unknown'),
                'age': int(patient.get('Age', 0)),
                'gender': patient.get('Gender', 'Unknown'),
                'roomNumber': patient.get('RoomNumber', 'Unknown'),
                'condition': patient.get('Condition', 'Unknown'),
                'status': patient.get('Status', 'Unknown')
            }
        else:
            return {
                'name': 'Unknown Patient',
                'age': 0,
                'gender': 'Unknown',
                'roomNumber': 'Unknown',
                'condition': 'Unknown',
                'status': 'Unknown'
            }
            
    except Exception as e:
        print(f"Error getting patient info for {patient_id}: {str(e)}")
        return {
            'name': 'Unknown Patient',
            'age': 0,
            'gender': 'Unknown',
            'roomNumber': 'Unknown',
            'condition': 'Unknown',
            'status': 'Unknown'
        }

def calculate_vital_signs_stats(vital_signs):
    """Calculate statistics for vital signs data"""
    
    if not vital_signs:
        return {}
    
    try:
        # Extract values for calculation
        heart_rates = [float(vs.get('HeartRate', 0)) for vs in vital_signs if vs.get('HeartRate')]
        systolic_bps = [float(vs.get('SystolicBP', 0)) for vs in vital_signs if vs.get('SystolicBP')]
        diastolic_bps = [float(vs.get('DiastolicBP', 0)) for vs in vital_signs if vs.get('DiastolicBP')]
        temperatures = [float(vs.get('Temperature', 0)) for vs in vital_signs if vs.get('Temperature')]
        oxygen_sats = [float(vs.get('OxygenSaturation', 0)) for vs in vital_signs if vs.get('OxygenSaturation')]
        
        stats = {}
        
        if heart_rates:
            stats['heartRate'] = {
                'min': min(heart_rates),
                'max': max(heart_rates),
                'avg': round(sum(heart_rates) / len(heart_rates), 1)
            }
        
        if systolic_bps:
            stats['systolicBP'] = {
                'min': min(systolic_bps),
                'max': max(systolic_bps),
                'avg': round(sum(systolic_bps) / len(systolic_bps), 1)
            }
        
        if diastolic_bps:
            stats['diastolicBP'] = {
                'min': min(diastolic_bps),
                'max': max(diastolic_bps),
                'avg': round(sum(diastolic_bps) / len(diastolic_bps), 1)
            }
        
        if temperatures:
            stats['temperature'] = {
                'min': min(temperatures),
                'max': max(temperatures),
                'avg': round(sum(temperatures) / len(temperatures), 1)
            }
        
        if oxygen_sats:
            stats['oxygenSaturation'] = {
                'min': min(oxygen_sats),
                'max': max(oxygen_sats),
                'avg': round(sum(oxygen_sats) / len(oxygen_sats), 1)
            }
        
        return stats
        
    except Exception as e:
        print(f"Error calculating stats: {str(e)}")
        return {}

def convert_decimals(obj):
    """Convert DynamoDB Decimal objects to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def create_success_response(data, status_code=200):
    """Create a successful API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(data, default=str)
    }

def create_error_response(status_code, message):
    """Create an error API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps({
            'error': message,
            'statusCode': status_code
        })
    }