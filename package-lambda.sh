#!/bin/bash
# package-lambda.sh - Package and upload Lambda functions for Patient Vital Signs Monitoring

set -e

# Configuration
PROJECT_NAME="VitalSignsMonitoring"
LAMBDA_CODE_BUCKET="vital-signs-lambda-code"
REGION="us-east-1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Packaging Lambda functions for $PROJECT_NAME...${NC}"

# Create temporary directory for packaging
TMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TMP_DIR"

# Function to package Lambda function
package_lambda() {
    local function_name=$1
    local source_dir=$2
    
    echo -e "${YELLOW}📦 Packaging ${function_name}...${NC}"
    
    # Create function directory
    func_dir="$TMP_DIR/$function_name"
    mkdir -p "$func_dir"
    
    # Copy function code
    cp -r "$source_dir"/* "$func_dir/"
    
    # Install dependencies if requirements.txt exists
    if [ -f "$func_dir/requirements.txt" ]; then
        echo "Installing dependencies for $function_name..."
        pip install -r "$func_dir/requirements.txt" -t "$func_dir/" --quiet
    fi
    
    # Create zip file
    cd "$func_dir"
    zip -r "../${function_name}.zip" . -q
    cd - > /dev/null
    
    # Upload to S3
    echo "Uploading $function_name.zip to S3..."
    aws s3 cp "$TMP_DIR/${function_name}.zip" "s3://$LAMBDA_CODE_BUCKET/${function_name}.zip" --region $REGION
    
    echo -e "${GREEN}✅ ${function_name} packaged and uploaded${NC}"
}

# Package each Lambda function
package_lambda "iot-simulator" "lambda/iot-simulator"
package_lambda "vitals-processor" "lambda/vitals-processor"
package_lambda "patient-management" "lambda/patient-management"
package_lambda "vitals-api" "lambda/vitals-api"
package_lambda "alert-management" "lambda/alert-management"

# Cleanup
rm -rf "$TMP_DIR"

echo -e "${GREEN}🎉 All Lambda functions packaged and uploaded successfully!${NC}"