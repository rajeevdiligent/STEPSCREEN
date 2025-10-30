#!/usr/bin/env python3
"""
Script to deploy Nova SEC Extractor as AWS Lambda function
"""

import boto3
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Configuration
LAMBDA_FUNCTION_NAME = "NovaSECExtractor"
LAMBDA_RUNTIME = "python3.11"
LAMBDA_TIMEOUT = 900  # 15 minutes (max for Lambda)
LAMBDA_MEMORY = 2048  # MB
AWS_PROFILE = "diligent"
AWS_REGION = "us-east-1"

def create_deployment_package():
    """Create Lambda deployment package"""
    print("=" * 70)
    print("Creating Lambda Deployment Package")
    print("=" * 70)
    
    # Create temporary directory for packaging
    package_dir = Path("lambda_package")
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    print("\n1. Installing dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "-r", "lambda_requirements.txt",
        "-t", str(package_dir),
        "--quiet"
    ], check=True)
    print("   ✅ Dependencies installed")
    
    print("\n2. Copying application files...")
    # Get script directory and parent directory
    script_dir = Path(__file__).parent
    parent_dir = script_dir.parent
    
    # Copy main extractor from parent directory
    shutil.copy2(parent_dir / "nova_sec_extractor.py", package_dir / "nova_sec_extractor.py")
    # Copy Lambda handler from current directory
    shutil.copy2(script_dir / "lambda_nova_sec_handler.py", package_dir / "lambda_handler.py")
    print("   ✅ Application files copied")
    
    print("\n3. Creating deployment package...")
    zip_path = Path("lambda_nova_sec_deployment.zip")
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
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Deployment package created: {zip_path} ({size_mb:.2f} MB)")
    
    return zip_path


def get_or_create_lambda_role(iam_client):
    """Get or create IAM role for Lambda"""
    role_name = f"{LAMBDA_FUNCTION_NAME}Role"
    
    print(f"\n4. Setting up IAM role: {role_name}...")
    
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
        
        # Attach policies for Bedrock, DynamoDB, and S3
        policies = [
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
        ]
        
        for policy_arn in policies:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        
        print("   ✅ Attached required policies")
        
        # Wait for role to be available
        import time
        print("   ⏳ Waiting for role to be ready...")
        time.sleep(10)
    
    return role_arn


def deploy_lambda_function(lambda_client, iam_client, zip_path):
    """Deploy or update Lambda function"""
    
    print("\n5. Deploying Lambda function...")
    
    # Get role ARN
    role_arn = get_or_create_lambda_role(iam_client)
    
    # Read deployment package
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Environment variables
    environment = {
        'Variables': {
            'AWS_PROFILE': AWS_PROFILE,
            'SERPER_API_KEY': os.getenv('SERPER_API_KEY', ''),
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
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=LAMBDA_RUNTIME,
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Environment=environment
        )
        
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
            Description="Nova Pro SEC Document Extractor - Extracts company information from SEC filings"
        )
        print(f"   ✅ Created new Lambda function")
    
    function_arn = response['FunctionArn']
    print(f"   📍 Function ARN: {function_arn}")
    
    return function_arn


def test_lambda_function(lambda_client):
    """Test the deployed Lambda function"""
    print("\n6. Testing Lambda function...")
    
    test_payload = {
        "company_name": "Intel Corporation",
        "stock_symbol": "INTC"
    }
    
    print(f"   📤 Invoking with test payload: {test_payload}")
    
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(test_payload)
    )
    
    result = json.loads(response['Payload'].read())
    
    if response['StatusCode'] == 200:
        print(f"   ✅ Lambda invocation successful")
        body = json.loads(result.get('body', '{}'))
        print(f"   📊 Extraction Status: {body.get('extraction_status')}")
        print(f"   📊 Completeness: {body.get('completeness')}%")
        print(f"   📊 Company: {body.get('company_name')}")
    else:
        print(f"   ⚠️  Lambda invocation returned status: {response['StatusCode']}")
        print(f"   Response: {result}")
    
    return result


def main():
    """Main deployment function"""
    
    print("\n" + "=" * 70)
    print("AWS Lambda Deployment - Nova SEC Extractor")
    print("=" * 70)
    
    # Initialize AWS clients
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    lambda_client = session.client('lambda')
    iam_client = session.client('iam')
    
    try:
        # Step 1-3: Create deployment package
        zip_path = create_deployment_package()
        
        # Step 4-5: Deploy Lambda function
        function_arn = deploy_lambda_function(lambda_client, iam_client, zip_path)
        
        # Step 6: Test (optional - comment out if you don't want automatic testing)
        # test_lambda_function(lambda_client)
        
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
        print(f'     --payload \'{{"company_name": "Apple Inc"}}\' \\')
        print(f'     --profile {AWS_PROFILE} response.json')
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

