#!/usr/bin/env python3
"""
Deploy Private Company Extractor Lambda Function

This script:
1. Creates/updates IAM role for Lambda
2. Packages code and dependencies
3. Creates/updates Lambda function
4. Configures environment variables and settings
"""

import boto3
import json
import os
import zipfile
import time
from pathlib import Path
import subprocess
import sys

def get_account_id(session):
    """Get AWS account ID"""
    sts_client = session.client('sts', region_name='us-east-1')
    return sts_client.get_caller_identity()['Account']

def create_or_update_iam_role(iam_client, role_name):
    """Create or update IAM role for Lambda"""
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
        # Try to create role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Lambda role for Private Company Data Extractor'
        )
        print(f"✅ Created IAM role: {role_name}")
        role_arn = response['Role']['Arn']
        
        # Wait for role to be available
        time.sleep(10)
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"ℹ️  IAM role already exists: {role_name}")
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
    
    # Attach policies
    policies = [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',  # CloudWatch Logs
        'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess',  # DynamoDB access
        'arn:aws:iam::aws:policy/AmazonBedrockFullAccess'  # Bedrock access
    ]
    
    for policy_arn in policies:
        try:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"✅ Attached policy: {policy_arn.split('/')[-1]}")
        except Exception as e:
            print(f"ℹ️  Policy already attached or error: {policy_arn.split('/')[-1]}")
    
    return role_arn

def create_deployment_package():
    """Create Lambda deployment package"""
    print("\n📦 Creating deployment package...")
    
    # Paths
    lambda_dir = Path(__file__).parent
    project_root = lambda_dir.parent
    package_dir = lambda_dir / 'package_private'
    zip_path = lambda_dir / 'lambda_private_company_deployment.zip'
    
    # Clean up old package directory and zip
    if package_dir.exists():
        import shutil
        shutil.rmtree(package_dir)
    if zip_path.exists():
        zip_path.unlink()
    
    # Create package directory
    package_dir.mkdir(exist_ok=True)
    
    # Install dependencies
    print("   Installing dependencies...")
    subprocess.run([
        sys.executable, '-m', 'pip', 'install',
        'boto3', 'requests', 'python-dotenv', 'beautifulsoup4', 'lxml',
        '-t', str(package_dir),
        '--quiet'
    ], check=True)
    
    # Copy Lambda handler
    print("   Copying Lambda handler...")
    import shutil
    shutil.copy2(
        lambda_dir / 'lambda_private_company_handler.py',
        package_dir / 'lambda_private_company_handler.py'
    )
    
    # Copy private company extractor
    print("   Copying private company extractor...")
    shutil.copy2(
        project_root / 'private_company_extractor.py',
        package_dir / 'private_company_extractor.py'
    )
    
    # Create zip file
    print("   Creating ZIP archive...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    # Clean up package directory
    shutil.rmtree(package_dir)
    
    zip_size = zip_path.stat().st_size / (1024 * 1024)  # MB
    print(f"✅ Deployment package created: {zip_path.name} ({zip_size:.2f} MB)")
    
    return zip_path

def create_or_update_lambda_function(lambda_client, function_name, role_arn, zip_path):
    """Create or update Lambda function"""
    
    # Read deployment package
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Function configuration
    config = {
        'FunctionName': function_name,
        'Runtime': 'python3.11',
        'Role': role_arn,
        'Handler': 'lambda_private_company_handler.lambda_handler',
        'Timeout': 300,  # 5 minutes
        'MemorySize': 512,  # 512 MB
        'Environment': {
            'Variables': {
                'SERPER_API_KEY': os.getenv('SERPER_API_KEY', ''),
            }
        },
        'Description': 'Private Company Data Extractor using Nova Pro AI'
    }
    
    try:
        # Try to create function
        print(f"\n🚀 Creating Lambda function: {function_name}")
        response = lambda_client.create_function(
            **config,
            Code={'ZipFile': zip_content}
        )
        print(f"✅ Lambda function created: {function_name}")
        
    except lambda_client.exceptions.ResourceConflictException:
        print(f"ℹ️  Lambda function already exists: {function_name}")
        print(f"   Updating function code...")
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # Wait for update to complete
        print("   Waiting for code update to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=function_name)
        
        # Update function configuration
        print("   Updating function configuration...")
        config_update = {k: v for k, v in config.items() if k != 'Code'}
        response = lambda_client.update_function_configuration(**config_update)
        
        print(f"✅ Lambda function updated: {function_name}")
    
    return response

def main():
    """Main deployment function"""
    print("="*80)
    print("🚀 DEPLOYING PRIVATE COMPANY EXTRACTOR LAMBDA FUNCTION")
    print("="*80)
    print()
    
    # Initialize AWS clients with diligent profile
    try:
        session = boto3.Session(profile_name='diligent')
        iam_client = session.client('iam', region_name='us-east-1')
        lambda_client = session.client('lambda', region_name='us-east-1')
        
        account_id = get_account_id(session)
        print(f"✅ Connected to AWS Account: {account_id}")
        print(f"   Profile: diligent")
        print(f"   Region: us-east-1")
        print()
        
    except Exception as e:
        print(f"❌ Error connecting to AWS: {e}")
        return
    
    # Configuration
    role_name = 'LambdaPrivateCompanyExtractionRole'
    function_name = 'PrivateCompanyExtractor'
    
    # Step 1: Create/update IAM role
    print("📋 Step 1: Setting up IAM role...")
    print("-" * 80)
    role_arn = create_or_update_iam_role(iam_client, role_name)
    print(f"   Role ARN: {role_arn}")
    print()
    
    # Step 2: Create deployment package
    print("📦 Step 2: Creating deployment package...")
    print("-" * 80)
    zip_path = create_deployment_package()
    print()
    
    # Step 3: Create/update Lambda function
    print("🚀 Step 3: Deploying Lambda function...")
    print("-" * 80)
    response = create_or_update_lambda_function(lambda_client, function_name, role_arn, zip_path)
    
    # Summary
    print()
    print("="*80)
    print("✅ DEPLOYMENT COMPLETE")
    print("="*80)
    print()
    print(f"Function Name: {function_name}")
    print(f"Function ARN: {response['FunctionArn']}")
    print(f"Runtime: {response['Runtime']}")
    print(f"Handler: {response['Handler']}")
    print(f"Memory: {response['MemorySize']} MB")
    print(f"Timeout: {response['Timeout']} seconds")
    print()
    print("Environment Variables:")
    print(f"   SERPER_API_KEY: {'✅ Set' if os.getenv('SERPER_API_KEY') else '❌ Not Set'}")
    print()
    print("Next Steps:")
    print("1. Test the Lambda function")
    print(f"2. aws lambda invoke --function-name {function_name} \\")
    print('      --payload \'{"company_name": "SpaceX"}\' \\')
    print('      response.json')
    print()

if __name__ == "__main__":
    main()

