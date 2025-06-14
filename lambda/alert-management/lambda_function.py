# lambda/alert-management/lambda_function.py - FIXED VERSION
import json
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
import os
from boto3.dynamodb.conditions import Key, Attr

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables
ALERT_HISTORY_TABLE = os.environ['ALERT_HISTORY_TABLE']
ALERT_CONFIG_TABLE = os.environ['ALERT_CONFIG_TABLE']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

# Get DynamoDB tables
alert_history_table = dynamodb.Table(ALERT_HISTORY_TABLE)
alert_config_table = dynamodb.Table(ALERT_CONFIG_TABLE)

def lambda_handler(event, context):
    """
    Handle alert management API requests
    """
    
    try:
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Parse the API Gateway event
        http_method = event['httpMethod']
        path = event['path']
        query_params = event.get('queryStringParameters') or {}
        
        print(f"HTTP Method: {http_method}, Path: {path}")
        
        # Extract alert ID from path if present
        alert_id = None
        if '/alerts/' in path:
            path_parts = path.split('/')
            print(f"Path parts: {path_parts}")
            if len(path_parts) >= 3:
                alert_id = path_parts[2]
                print(f"Extracted alert ID: {alert_id}")
        
        # Route based on HTTP method
        if http_method == 'GET':
            return handle_get_alerts(query_params)
        elif http_method == 'PUT' and alert_id:
            if 'acknowledge' in path:
                return acknowledge_alert(alert_id)
            else:
                return update_alert_config(alert_id, json.loads(event['body']))
        elif http_method == 'POST':
            return create_alert_config(json.loads(event['body']))
        elif http_method == 'DELETE' and alert_id:
            return delete_alert_config(alert_id)
        else:
            return create_error_response(405, f"Method {http_method} not allowed")
            
    except Exception as e:
        print(f"Error handling alert request: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")

def acknowledge_alert(alert_id):
    """Acknowledge an alert - FIXED VERSION"""
    
    try:
        print(f"Attempting to acknowledge alert: {alert_id}")
        
        # First, scan to find the alert by AlertId since we need both AlertId and Timestamp
        response = alert_history_table.scan(
            FilterExpression=Attr('AlertId').eq(alert_id)
        )
        
        print(f"Scan response: {response}")
        
        if not response.get('Items'):
            print(f"Alert {alert_id} not found in scan results")
            return create_error_response(404, f"Alert {alert_id} not found")
        
        alert_item = response['Items'][0]  # Get the first matching item
        print(f"Found alert item: {json.dumps(alert_item, default=str)}")
        
        # Check if already acknowledged
        if alert_item.get('Status') == 'ACKNOWLEDGED':
            return create_success_response({
                'message': f"Alert {alert_id} was already acknowledged",
                'alertId': alert_id,
                'status': 'ACKNOWLEDGED',
                'acknowledgedAt': alert_item.get('AcknowledgedAt')
            })
        
        # Update alert status to acknowledged using both keys
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        update_response = alert_history_table.update_item(
            Key={
                'AlertId': alert_id,
                'Timestamp': alert_item['Timestamp']
            },
            UpdateExpression="SET #status = :status, AcknowledgedAt = :ack_time",
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'ACKNOWLEDGED',
                ':ack_time': current_time
            },
            ReturnValues='ALL_NEW'
        )
        
        print(f"Update response: {json.dumps(update_response, default=str)}")
        
        return create_success_response({
            'message': f"Alert {alert_id} acknowledged successfully",
            'alertId': alert_id,
            'status': 'ACKNOWLEDGED',
            'acknowledgedAt': current_time,
            'updatedItem': convert_decimals(update_response['Attributes'])
        })
        
    except Exception as e:
        print(f"Error acknowledging alert {alert_id}: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return create_error_response(500, f"Error acknowledging alert: {str(e)}")

def handle_get_alerts(query_params):
    """Handle GET requests for alerts"""
    
    patient_id = query_params.get('patientId')
    hours = int(query_params.get('hours', '24'))
    limit = int(query_params.get('limit', '50'))
    alert_type = query_params.get('type')
    status = query_params.get('status')
    
    try:
        if patient_id:
            return get_patient_alerts(patient_id, hours, limit, alert_type, status)
        else:
            return get_all_alerts(hours, limit, alert_type, status)
            
    except Exception as e:
        print(f"Error in handle_get_alerts: {str(e)}")
        return create_error_response(500, f"Error retrieving alerts: {str(e)}")

def get_all_alerts(hours, limit, alert_type=None, status=None):
    """Get all alerts within specified time range"""
    
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        time_threshold_str = time_threshold.isoformat() + 'Z'
        
        # Build filter expression
        filter_expression = Attr('Timestamp').gte(time_threshold_str)
        
        if alert_type:
            filter_expression = filter_expression & Attr('AlertType').eq(alert_type)
        
        if status:
            filter_expression = filter_expression & Attr('Status').eq(status)
        
        # Scan the alert history table with filters
        response = alert_history_table.scan(
            FilterExpression=filter_expression,
            Limit=limit
        )
        
        alerts = response.get('Items', [])
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x['Timestamp'], reverse=True)
        
        # Get alert statistics
        stats = calculate_alert_stats(alerts)
        
        result = {
            'alerts': convert_decimals(alerts),
            'statistics': stats,
            'timeRange': f"Last {hours} hours",
            'count': len(alerts)
        }
        
        return create_success_response(result)
        
    except Exception as e:
        print(f"Error getting all alerts: {str(e)}")
        return create_error_response(500, f"Error retrieving alerts: {str(e)}")

def get_patient_alerts(patient_id, hours, limit, alert_type=None, status=None):
    """Get alerts for a specific patient"""
    
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        time_threshold_str = time_threshold.isoformat() + 'Z'
        
        # Query using GSI on PatientId
        key_condition = Key('PatientId').eq(patient_id) & Key('Timestamp').gte(time_threshold_str)
        
        response = alert_history_table.query(
            IndexName='PatientAlertIndex',
            KeyConditionExpression=key_condition,
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        alerts = response.get('Items', [])
        
        # Apply additional filters if specified
        if alert_type:
            alerts = [alert for alert in alerts if alert.get('AlertType') == alert_type]
        
        if status:
            alerts = [alert for alert in alerts if alert.get('Status') == status]
        
        # Get alert statistics for this patient
        stats = calculate_alert_stats(alerts)
        
        result = {
            'patientId': patient_id,
            'alerts': convert_decimals(alerts),
            'statistics': stats,
            'timeRange': f"Last {hours} hours",
            'count': len(alerts)
        }
        
        return create_success_response(result)
        
    except Exception as e:
        print(f"Error getting patient alerts: {str(e)}")
        return create_error_response(500, f"Error retrieving patient alerts: {str(e)}")

def create_alert_config(config_data):
    """Create a new alert configuration"""
    
    try:
        # Validate required fields
        required_fields = ['PatientId', 'VitalType']
        for field in required_fields:
            if field not in config_data:
                return create_error_response(400, f"Missing required field: {field}")
        
        # Prepare config item
        config_item = {
            'PatientId': config_data['PatientId'],
            'VitalType': config_data['VitalType'],
            'AlertEnabled': config_data.get('AlertEnabled', True),
            'CreatedAt': datetime.utcnow().isoformat() + 'Z',
            'UpdatedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add thresholds if provided
        if 'ThresholdMin' in config_data:
            config_item['ThresholdMin'] = Decimal(str(config_data['ThresholdMin']))
        
        if 'ThresholdMax' in config_data:
            config_item['ThresholdMax'] = Decimal(str(config_data['ThresholdMax']))
        
        # Store configuration
        alert_config_table.put_item(Item=config_item)
        
        return create_success_response({
            'message': 'Alert configuration created successfully',
            'configuration': convert_decimals(config_item)
        }, 201)
        
    except Exception as e:
        print(f"Error creating alert config: {str(e)}")
        return create_error_response(500, f"Error creating alert configuration: {str(e)}")

def update_alert_config(config_id, update_data):
    """Update an existing alert configuration"""
    
    try:
        # For simplicity, assuming config_id is in format "PatientId-VitalType"
        parts = config_id.split('-', 1)
        if len(parts) != 2:
            return create_error_response(400, "Invalid configuration ID format")
        
        patient_id, vital_type = parts
        
        # Check if config exists
        response = alert_config_table.get_item(
            Key={
                'PatientId': patient_id,
                'VitalType': vital_type
            }
        )
        
        if 'Item' not in response:
            return create_error_response(404, f"Alert configuration {config_id} not found")
        
        # Build update expression
        update_expression = "SET UpdatedAt = :updated_at"
        expression_values = {
            ':updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add updateable fields
        if 'AlertEnabled' in update_data:
            update_expression += ", AlertEnabled = :enabled"
            expression_values[':enabled'] = update_data['AlertEnabled']
        
        if 'ThresholdMin' in update_data:
            update_expression += ", ThresholdMin = :min_threshold"
            expression_values[':min_threshold'] = Decimal(str(update_data['ThresholdMin']))
        
        if 'ThresholdMax' in update_data:
            update_expression += ", ThresholdMax = :max_threshold"
            expression_values[':max_threshold'] = Decimal(str(update_data['ThresholdMax']))
        
        # Update configuration
        response = alert_config_table.update_item(
            Key={
                'PatientId': patient_id,
                'VitalType': vital_type
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return create_success_response({
            'message': f"Alert configuration {config_id} updated successfully",
            'configuration': convert_decimals(response['Attributes'])
        })
        
    except Exception as e:
        print(f"Error updating alert config: {str(e)}")
        return create_error_response(500, f"Error updating alert configuration: {str(e)}")

def delete_alert_config(config_id):
    """Delete an alert configuration"""
    
    try:
        # Parse config ID
        parts = config_id.split('-', 1)
        if len(parts) != 2:
            return create_error_response(400, "Invalid configuration ID format")
        
        patient_id, vital_type = parts
        
        # Check if config exists
        response = alert_config_table.get_item(
            Key={
                'PatientId': patient_id,
                'VitalType': vital_type
            }
        )
        
        if 'Item' not in response:
            return create_error_response(404, f"Alert configuration {config_id} not found")
        
        # Delete configuration
        alert_config_table.delete_item(
            Key={
                'PatientId': patient_id,
                'VitalType': vital_type
            }
        )
        
        return create_success_response({
            'message': f"Alert configuration {config_id} deleted successfully"
        })
        
    except Exception as e:
        print(f"Error deleting alert config: {str(e)}")
        return create_error_response(500, f"Error deleting alert configuration: {str(e)}")

def calculate_alert_stats(alerts):
    """Calculate statistics for alerts"""
    
    if not alerts:
        return {
            'total': 0,
            'byType': {},
            'byStatus': {},
            'recentCritical': 0
        }
    
    try:
        stats = {
            'total': len(alerts),
            'byType': {},
            'byStatus': {},
            'recentCritical': 0
        }
        
        # Count by type and status
        for alert in alerts:
            alert_type = alert.get('AlertType', 'UNKNOWN')
            alert_status = alert.get('Status', 'UNKNOWN')
            
            # Count by type
            stats['byType'][alert_type] = stats['byType'].get(alert_type, 0) + 1
            
            # Count by status
            stats['byStatus'][alert_status] = stats['byStatus'].get(alert_status, 0) + 1
            
            # Count recent critical alerts (last hour)
            if alert_type == 'CRITICAL':
                alert_time = datetime.fromisoformat(alert['Timestamp'].replace('Z', '+00:00'))
                if alert_time > datetime.utcnow().replace(tzinfo=alert_time.tzinfo) - timedelta(hours=1):
                    stats['recentCritical'] += 1
        
        return stats
        
    except Exception as e:
        print(f"Error calculating alert stats: {str(e)}")
        return {
            'total': len(alerts),
            'byType': {},
            'byStatus': {},
            'recentCritical': 0
        }

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