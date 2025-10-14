#!/usr/bin/env python3
"""
Deploy API Gateway to invoke Step Function for Company Data Extraction

This script creates:
1. REST API Gateway
2. IAM role for API Gateway to invoke Step Functions
3. API resource and method (POST)
4. Integration with Step Functions
5. Deployment and stage
"""

import boto3
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_account_id(session=None):
    """Get AWS account ID"""
    if session:
        sts_client = session.client('sts', region_name='us-east-1')
    else:
        sts_client = boto3.client('sts', region_name='us-east-1')
    return sts_client.get_caller_identity()['Account']

def get_stepfunction_arn(account_id):
    """Get Step Function ARN"""
    state_machine_name = "CompanyDataExtractionPipeline"
    region = "us-east-1"
    return f"arn:aws:states:{region}:{account_id}:stateMachine:{state_machine_name}"

def create_api_gateway_role(iam_client, account_id):
    """Create IAM role for API Gateway to invoke Step Functions"""
    role_name = "APIGatewayStepFunctionsRole"
    
    # Trust policy for API Gateway
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "apigateway.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Check if role exists
    try:
        role = iam_client.get_role(RoleName=role_name)
        logger.info(f"✅ IAM role already exists: {role_name}")
        role_arn = role['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        # Create role
        logger.info(f"Creating IAM role: {role_name}")
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Allows API Gateway to invoke Step Functions"
        )
        role_arn = role['Role']['Arn']
        logger.info(f"✅ Created IAM role: {role_name}")
        
        # Wait for role to propagate
        time.sleep(10)
    
    # Attach policy to invoke Step Functions
    policy_name = "InvokeStepFunctionsPolicy"
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "states:StartExecution"
                ],
                "Resource": [
                    f"arn:aws:states:us-east-1:{account_id}:stateMachine:*"
                ]
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        logger.info(f"✅ Attached policy: {policy_name}")
    except Exception as e:
        logger.warning(f"Policy might already be attached: {e}")
    
    return role_arn

def create_rest_api(apigw_client):
    """Create REST API Gateway"""
    api_name = "CompanyDataExtractionAPI"
    
    # Check if API exists
    apis = apigw_client.get_rest_apis()
    for api in apis['items']:
        if api['name'] == api_name:
            logger.info(f"✅ API already exists: {api_name} (ID: {api['id']})")
            return api['id']
    
    # Create new API
    logger.info(f"Creating REST API: {api_name}")
    response = apigw_client.create_rest_api(
        name=api_name,
        description="API to trigger company data extraction via Step Functions",
        endpointConfiguration={
            'types': ['REGIONAL']
        }
    )
    api_id = response['id']
    logger.info(f"✅ Created REST API: {api_name} (ID: {api_id})")
    return api_id

def get_root_resource(apigw_client, api_id):
    """Get root resource ID"""
    resources = apigw_client.get_resources(restApiId=api_id)
    for resource in resources['items']:
        if resource['path'] == '/':
            return resource['id']
    raise Exception("Root resource not found")

def create_extract_resource(apigw_client, api_id, parent_id):
    """Create /extract resource"""
    # Check if resource exists
    resources = apigw_client.get_resources(restApiId=api_id)
    for resource in resources['items']:
        if resource['path'] == '/extract':
            logger.info(f"✅ Resource already exists: /extract")
            return resource['id']
    
    # Create resource
    logger.info("Creating resource: /extract")
    response = apigw_client.create_resource(
        restApiId=api_id,
        parentId=parent_id,
        pathPart='extract'
    )
    logger.info(f"✅ Created resource: /extract")
    return response['id']

def create_post_method(apigw_client, api_id, resource_id, role_arn, stepfunction_arn):
    """Create POST method with Step Functions integration"""
    
    # Check if method exists
    try:
        apigw_client.get_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST'
        )
        logger.info("⚠️  POST method already exists, deleting and recreating...")
        apigw_client.delete_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST'
        )
    except apigw_client.exceptions.NotFoundException:
        pass
    
    # Create method
    logger.info("Creating POST method")
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE',
        apiKeyRequired=False,
        requestParameters={},
        requestModels={
            'application/json': 'Empty'
        }
    )
    logger.info("✅ Created POST method")
    
    # Create integration with Step Functions
    logger.info("Creating Step Functions integration")
    
    # Request template to transform API input to Step Function input
    request_template = """{
    "input": "$util.escapeJavaScript($input.json('$'))",
    "stateMachineArn": """ + f'"{stepfunction_arn}"' + """
}"""
    
    apigw_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        type='AWS',
        integrationHttpMethod='POST',
        uri=f'arn:aws:apigateway:us-east-1:states:action/StartExecution',
        credentials=role_arn,
        requestTemplates={
            'application/json': request_template
        },
        passthroughBehavior='NEVER'
    )
    logger.info("✅ Created Step Functions integration")
    
    # Create method response (200)
    apigw_client.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        statusCode='200',
        responseModels={
            'application/json': 'Empty'
        },
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': False
        }
    )
    logger.info("✅ Created 200 method response")
    
    # Create integration response
    response_template = """{
    "executionArn": "$input.path('$.executionArn')",
    "startDate": "$input.path('$.startDate')",
    "message": "Step Function execution started successfully"
}"""
    
    apigw_client.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        statusCode='200',
        responseTemplates={
            'application/json': response_template
        },
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': "'*'"
        }
    )
    logger.info("✅ Created integration response")
    
    # Create method response (500) for errors
    apigw_client.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        statusCode='500',
        responseModels={
            'application/json': 'Empty'
        }
    )
    
    # Create integration response for errors
    error_response_template = """{
    "error": "Step Function execution failed",
    "message": "$input.path('$.errorMessage')"
}"""
    
    apigw_client.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        statusCode='500',
        selectionPattern='.*error.*',
        responseTemplates={
            'application/json': error_response_template
        }
    )
    logger.info("✅ Created error responses")

def enable_cors(apigw_client, api_id, resource_id):
    """Enable CORS by adding OPTIONS method"""
    
    # Check if OPTIONS method exists
    try:
        apigw_client.get_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS'
        )
        logger.info("⚠️  OPTIONS method already exists")
        return
    except apigw_client.exceptions.NotFoundException:
        pass
    
    logger.info("Enabling CORS (creating OPTIONS method)")
    
    # Create OPTIONS method
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        authorizationType='NONE'
    )
    
    # Create mock integration for OPTIONS
    apigw_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        type='MOCK',
        requestTemplates={
            'application/json': '{"statusCode": 200}'
        }
    )
    
    # Create method response for OPTIONS
    apigw_client.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': False,
            'method.response.header.Access-Control-Allow-Methods': False,
            'method.response.header.Access-Control-Allow-Origin': False
        },
        responseModels={
            'application/json': 'Empty'
        }
    )
    
    # Create integration response for OPTIONS
    apigw_client.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
            'method.response.header.Access-Control-Allow-Origin': "'*'"
        },
        responseTemplates={
            'application/json': ''
        }
    )
    
    logger.info("✅ CORS enabled")

def deploy_api(apigw_client, api_id):
    """Deploy API to a stage"""
    stage_name = "prod"
    
    logger.info(f"Deploying API to stage: {stage_name}")
    response = apigw_client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
        stageDescription='Production stage',
        description=f'Deployment at {datetime.now().isoformat()}'
    )
    
    logger.info(f"✅ Deployed API to stage: {stage_name}")
    return stage_name

def main():
    """Main deployment function"""
    print("=" * 80)
    print("🚀 DEPLOYING API GATEWAY FOR STEP FUNCTION")
    print("=" * 80)
    print()
    
    # Initialize clients with diligent profile
    session = boto3.Session(profile_name='diligent')
    iam_client = session.client('iam', region_name='us-east-1')
    apigw_client = session.client('apigateway', region_name='us-east-1')
    
    # Get account ID and Step Function ARN
    account_id = get_account_id(session)
    stepfunction_arn = get_stepfunction_arn(account_id)
    
    logger.info(f"Account ID: {account_id}")
    logger.info(f"Step Function ARN: {stepfunction_arn}")
    print()
    
    # Step 1: Create IAM role
    print("📋 Step 1: Creating IAM role for API Gateway")
    print("-" * 80)
    role_arn = create_api_gateway_role(iam_client, account_id)
    print()
    
    # Step 2: Create REST API
    print("📋 Step 2: Creating REST API")
    print("-" * 80)
    api_id = create_rest_api(apigw_client)
    print()
    
    # Step 3: Create resources
    print("📋 Step 3: Creating API resources")
    print("-" * 80)
    root_id = get_root_resource(apigw_client, api_id)
    extract_resource_id = create_extract_resource(apigw_client, api_id, root_id)
    print()
    
    # Step 4: Create POST method
    print("📋 Step 4: Creating POST method and integration")
    print("-" * 80)
    create_post_method(apigw_client, api_id, extract_resource_id, role_arn, stepfunction_arn)
    print()
    
    # Step 5: Enable CORS
    print("📋 Step 5: Enabling CORS")
    print("-" * 80)
    enable_cors(apigw_client, api_id, extract_resource_id)
    print()
    
    # Step 6: Deploy API
    print("📋 Step 6: Deploying API")
    print("-" * 80)
    stage_name = deploy_api(apigw_client, api_id)
    print()
    
    # Print summary
    api_url = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/{stage_name}/extract"
    
    print("=" * 80)
    print("✅ API GATEWAY DEPLOYMENT COMPLETE")
    print("=" * 80)
    print()
    print(f"API ID: {api_id}")
    print(f"Stage: {stage_name}")
    print(f"Endpoint URL: {api_url}")
    print()
    print("=" * 80)
    print("📝 HOW TO USE THE API")
    print("=" * 80)
    print()
    print("Method: POST")
    print(f"URL: {api_url}")
    print()
    print("Headers:")
    print("  Content-Type: application/json")
    print()
    print("Body (JSON):")
    print(json.dumps({
        "company_name": "Apple Inc",
        "website_url": "https://apple.com",
        "stock_symbol": "AAPL"
    }, indent=2))
    print()
    print("=" * 80)
    print("🧪 TEST COMMAND (curl)")
    print("=" * 80)
    print()
    print(f"""curl -X POST {api_url} \\
  -H "Content-Type: application/json" \\
  -d '{{"company_name": "Apple Inc", "website_url": "https://apple.com", "stock_symbol": "AAPL"}}'
""")
    print()
    print("=" * 80)
    print("🧪 TEST COMMAND (Python)")
    print("=" * 80)
    print()
    print(f"""import requests
import json

url = "{api_url}"
payload = {{
    "company_name": "Apple Inc",
    "website_url": "https://apple.com",
    "stock_symbol": "AAPL"
}}

response = requests.post(url, json=payload)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
""")
    print()
    print("=" * 80)
    print("📊 EXPECTED RESPONSE")
    print("=" * 80)
    print()
    print("Status: 200 OK")
    print("Body:")
    print(json.dumps({
        "executionArn": "arn:aws:states:us-east-1:891067072053:execution:CompanyDataExtractionPipeline:...",
        "startDate": "2025-10-14T10:30:00.000Z",
        "message": "Step Function execution started successfully"
    }, indent=2))
    print()
    print("=" * 80)
    print()
    
    # Save configuration
    config = {
        "api_id": api_id,
        "stage_name": stage_name,
        "endpoint_url": api_url,
        "region": "us-east-1",
        "deployment_date": datetime.now().isoformat()
    }
    
    with open('api_gateway_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("💾 Configuration saved to: api_gateway_config.json")
    print()

if __name__ == "__main__":
    main()

