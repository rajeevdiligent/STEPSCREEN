#!/usr/bin/env python3
"""
Deploy Complete Company Data Extraction Step Function

This Step Function orchestrates:
1. Nova SEC Extractor
2. CXO Website Extractor (parallel)
3. Adverse Media Scanner (parallel)
4. Sanctions Screener (after CXO completes)
5. DynamoDB to S3 Merger

Flow:
  Input (company_name, location)
    → Nova SEC Extractor
    → Extract company_id and website_url
    → Parallel:
        - CXO Extractor
        - Adverse Media Scanner
    → Sanctions Screener (uses CXO data from DynamoDB)
    → Compile Results
    → Merge & Save to S3
    → Success
"""

import boto3
import json
import time
from pathlib import Path

def get_account_id(session):
    """Get AWS account ID"""
    sts_client = session.client('sts')
    return sts_client.get_caller_identity()['Account']


def create_stepfunction_role(iam_client, role_name, account_id, region):
    """Create IAM role for Step Functions"""
    
    print(f"\n🔐 Creating IAM role: {role_name}")
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "states.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for Complete Company Data Extraction Step Function'
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
    
    # Create inline policy for Lambda invocation
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": [
                    f"arn:aws:lambda:{region}:{account_id}:function:NovaSECExtractor",
                    f"arn:aws:lambda:{region}:{account_id}:function:CXOWebsiteExtractor",
                    f"arn:aws:lambda:{region}:{account_id}:function:AdverseMediaScanner",
                    f"arn:aws:lambda:{region}:{account_id}:function:SanctionsScreener",
                    f"arn:aws:lambda:{region}:{account_id}:function:DynamoDBToS3Merger"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='StepFunctionExecutionPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        print("   ✅ Attached execution policy")
    except Exception as e:
        print(f"   ⚠️  Policy attachment: {e}")
    
    return role_arn


def deploy_step_function(sfn_client, state_machine_name, role_arn, definition_file):
    """Deploy or update Step Function"""
    
    print(f"\n🚀 Deploying Step Function: {state_machine_name}")
    
    # Load definition
    with open(definition_file, 'r') as f:
        definition = f.read()
    
    try:
        # Try to create new state machine
        response = sfn_client.create_state_machine(
            name=state_machine_name,
            definition=definition,
            roleArn=role_arn,
            type='STANDARD',
            tags=[
                {
                    'key': 'Project',
                    'value': 'CompanyDataExtraction'
                },
                {
                    'key': 'Component',
                    'value': 'CompleteExtractionPipeline'
                }
            ]
        )
        print(f"   ✅ Created new Step Function")
        print(f"   State Machine ARN: {response['stateMachineArn']}")
        return response['stateMachineArn']
        
    except sfn_client.exceptions.StateMachineAlreadyExists:
        # State machine exists, update it
        print("   ℹ️  Step Function already exists, updating...")
        
        # Get existing state machine ARN
        state_machines = sfn_client.list_state_machines()
        state_machine_arn = None
        for sm in state_machines['stateMachines']:
            if sm['name'] == state_machine_name:
                state_machine_arn = sm['stateMachineArn']
                break
        
        if state_machine_arn:
            sfn_client.update_state_machine(
                stateMachineArn=state_machine_arn,
                definition=definition,
                roleArn=role_arn
            )
            print(f"   ✅ Updated Step Function")
            print(f"   State Machine ARN: {state_machine_arn}")
            return state_machine_arn
        else:
            raise Exception("Could not find existing state machine")


def test_step_function(sfn_client, state_machine_arn):
    """Test the Step Function with a sample execution"""
    
    print(f"\n🧪 Testing Step Function")
    
    test_input = {
        "company_name": "Apple Inc",
        "location": "California"
    }
    
    print(f"   Test input: {json.dumps(test_input, indent=2)}")
    
    try:
        response = sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(test_input)
        )
        
        execution_arn = response['executionArn']
        print(f"\n   ✅ Execution started!")
        print(f"   Execution ARN: {execution_arn}")
        print(f"   Start Time: {response['startDate']}")
        
        # Wait a moment and check status
        print("\n   ⏳ Waiting for execution to progress...")
        time.sleep(5)
        
        execution = sfn_client.describe_execution(executionArn=execution_arn)
        status = execution['status']
        
        print(f"   📊 Current Status: {status}")
        
        if status == 'RUNNING':
            print("   ℹ️  Execution is in progress (this may take 30-60 seconds)")
            print(f"   ℹ️  Monitor at: https://console.aws.amazon.com/states/home?region=us-east-1#/executions/details/{execution_arn}")
        elif status == 'SUCCEEDED':
            print("   ✅ Execution completed successfully!")
            output = json.loads(execution['output'])
            print(f"   Output: {json.dumps(output, indent=2)}")
        elif status == 'FAILED':
            print(f"   ❌ Execution failed")
            if 'cause' in execution:
                print(f"   Cause: {execution['cause']}")
        
        return execution_arn
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def main():
    """Main deployment function"""
    
    print("\n" + "=" * 80)
    print("Step Function Deployment - Complete Company Data Extraction")
    print("=" * 80)
    
    # Configuration
    state_machine_name = 'CompleteCompanyDataExtraction'
    role_name = 'CompleteCompanyDataExtractionRole'
    definition_file = Path(__file__).parent / 'stepfunction_definition_complete_extraction.json'
    region = 'us-east-1'
    
    if not definition_file.exists():
        print(f"\n❌ Error: Definition file not found: {definition_file}")
        return
    
    try:
        # Initialize AWS clients
        session = boto3.Session(profile_name='diligent', region_name=region)
        sfn_client = session.client('stepfunctions')
        iam_client = session.client('iam')
        
        account_id = get_account_id(session)
        
        print(f"\n✅ Connected to AWS")
        print(f"   Profile: diligent")
        print(f"   Region: {region}")
        print(f"   Account ID: {account_id}")
        
        # Step 1: Create/get IAM role
        role_arn = create_stepfunction_role(iam_client, role_name, account_id, region)
        
        # Step 2: Deploy Step Function
        state_machine_arn = deploy_step_function(sfn_client, state_machine_name, role_arn, definition_file)
        
        # Step 3: Test the Step Function
        execution_arn = test_step_function(sfn_client, state_machine_arn)
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 80)
        
        print(f"\n📊 Step Function Details:")
        print(f"   Name: {state_machine_name}")
        print(f"   ARN: {state_machine_arn}")
        print(f"   Region: {region}")
        
        print(f"\n🎯 To start an execution:")
        print(f'   aws stepfunctions start-execution \\')
        print(f'       --state-machine-arn {state_machine_arn} \\')
        print(f'       --input \'{{"company_name": "Company Name", "location": "Location"}}\' \\')
        print(f'       --profile diligent')
        
        print(f"\n📝 CloudWatch Logs:")
        print(f"   Log Group: /aws/vendedlogs/states/{state_machine_name}")
        
        print(f"\n🌐 AWS Console:")
        print(f"   https://console.aws.amazon.com/states/home?region={region}#/statemachines/view/{state_machine_arn}")
        
        if execution_arn:
            print(f"\n🧪 Test Execution:")
            print(f"   ARN: {execution_arn}")
            print(f"   Monitor: https://console.aws.amazon.com/states/home?region={region}#/executions/details/{execution_arn}")
        
        print()
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

