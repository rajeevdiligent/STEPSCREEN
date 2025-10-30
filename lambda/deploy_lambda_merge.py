#!/usr/bin/env python3
"""
Script to deploy DynamoDB to S3 Merger as AWS Lambda function
"""

import boto3
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

# Configuration
LAMBDA_FUNCTION_NAME = "DynamoDBToS3Merger"
LAMBDA_RUNTIME = "python3.11"
LAMBDA_TIMEOUT = 300  # 5 minutes (sufficient for merge operations)
LAMBDA_MEMORY = 512  # MB (merge is memory-light)
AWS_PROFILE = "diligent"
AWS_REGION = "us-east-1"

def create_deployment_package():
    """Create Lambda deployment package"""
    print("=" * 70)
    print("Creating Lambda Deployment Package")
    print("=" * 70)
    
    # Create temporary directory for packaging
    package_dir = Path("lambda_merge_package")
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    print("\n1. Copying application files...")
    # Copy Lambda handler (no external dependencies needed - boto3 is built-in)
    shutil.copy2("lambda_merge_handler.py", package_dir / "lambda_handler.py")
    print("   ✅ Application files copied")
    
    print("\n2. Creating deployment package...")
    zip_path = Path("lambda_merge_deployment.zip")
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    # Clean up
    shutil.rmtree(package_dir)
    
    size_kb = zip_path.stat().st_size / 1024
    print(f"   ✅ Deployment package created: {zip_path} ({size_kb:.2f} KB)")
    
    return zip_path


def get_or_create_lambda_role(iam_client):
    """Get or create IAM role for Lambda"""
    role_name = f"{LAMBDA_FUNCTION_NAME}Role"
    
    print(f"\n3. Setting up IAM role: {role_name}...")
    
    # Trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Try to get existing role
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"   ℹ️  Using existing role: {role_arn}")
    except iam_client.exceptions.NoSuchEntityException:
        # Create new role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for {LAMBDA_FUNCTION_NAME} Lambda function"
        )
        role_arn = response['Role']['Arn']
        print(f"   ✅ Created new role: {role_arn}")
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        # Attach policies for DynamoDB and S3
        policies = [
            "arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess",
            "arn:aws:iam::aws:policy/AmazonS3FullAccess"
        ]
        
        for policy_arn in policies:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        
        print("   ✅ Attached required policies (DynamoDB Read, S3 Write)")
        
        # Wait for role to be available
        import time
        print("   ⏳ Waiting for role to be ready...")
        time.sleep(10)
    
    return role_arn


def deploy_lambda_function(lambda_client, iam_client, zip_path):
    """Deploy or update Lambda function"""
    
    print("\n4. Deploying Lambda function...")
    
    # Get role ARN
    role_arn = get_or_create_lambda_role(iam_client)
    
    # Read deployment package
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Environment variables (minimal - no API keys needed)
    environment = {
        'Variables': {
            'PYTHONPATH': '/var/task'
        }
    }
    
    try:
        # Try to update existing function
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_content
        )
        print(f"   ✅ Updated existing Lambda function")
        
        # Wait for function code update to complete
        print(f"   ⏳ Waiting for code update to complete...")
        waiter = lambda_client.get_waiter('function_updated_v2')
        waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME, WaiterConfig={'MaxAttempts': 60, 'Delay': 2})
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=LAMBDA_RUNTIME,
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Environment=environment
        )
        print(f"   ✅ Updated function configuration")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=LAMBDA_RUNTIME,
            Role=role_arn,
            Handler="lambda_handler.lambda_handler",
            Code={'ZipFile': zip_content},
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Environment=environment,
            Description="DynamoDB to S3 Merger - Merges SEC and CXO data from DynamoDB and saves to S3"
        )
        print(f"   ✅ Created new Lambda function")
    
    function_arn = response['FunctionArn']
    print(f"   📍 Function ARN: {function_arn}")
    
    return function_arn


def main():
    """Main deployment function"""
    
    print("\n" + "=" * 70)
    print("AWS Lambda Deployment - DynamoDB to S3 Merger")
    print("=" * 70)
    
    # Initialize AWS clients
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    lambda_client = session.client('lambda')
    iam_client = session.client('iam')
    
    try:
        # Step 1-2: Create deployment package
        zip_path = create_deployment_package()
        
        # Step 3-4: Deploy Lambda function
        function_arn = deploy_lambda_function(lambda_client, iam_client, zip_path)
        
        print("\n" + "=" * 70)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 70)
        print(f"\n📋 Lambda Function: {LAMBDA_FUNCTION_NAME}")
        print(f"📍 ARN: {function_arn}")
        print(f"🌍 Region: {AWS_REGION}")
        print(f"⏱️  Timeout: {LAMBDA_TIMEOUT}s")
        print(f"💾 Memory: {LAMBDA_MEMORY}MB")
        print(f"\n📖 Invocation Example:")
        print(f'   aws lambda invoke --function-name {LAMBDA_FUNCTION_NAME} \\')
        print(f'     --payload \'{{"s3_bucket_name": "company-sec-cxo-data-diligent"}}\' \\')
        print(f'     --profile {AWS_PROFILE} response.json')
        print("\n💡 This Lambda merges data from DynamoDB tables:")
        print("   - CompanySECData (SEC filings)")
        print("   - CompanyCXOData (Executive data)")
        print("   And saves merged results to S3 bucket")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

