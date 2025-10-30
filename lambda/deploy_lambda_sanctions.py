#!/usr/bin/env python3
"""
Deploy Sanctions Screening Lambda Function

This script packages and deploys the sanctions screening Lambda function to AWS.
"""

import os
import sys
import json
import time
import zipfile
import shutil
import tempfile
from pathlib import Path
import boto3
from botocore.exceptions import ClientError


def create_deployment_package():
    """Create a deployment package with all dependencies"""
    print("\n📦 Creating deployment package...")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    package_dir = Path(temp_dir) / "package"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"   Working directory: {package_dir}")
    
    # Get the current script's directory (lambda/)
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    
    # Copy main sanctions_screener.py from parent directory
    sanctions_screener_path = parent_dir / "sanctions_screener.py"
    if sanctions_screener_path.exists():
        shutil.copy2(sanctions_screener_path, package_dir / "sanctions_screener.py")
        print(f"   ✅ Copied sanctions_screener.py")
    else:
        print(f"   ❌ Error: sanctions_screener.py not found at {sanctions_screener_path}")
        sys.exit(1)
    
    # Copy Lambda handler
    handler_path = current_dir / "lambda_sanctions_handler.py"
    if handler_path.exists():
        shutil.copy2(handler_path, package_dir / "lambda_function.py")
        print(f"   ✅ Copied lambda handler as lambda_function.py")
    else:
        print(f"   ❌ Error: lambda_sanctions_handler.py not found")
        sys.exit(1)
    
    # Install dependencies from lambda_requirements.txt
    requirements_file = current_dir / "lambda_requirements.txt"
    if requirements_file.exists():
        print(f"   📥 Installing dependencies from lambda_requirements.txt...")
        os.system(f"pip install -r {requirements_file} -t {package_dir} --quiet")
        print(f"   ✅ Dependencies installed")
    else:
        print(f"   ⚠️  Warning: lambda_requirements.txt not found")
    
    # Create zip file
    zip_path = Path(temp_dir) / "lambda_package.zip"
    print(f"   🗜️  Creating ZIP archive...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    zip_size = zip_path.stat().st_size / (1024 * 1024)  # MB
    print(f"   ✅ Package created: {zip_size:.2f} MB")
    
    return str(zip_path)


def create_or_update_iam_role(iam_client, role_name):
    """Create or update IAM role for Lambda"""
    print(f"\n🔐 Setting up IAM role: {role_name}")
    
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Check if role exists
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"   ✅ Role already exists: {role_arn}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            # Create new role
            print(f"   🆕 Creating new role...")
            response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description='Lambda execution role for Sanctions Screening'
            )
            role_arn = response['Role']['Arn']
            print(f"   ✅ Role created: {role_arn}")
            
            # Wait for role to propagate
            print("   ⏳ Waiting for role to propagate...")
            time.sleep(10)
        else:
            raise
    
    # Attach required policies
    policies = [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess',
        'arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
    ]
    
    for policy_arn in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            policy_name = policy_arn.split('/')[-1]
            print(f"   ✅ Attached policy: {policy_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                pass
            else:
                raise
    
    return role_arn


def deploy_lambda_function(lambda_client, iam_client, zip_path, serper_api_key, aws_region):
    """Deploy Lambda function to AWS"""
    function_name = "SanctionsScreener"
    handler_name = "lambda_function.lambda_handler"
    runtime = "python3.11"
    memory = 512
    timeout = 900  # 15 minutes (sanctions screening can take time)
    
    role_name = "SanctionsScreenerLambdaRole"
    role_arn = create_or_update_iam_role(iam_client, role_name)
    
    print(f"\n🚀 Deploying Lambda function: {function_name}")
    
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    environment_variables = {
        'SERPER_API_KEY': serper_api_key,
    }
    
    try:
        # Try to create new function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role_arn,
            Handler=handler_name,
            Code={'ZipFile': zip_content},
            Description='Lambda function for Sanctions & Watchlist Screening',
            Timeout=timeout,
            MemorySize=memory,
            Publish=True,
            Environment={'Variables': environment_variables},
            Tags={'Project': 'CompanyDataExtraction', 'Module': 'SanctionsScreening'}
        )
        print("   ✅ Created new Lambda function")
        function_arn = response['FunctionArn']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print("   ℹ️  Function already exists, updating...")
            
            # Wait for any in-progress updates
            waiter = lambda_client.get_waiter('function_updated_v2')
            try:
                waiter.wait(FunctionName=function_name, WaiterConfig={'MaxAttempts': 60})
            except:
                pass
            
            # Update function code
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print("   ✅ Updated function code")
            
            # Wait for code update to complete
            print("   ⏳ Waiting for code update to complete...")
            time.sleep(5)
            waiter = lambda_client.get_waiter('function_updated_v2')
            try:
                waiter.wait(FunctionName=function_name, WaiterConfig={'MaxAttempts': 60, 'Delay': 2})
            except Exception as e:
                print(f"   ⚠️  Waiter warning: {e}")
                time.sleep(5)
            
            # Update function configuration
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Runtime=runtime,
                Role=role_arn,
                Handler=handler_name,
                Description='Lambda function for Sanctions & Watchlist Screening',
                Timeout=timeout,
                MemorySize=memory,
                Environment={'Variables': environment_variables}
            )
            print("   ✅ Updated function configuration")
            
            function_arn = lambda_client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']
        else:
            print(f"❌ Deployment failed: {e}")
            raise
    
    print(f"   Function ARN: {function_arn}")
    return function_arn


def test_lambda_function(lambda_client, function_name):
    """Test the deployed Lambda function"""
    print(f"\n🧪 Testing Lambda function: {function_name}")
    
    test_payload = {
        "company_name": "Tesla Inc"
    }
    
    print(f"   Test payload: {json.dumps(test_payload)}")
    print(f"   ⏳ Invoking Lambda (this may take 2-5 minutes)...")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        payload = json.loads(response['Payload'].read())
        status_code = payload.get('statusCode')
        
        if status_code == 200:
            body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
            print(f"\n   ✅ Lambda test SUCCESSFUL!")
            print(f"   Company: {body.get('company_name')}")
            print(f"   Entities Screened: {body.get('total_entities_screened')}")
            print(f"   Matches Found: {body.get('total_matches_found')}")
            if body.get('company_matches'):
                print(f"   Company Matches: {len(body.get('company_matches'))}")
            if body.get('executive_matches'):
                print(f"   Executive Matches: {len(body.get('executive_matches'))}")
        else:
            print(f"   ❌ Lambda test FAILED with status code: {status_code}")
            print(f"   Response: {json.dumps(payload, indent=2)}")
            
    except Exception as e:
        print(f"   ❌ Test invocation failed: {e}")


def main():
    """Main deployment function"""
    print("="*80)
    print("🛡️  Sanctions Screening Lambda Deployment")
    print("="*80)
    
    # Get configuration from environment
    aws_profile = os.getenv('AWS_PROFILE', 'diligent')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    serper_api_key = os.getenv('SERPER_API_KEY')
    
    if not serper_api_key:
        print("❌ Error: SERPER_API_KEY not found in environment variables")
        sys.exit(1)
    
    print(f"\n📋 Configuration:")
    print(f"   AWS Profile: {aws_profile}")
    print(f"   AWS Region: {aws_region}")
    print(f"   Serper API Key: {'*' * 20}{serper_api_key[-4:]}")
    
    # Initialize AWS clients
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    lambda_client = session.client('lambda')
    iam_client = session.client('iam')
    
    print(f"\n✅ Connected to AWS (Profile: {aws_profile}, Region: {aws_region})")
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    # Deploy Lambda function
    function_arn = deploy_lambda_function(
        lambda_client,
        iam_client,
        zip_path,
        serper_api_key,
        aws_region
    )
    
    # Test Lambda function
    print("\n" + "="*80)
    user_input = input("Would you like to test the Lambda function? (y/n): ")
    if user_input.lower() == 'y':
        test_lambda_function(lambda_client, "SanctionsScreener")
    
    # Clean up temp files
    print(f"\n🧹 Cleaning up temporary files...")
    temp_dir = Path(zip_path).parent
    shutil.rmtree(temp_dir)
    print(f"   ✅ Cleaned up")
    
    print("\n" + "="*80)
    print("✅ Deployment Complete!")
    print("="*80)
    print(f"\nFunction Name: SanctionsScreener")
    print(f"Function ARN: {function_arn}")
    print(f"Runtime: python3.11")
    print(f"Timeout: 15 minutes")
    print(f"Memory: 512 MB")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()

