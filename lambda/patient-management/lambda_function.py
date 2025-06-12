# lambda/patient-management/lambda_function.py
import json
import boto3
from decimal import Decimal
from datetime import datetime
import os

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
PATIENT_RECORDS_TABLE = os.environ['PATIENT_RECORDS_TABLE']
ALERT_CONFIG_TABLE = os.environ['ALERT_CONFIG_TABLE']

# Get DynamoDB tables
patient_table = dynamodb.Table(PATIENT_RECORDS_TABLE)
alert_config_table = dynamodb.Table(ALERT_CONFIG_TABLE)

def lambda_handler(event, context):
    """
    Handle patient management API requests
    """
    
    try:
        # Parse the API Gateway event
        http_method = event['httpMethod']
        path = event['path']
        
        # Extract patient ID from path if present
        patient_id = None
        if '/patients/' in path:
            path_parts = path.split('/')
            if len(path_parts) >= 3:
                patient_id = path_parts[2]
        
        # Route based on HTTP method
        if http_method == 'GET':
            if patient_id:
                return get_patient(patient_id)
            else:
                return get_all_patients(event.get('queryStringParameters', {}))
                
        elif http_method == 'POST':
            return create_patient(json.loads(event['body']))
            
        elif http_method == 'PUT':
            if patient_id:
                return update_patient(patient_id, json.loads(event['body']))
            else:
                return create_error_response(400, "Patient ID required for update")
                
        elif http_method == 'DELETE':
            if patient_id:
                return delete_patient(patient_id)
            else:
                return create_error_response(400, "Patient ID required for delete")
                
        else:
            return create_error_response(405, f"Method {http_method} not allowed")
            
    except Exception as e:
        print(f"Error handling request: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")

def get_all_patients(query_params):
    """Get all patients with optional filtering"""
    
    try:
        # Check for room number filter
        room_number = query_params.get('room') if query_params else None
        
        if room_number:
            # Query by room number using GSI
            response = patient_table.query(
                IndexName='RoomIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('RoomNumber').eq(room_number)
            )
        else:
            # Scan all patients
            response = patient_table.scan()
        
        patients = response.get('Items', [])
        
        # Convert Decimal to float for JSON serialization
        patients = convert_decimals(patients)
        
        return create_success_response({
            'patients': patients,
            'count': len(patients)
        })
        
    except Exception as e:
        print(f"Error getting patients: {str(e)}")
        return create_error_response(500, f"Error retrieving patients: {str(e)}")

def get_patient(patient_id):
    """Get a specific patient by ID"""
    
    try:
        response = patient_table.get_item(
            Key={'PatientId': patient_id}
        )
        
        if 'Item' not in response:
            return create_error_response(404, f"Patient {patient_id} not found")
        
        patient = convert_decimals(response['Item'])
        
        # Also get alert configurations for this patient
        alert_configs = get_patient_alert_configs(patient_id)
        patient['alertConfigurations'] = alert_configs
        
        return create_success_response(patient)
        
    except Exception as e:
        print(f"Error getting patient {patient_id}: {str(e)}")
        return create_error_response(500, f"Error retrieving patient: {str(e)}")

def create_patient(patient_data):
    """Create a new patient record"""
    
    try:
        # Validate required fields
        required_fields = ['PatientId', 'Name', 'Age', 'Gender', 'RoomNumber']
        for field in required_fields:
            if field not in patient_data:
                return create_error_response(400, f"Missing required field: {field}")
        
        # Check if patient already exists
        existing_patient = patient_table.get_item(
            Key={'PatientId': patient_data['PatientId']}
        )
        
        if 'Item' in existing_patient:
            return create_error_response(409, f"Patient {patient_data['PatientId']} already exists")
        
        # Prepare patient item
        patient_item = {
            'PatientId': patient_data['PatientId'],
            'Name': patient_data['Name'],
            'Age': Decimal(str(patient_data['Age'])),
            'Gender': patient_data['Gender'],
            'RoomNumber': patient_data['RoomNumber'],
            'Status': patient_data.get('Status', 'Active'),
            'Condition': patient_data.get('Condition', 'Stable'),
            'AdmissionDate': patient_data.get('AdmissionDate', datetime.now().isoformat()),
            'EmergencyContact': patient_data.get('EmergencyContact', ''),
            'MedicalHistory': patient_data.get('MedicalHistory', ''),
            'Allergies': patient_data.get('Allergies', ''),
            'CurrentMedications': patient_data.get('CurrentMedications', []),
            'CreatedAt': datetime.now().isoformat(),
            'UpdatedAt': datetime.now().isoformat()
        }
        
        # Store patient
        patient_table.put_item(Item=patient_item)
        
        # Create default alert configurations
        create_default_alert_configs(patient_data['PatientId'])
        
        return create_success_response({
            'message': f"Patient {patient_data['PatientId']} created successfully",
            'patient': convert_decimals(patient_item)
        }, 201)
        
    except Exception as e:
        print(f"Error creating patient: {str(e)}")
        return create_error_response(500, f"Error creating patient: {str(e)}")

def update_patient(patient_id, update_data):
    """Update an existing patient record"""
    
    try:
        # Check if patient exists
        existing_patient = patient_table.get_item(
            Key={'PatientId': patient_id}
        )
        
        if 'Item' not in existing_patient:
            return create_error_response(404, f"Patient {patient_id} not found")
        
        # Prepare update expression
        update_expression = "SET UpdatedAt = :updated_at"
        expression_values = {
            ':updated_at': datetime.now().isoformat()
        }
        
        # Add fields to update
        updateable_fields = ['Name', 'Age', 'Gender', 'RoomNumber', 'Status', 'Condition', 
                           'EmergencyContact', 'MedicalHistory', 'Allergies', 'CurrentMedications']
        
        for field in updateable_fields:
            if field in update_data:
                field_key = f":{field.lower()}"
                update_expression += f", {field} = {field_key}"
                
                # Handle numeric fields
                if field == 'Age' and isinstance(update_data[field], (int, float)):
                    expression_values[field_key] = Decimal(str(update_data[field]))
                else:
                    expression_values[field_key] = update_data[field]
        
        # Update patient
        response = patient_table.update_item(
            Key={'PatientId': patient_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_patient = convert_decimals(response['Attributes'])
        
        return create_success_response({
            'message': f"Patient {patient_id} updated successfully",
            'patient': updated_patient
        })
        
    except Exception as e:
        print(f"Error updating patient {patient_id}: {str(e)}")
        return create_error_response(500, f"Error updating patient: {str(e)}")

def delete_patient(patient_id):
    """Delete a patient record"""
    
    try:
        # Check if patient exists
        existing_patient = patient_table.get_item(
            Key={'PatientId': patient_id}
        )
        
        if 'Item' not in existing_patient:
            return create_error_response(404, f"Patient {patient_id} not found")
        
        # Instead of actually deleting, mark as inactive
        patient_table.update_item(
            Key={'PatientId': patient_id},
            UpdateExpression="SET #status = :status, UpdatedAt = :updated_at",
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'Inactive',
                ':updated_at': datetime.now().isoformat()
            }
        )
        
        return create_success_response({
            'message': f"Patient {patient_id} marked as inactive"
        })
        
    except Exception as e:
        print(f"Error deleting patient {patient_id}: {str(e)}")
        return create_error_response(500, f"Error deleting patient: {str(e)}")

def get_patient_alert_configs(patient_id):
    """Get alert configurations for a patient"""
    
    try:
        response = alert_config_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('PatientId').eq(patient_id)
        )
        
        configs = response.get('Items', [])
        return convert_decimals(configs)
        
    except Exception as e:
        print(f"Error getting alert configs for {patient_id}: {str(e)}")
        return []

def create_default_alert_configs(patient_id):
    """Create default alert configurations for a new patient"""
    
    default_configs = [
        {
            'PatientId': patient_id,
            'VitalType': 'heart_rate',
            'ThresholdMin': Decimal('50'),
            'ThresholdMax': Decimal('120'),
            'AlertEnabled': True,
            'CreatedAt': datetime.now().isoformat()
        },
        {
            'PatientId': patient_id,
            'VitalType': 'systolic_bp',
            'ThresholdMin': Decimal('90'),
            'ThresholdMax': Decimal('180'),
            'AlertEnabled': True,
            'CreatedAt': datetime.now().isoformat()
        },
        {
            'PatientId': patient_id,
            'VitalType': 'diastolic_bp',
            'ThresholdMin': Decimal('50'),
            'ThresholdMax': Decimal('120'),
            'AlertEnabled': True,
            'CreatedAt': datetime.now().isoformat()
        },
        {
            'PatientId': patient_id,
            'VitalType': 'temperature',
            'ThresholdMin': Decimal('95.0'),
            'ThresholdMax': Decimal('101.5'),
            'AlertEnabled': True,
            'CreatedAt': datetime.now().isoformat()
        },
        {
            'PatientId': patient_id,
            'VitalType': 'oxygen_saturation',
            'ThresholdMin': Decimal('90'),
            'ThresholdMax': Decimal('100'),
            'AlertEnabled': True,
            'CreatedAt': datetime.now().isoformat()
        }
    ]
    
    for config in default_configs:
        try:
            alert_config_table.put_item(Item=config)
        except Exception as e:
            print(f"Error creating default alert config: {str(e)}")

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