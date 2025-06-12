#!/bin/bash
# deploy.sh - Script to deploy the Patient Vital Signs Monitoring System

set -e  # Exit immediately if a command exits with a non-zero status

# Disable AWS CLI pager to prevent interactive less
export AWS_PAGER=""

# Configuration
PROJECT_NAME="VitalSignsMonitoring"
REGION="us-east-1"  # Use the region that's available in your AWS Academy Lab
STACK_NAME_PREFIX="vital-signs"
LAMBDA_CODE_BUCKET="vital-signs-lambda-code"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🏥 Starting deployment of $PROJECT_NAME Healthcare System${NC}"
echo -e "${BLUE}================================================${NC}"

# 1. Deploy S3 resources
echo -e "${YELLOW}📦 Step 1/8: Deploying S3 resources...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/s3.yaml \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $REGION

# Get the S3 bucket name from the S3 stack
S3_BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ S3 resources deployed${NC}"
echo -e "   Website Bucket: $S3_BUCKET_NAME"

# 2. Deploy DynamoDB resources
echo -e "${YELLOW}📦 Step 2/8: Deploying DynamoDB tables...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/dynamodb.yaml \
  --stack-name "${STACK_NAME_PREFIX}-dynamodb" \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $REGION

echo -e "${GREEN}✅ DynamoDB tables deployed${NC}"

# 3. Deploy IoT Core resources
echo -e "${YELLOW}📦 Step 3/8: Deploying IoT Core resources...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/iot.yaml \
  --stack-name "${STACK_NAME_PREFIX}-iot" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    DynamoDBStackName="${STACK_NAME_PREFIX}-dynamodb" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

echo -e "${GREEN}✅ IoT Core resources deployed${NC}"

# 4. Create/check Lambda code bucket and upload Lambda code
echo -e "${YELLOW}📦 Step 4/8: Setting up Lambda code...${NC}"

# Check if the bucket exists
if aws s3api head-bucket --bucket $LAMBDA_CODE_BUCKET 2>/dev/null; then
  echo "Lambda code bucket already exists: $LAMBDA_CODE_BUCKET"
else
  echo "Creating Lambda code bucket: $LAMBDA_CODE_BUCKET"
  aws s3api create-bucket --bucket $LAMBDA_CODE_BUCKET --region $REGION
fi

# Package and upload Lambda code
echo -e "${YELLOW}🔧 Packaging Lambda functions...${NC}"
./package-lambda.sh

echo -e "${GREEN}✅ Lambda code packaged and uploaded${NC}"

# 5. Deploy Lambda functions
echo -e "${YELLOW}📦 Step 5/8: Deploying Lambda functions...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/lambda.yaml \
  --stack-name "${STACK_NAME_PREFIX}-lambda" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    S3StackName="${STACK_NAME_PREFIX}-s3" \
    DynamoDBStackName="${STACK_NAME_PREFIX}-dynamodb" \
    IoTStackName="${STACK_NAME_PREFIX}-iot" \
    LambdaCodeBucket=$LAMBDA_CODE_BUCKET \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

echo -e "${GREEN}✅ Lambda functions deployed${NC}"

# 6. Deploy API Gateway
echo -e "${YELLOW}📦 Step 6/8: Deploying API Gateway...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/api-gateway.yaml \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    LambdaStackName="${STACK_NAME_PREFIX}-lambda" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ API Gateway deployed${NC}"

# 7. Deploy CloudWatch Monitoring
echo -e "${YELLOW}📊 Step 7/8: Deploying CloudWatch monitoring...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/cloudwatch.yaml \
  --stack-name "${STACK_NAME_PREFIX}-monitoring" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    LambdaStackName="${STACK_NAME_PREFIX}-lambda" \
    ApiStackName="${STACK_NAME_PREFIX}-api" \
    DynamoDBStackName="${STACK_NAME_PREFIX}-dynamodb" \
    IoTStackName="${STACK_NAME_PREFIX}-iot" \
    CriticalVitalSignsThreshold=5 \
    HighLatencyThreshold=5000 \
    ErrorRateThreshold=10 \
  --region $REGION

# Get CloudWatch Dashboard URL
DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-monitoring" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardUrl'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ CloudWatch monitoring deployed${NC}"
echo -e "   Dashboard URL: $DASHBOARD_URL"

# 8. Deploy frontend with configuration
echo -e "${YELLOW}🌐 Step 8/8: Deploying frontend...${NC}"
./upload-frontend.sh

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo -e "${BLUE}================================================${NC}"

echo -e "${YELLOW}📋 Deployment Summary:${NC}"
echo -e "   🌐 Website URL: http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo -e "   🔗 API Gateway URL: $API_URL"
echo -e "   📊 CloudWatch Dashboard: $DASHBOARD_URL"

echo -e "${YELLOW}🏥 Healthcare System Features:${NC}"
echo -e "   ✅ Real-time patient vital signs monitoring"
echo -e "   ✅ IoT Core for sensor data ingestion"
echo -e "   ✅ Automated critical alert system via SNS"
echo -e "   ✅ Historical data analysis and trends"
echo -e "   ✅ CloudWatch monitoring and alarms"
echo -e "   ✅ Secure patient data storage with encryption"

echo -e "${YELLOW}📝 Next Steps:${NC}"
echo -e "   1. 🏥 Access the healthcare dashboard at: http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo -e "   2. 📊 View monitoring dashboard: $DASHBOARD_URL"
echo -e "   3. 🔬 Test IoT sensor simulation for patient vital signs"
echo -e "   4. 🚨 Verify alert system with critical vital signs thresholds"
echo -e "   5. 📈 Analyze historical patient data and trends"

echo -e "${RED}⚠️  IMPORTANT: This is a simulated healthcare system for educational purposes.${NC}"
echo -e "${RED}   Do not use with real patient data or in production healthcare environments.${NC}"