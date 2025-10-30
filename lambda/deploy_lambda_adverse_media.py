#!/usr/bin/env python3
"""
Deploy Adverse Media Scanner Lambda Function

This script:
1. Packages the adverse media scanner with dependencies
2. Creates/updates the Lambda function
3. Configures environment variables and permissions
4. Tests the deployment
"""

import boto3
import zipfile
import os
import sys
import json
import time
from pathlib import Path

def create_deployment_package():
    """Create a deployment package with all dependencies"""
    
    print("=" * 80)
    print("Creating Adverse Media Scanner Lambda Deployment Package")
    print("=" * 80)
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Files to include in the package
    files_to_include = [
        'adverse_media_scanner.py',
    ]
    
    # Create deployment package
    zip_path = script_dir / 'lambda_adverse_media_deployment.zip'
    
    print(f"\n📦 Creating deployment package: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add the Lambda handler
        handler_path = script_dir / 'lambda_adverse_media_handler.py'
        zipf.write(handler_path, 'lambda_function.py')
        print(f"   ✅ Added: lambda_function.py (handler)")
        
        # Add the adverse media scanner
        for filename in files_to_include:
            file_path = project_root / filename
            if file_path.exists():
                zipf.write(file_path, filename)
                print(f"   ✅ Added: {filename}")
            else:
                print(f"   ⚠️  Skipped: {filename} (not found)")
        
        # Add dependencies from package directory
        package_dir = script_dir / 'package'
        if package_dir.exists():
            print("\n   📦 Adding dependencies from package directory...")
            dep_count = 0
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(package_dir))
                    zipf.write(file_path, arcname)
                    dep_count += 1
            print(f"   ✅ Added {dep_count} dependency files")
        else:
            print("\n   ⚠️  Package directory not found - run: pip install requests python-dotenv -t lambda/package/")
    
    print(f"\n✅ Deployment package created: {zip_path.name}")
    print(f"   Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return zip_path


def create_iam_role(iam_client, role_name):
    """Create IAM role for Lambda function"""
    
    print(f"\n🔐 Creating IAM role: {role_name}")
    
    trust_policy = {
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
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for Adverse Media Scanner Lambda function'
        )
        role_arn = role['Role']['Arn']
        print(f"   ✅ Created new role: {role_arn}")
        
        # Wait for role to be available
        print("   ⏳ Waiting for role to be available...")
        time.sleep(10)
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"   ℹ️  Role already exists: {role_arn}")
    
    # Attach necessary policies
    policies = [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',  # CloudWatch Logs
        'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess',  # DynamoDB access
        'arn:aws:iam::aws:policy/AmazonBedrockFullAccess',  # AWS Bedrock (Nova Pro)
    ]
    
    print("\n   📋 Attaching policies:")
    for policy_arn in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print(f"      ✅ {policy_arn.split('/')[-1]}")
        except Exception as e:
            print(f"      ⚠️  {policy_arn.split('/')[-1]}: {e}")
    
    return role_arn


def deploy_lambda_function(lambda_client, function_name, role_arn, zip_path, serper_api_key):
    """Deploy or update Lambda function"""
    
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
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='Adverse Media Scanner using Serper API and AWS Nova Pro',
            Timeout=300,  # 5 minutes
            MemorySize=512,  # 512 MB
            Environment={'Variables': environment_variables},
            Tags={
                'Project': 'CompanyDataExtraction',
                'Component': 'AdverseMediaScanner',
                'ManagedBy': 'PythonScript'
            }
        )
        print(f"   ✅ Created new Lambda function")
        print(f"   Function ARN: {response['FunctionArn']}")
        
    except lambda_client.exceptions.ResourceConflictException:
        # Function exists, update it
        print("   ℹ️  Function already exists, updating...")
        
        # Wait for function to be in a stable state
        waiter = lambda_client.get_waiter('function_updated')
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
        
        # Wait for function to be updated before changing configuration
        print("   ⏳ Waiting for function code update to complete...")
        waiter = lambda_client.get_waiter('function_updated_v2')
        try:
            waiter.wait(FunctionName=function_name, WaiterConfig={'MaxAttempts': 60, 'Delay': 2})
        except Exception as e:
            print(f"   ⚠️  Waiter warning: {e}")
            time.sleep(5)  # Fallback wait
        
        # Update function configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Description='Adverse Media Scanner using Serper API and AWS Nova Pro',
            Timeout=300,
            MemorySize=512,
            Environment={'Variables': environment_variables}
        )
        print("   ✅ Updated function configuration")
        
        response = lambda_client.get_function(FunctionName=function_name)
    
    return response


def test_lambda_function(lambda_client, function_name):
    """Test the deployed Lambda function"""
    
    print(f"\n🧪 Testing Lambda function: {function_name}")
    
    test_payload = {
        'company_name': 'Test Company',
        'years': 1
    }
    
    print(f"   Test payload: {json.dumps(test_payload)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        print(f"\n   Response Status Code: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result.get('body', '{}'))
            print(f"   ✅ Test successful!")
            print(f"   Company: {body.get('company_name')}")
            print(f"   Adverse Items Found: {body.get('adverse_items_found')}")
            print(f"   Message: {body.get('message')}")
        else:
            print(f"   ⚠️  Test completed with status: {result.get('statusCode')}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def main():
    """Main deployment function"""
    
    print("\n" + "=" * 80)
    print("AWS Lambda Deployment - Adverse Media Scanner")
    print("=" * 80)
    
    # Configuration
    function_name = 'AdverseMediaScanner'
    role_name = 'AdverseMediaScannerLambdaRole'
    
    # Get Serper API key from environment
    serper_api_key = os.getenv('SERPER_API_KEY')
    if not serper_api_key:
        print("\n❌ Error: SERPER_API_KEY not found in environment variables")
        print("   Please set it using: export SERPER_API_KEY='your_key'")
        sys.exit(1)
    
    try:
        # Initialize AWS clients using 'diligent' profile
        session = boto3.Session(profile_name='diligent', region_name='us-east-1')
        lambda_client = session.client('lambda')
        iam_client = session.client('iam')
        
        print(f"\n✅ Connected to AWS (Profile: diligent, Region: us-east-1)")
        
        # Step 1: Create deployment package
        zip_path = create_deployment_package()
        
        # Step 2: Create/get IAM role
        role_arn = create_iam_role(iam_client, role_name)
        
        # Step 3: Deploy Lambda function
        response = deploy_lambda_function(
            lambda_client, 
            function_name, 
            role_arn, 
            zip_path,
            serper_api_key
        )
        
        # Step 4: Test the function
        print("\n⏳ Waiting 5 seconds before testing...")
        time.sleep(5)
        test_result = test_lambda_function(lambda_client, function_name)
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 80)
        print(f"\n📊 Lambda Function Details:")
        print(f"   Name: {function_name}")
        print(f"   Runtime: Python 3.11")
        print(f"   Memory: 512 MB")
        print(f"   Timeout: 300 seconds (5 minutes)")
        print(f"   Handler: lambda_function.lambda_handler")
        
        print(f"\n🎯 To invoke this function:")
        print(f'   aws lambda invoke --function-name {function_name} \\')
        print(f'       --payload \'{{"company_name": "Company Name", "years": 5}}\' \\')
        print(f'       --profile diligent \\')
        print(f'       response.json')
        
        print(f"\n📝 CloudWatch Logs:")
        print(f"   Log Group: /aws/lambda/{function_name}")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

