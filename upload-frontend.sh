#!/bin/bash
# upload-frontend.sh - Upload frontend files to S3 for Patient Vital Signs Monitoring

set -e

# Configuration
PROJECT_NAME="VitalSignsMonitoring"
REGION="us-east-1"
STACK_NAME_PREFIX="vital-signs"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 Uploading frontend for $PROJECT_NAME...${NC}"

# Get bucket name from CloudFormation stack
S3_BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text)

if [ -z "$S3_BUCKET_NAME" ]; then
    echo -e "${RED}❌ Could not retrieve S3 bucket name from stack${NC}"
    exit 1
fi

echo "S3 Bucket: $S3_BUCKET_NAME"

# Get API Gateway URL from CloudFormation stack
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

if [ -z "$API_URL" ]; then
    echo -e "${RED}❌ Could not retrieve API Gateway URL from stack${NC}"
    exit 1
fi

echo "API Gateway URL: $API_URL"

# Create config.js with API endpoint
echo -e "${YELLOW}📝 Creating frontend configuration...${NC}"
cat > frontend/src/js/config.js << EOF
// Configuration for Patient Vital Signs Monitoring System
const CONFIG = {
    API_BASE_URL: '$API_URL',
    PROJECT_NAME: '$PROJECT_NAME',
    REGION: '$REGION',
    
    // API Endpoints
    ENDPOINTS: {
        PATIENTS: '/patients',
        VITAL_SIGNS: '/vitalsigns',
        ALERTS: '/alerts'
    },
    
    // Vital Signs Thresholds
    VITAL_THRESHOLDS: {
        HEART_RATE: { min: 60, max: 100 },
        SYSTOLIC_BP: { min: 90, max: 140 },
        DIASTOLIC_BP: { min: 60, max: 90 },
        TEMPERATURE: { min: 97.0, max: 99.5 },
        OXYGEN_SAT: { min: 95, max: 100 }
    },
    
    // Chart Configuration
    CHART_CONFIG: {
        UPDATE_INTERVAL: 30000, // 30 seconds
        MAX_DATA_POINTS: 50,
        COLORS: {
            NORMAL: '#28a745',
            WARNING: '#ffc107',
            CRITICAL: '#dc3545'
        }
    }
};

// Make CONFIG available globally
window.HEALTHCARE_CONFIG = CONFIG;
EOF

# Upload all frontend files to S3
echo -e "${YELLOW}📤 Uploading frontend files to S3...${NC}"

# Upload HTML files
aws s3 cp frontend/public/index.html "s3://$S3_BUCKET_NAME/" --region $REGION --content-type "text/html"

# Upload CSS files
aws s3 cp frontend/src/css/ "s3://$S3_BUCKET_NAME/css/" --recursive --region $REGION --content-type "text/css"

# Upload JavaScript files
aws s3 cp frontend/src/js/ "s3://$S3_BUCKET_NAME/js/" --recursive --region $REGION --content-type "application/javascript"

# Upload assets
if [ -d "frontend/src/assets" ]; then
    aws s3 cp frontend/src/assets/ "s3://$S3_BUCKET_NAME/assets/" --recursive --region $REGION
fi

# Set bucket policy for website hosting (if not already set)
echo -e "${YELLOW}🔧 Configuring S3 bucket for website hosting...${NC}"

# The bucket policy should already be set by CloudFormation, but let's verify
aws s3api put-bucket-website \
  --bucket "$S3_BUCKET_NAME" \
  --website-configuration '{
    "IndexDocument": {"Suffix": "index.html"},
    "ErrorDocument": {"Key": "error.html"}
  }' \
  --region $REGION

echo -e "${GREEN}✅ Frontend uploaded successfully!${NC}"
echo -e "${BLUE}🌐 Website URL: http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com${NC}"

# Test if the website is accessible
echo -e "${YELLOW}🧪 Testing website accessibility...${NC}"
WEBSITE_URL="http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com"

# Wait a moment for S3 to update
sleep 5

if curl -s --head "$WEBSITE_URL" | head -n 1 | grep -q "200 OK"; then
    echo -e "${GREEN}✅ Website is accessible!${NC}"
else
    echo -e "${YELLOW}⚠️  Website may take a few minutes to become available${NC}"
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 Frontend deployment completed!${NC}"
echo -e "${BLUE}================================================${NC}"