#!/usr/bin/env python3
"""
Deploy AWS Step Functions State Machine for Company Data Extraction Pipeline
"""

import boto3
import json
import logging
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def create_stepfunction_role(iam_client):
    """Create IAM role for Step Functions"""
    role_name = "CompanyDataExtractionStepFunctionRole"
    
    # Trust policy for Step Functions
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
    
    # Policy to invoke Lambda functions
    lambda_invoke_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": [
                    "arn:aws:lambda:us-east-1:*:function:NovaSECExtractor",
                    "arn:aws:lambda:us-east-1:*:function:CXOWebsiteExtractor",
                    "arn:aws:lambda:us-east-1:*:function:DynamoDBToS3Merger"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            }
        ]
    }
    
    try:
        # Try to create the role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for Company Data Extraction Step Functions',
            Tags=[
                {'Key': 'Project', 'Value': 'STEPSCREEN'},
                {'Key': 'Purpose', 'Value': 'StepFunctions'}
            ]
        )
        logger.info(f"✅ Created IAM role: {role_name}")
        role_arn = response['Role']['Arn']
        
        # Attach inline policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='LambdaInvokePolicy',
            PolicyDocument=json.dumps(lambda_invoke_policy)
        )
        logger.info(f"✅ Attached Lambda invoke policy")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            logger.info(f"ℹ️  Role '{role_name}' already exists")
            response = iam_client.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
            
            # Update the policy
            try:
                iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName='LambdaInvokePolicy',
                    PolicyDocument=json.dumps(lambda_invoke_policy)
                )
                logger.info(f"✅ Updated Lambda invoke policy")
            except Exception as e:
                logger.warning(f"⚠️  Could not update policy: {e}")
        else:
            raise
    
    return role_arn


def deploy_state_machine(sfn_client, role_arn):
    """Deploy Step Functions state machine"""
    state_machine_name = "CompanyDataExtractionPipeline"
    
    # Load state machine definition
    with open('stepfunction_definition.json', 'r') as f:
        definition = f.read()
    
    try:
        # Try to create the state machine (without CloudWatch logging for now)
        response = sfn_client.create_state_machine(
            name=state_machine_name,
            definition=definition,
            roleArn=role_arn,
            type='STANDARD',
            tags=[
                {'key': 'Project', 'value': 'STEPSCREEN'},
                {'key': 'Purpose', 'value': 'DataExtraction'}
            ]
        )
        logger.info(f"✅ Created state machine: {state_machine_name}")
        state_machine_arn = response['stateMachineArn']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'StateMachineAlreadyExists':
            logger.info(f"ℹ️  State machine '{state_machine_name}' already exists. Updating...")
            
            # Get existing state machine ARN
            response = sfn_client.list_state_machines()
            state_machine_arn = None
            for sm in response['stateMachines']:
                if sm['name'] == state_machine_name:
                    state_machine_arn = sm['stateMachineArn']
                    break
            
            if state_machine_arn:
                # Update the state machine
                sfn_client.update_state_machine(
                    stateMachineArn=state_machine_arn,
                    definition=definition,
                    roleArn=role_arn
                )
                logger.info(f"✅ Updated state machine")
            else:
                raise Exception("Could not find existing state machine ARN")
        else:
            raise
    
    return state_machine_arn


def main():
    """Main deployment function"""
    
    print("\n" + "="*70)
    print("AWS Step Functions Deployment - Company Data Extraction Pipeline")
    print("="*70)
    
    # Initialize AWS clients
    session = boto3.Session(profile_name='diligent', region_name='us-east-1')
    iam_client = session.client('iam')
    sfn_client = session.client('stepfunctions')
    
    try:
        # Step 1: Create IAM role
        print("\n1️⃣  Setting up IAM role...")
        role_arn = create_stepfunction_role(iam_client)
        logger.info(f"   Role ARN: {role_arn}")
        
        # Wait a moment for IAM role to propagate
        import time
        logger.info("   Waiting for IAM role to propagate...")
        time.sleep(10)
        
        # Step 2: Deploy state machine
        print("\n2️⃣  Deploying state machine...")
        state_machine_arn = deploy_state_machine(sfn_client, role_arn)
        logger.info(f"   State Machine ARN: {state_machine_arn}")
        
        # Success summary
        print("\n" + "="*70)
        print("✅ DEPLOYMENT SUCCESSFUL")
        print("="*70)
        print(f"\nState Machine: CompanyDataExtractionPipeline")
        print(f"ARN: {state_machine_arn}")
        print(f"\nYou can now test the pipeline using:")
        print(f"  python test_stepfunction.py")
        print("\nOr via AWS Console:")
        print(f"  https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"\n❌ Deployment failed: {e}")
        raise


if __name__ == "__main__":
    main()

