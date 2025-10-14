#!/usr/bin/env python3
"""
Update API Gateway to Add /extract-private Path

This script adds a new resource path that includes private company extraction.
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_account_id(session=None):
    """Get AWS account ID"""
    if session:
        sts_client = session.client('sts', region_name='us-east-1')
    else:
        sts_client = boto3.client('sts', region_name='us-east-1')
    return sts_client.get_caller_identity()['Account']

def get_api_gateway_id(apigw_client):
    """Find the existing API Gateway"""
    response = apigw_client.get_rest_apis()
    for api in response['items']:
        if 'CompanyDataExtraction' in api['name']:
            return api['id'], api['name']
    return None, None

def get_stepfunction_arn(account_id):
    """Get Step Function ARN"""
    return f"arn:aws:states:us-east-1:{account_id}:stateMachine:CompanyDataExtractionPipeline"

def create_private_extract_resource(apigw_client, api_id, root_id, role_arn, stepfunction_arn):
    """Create /extract-private resource"""
    
    # Create resource
    logger.info("Creating /extract-private resource...")
    resource_response = apigw_client.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='extract-private'
    )
    resource_id = resource_response['id']
    logger.info(f"✅ Created resource: /extract-private (ID: {resource_id})")
    
    # Create POST method
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE',
        requestParameters={},
        requestModels={
            'application/json': 'Empty'
        }
    )
    logger.info("✅ Created POST method")
    
    # Create Step Functions integration with include_private_data flag
    request_template = """{
    "input": "{\\"company_name\\": \\"$util.escapeJavaScript($input.path('$.company_name'))\\", \\"website_url\\": \\"$util.escapeJavaScript($input.path('$.website_url'))\\", \\"stock_symbol\\": \\"$util.escapeJavaScript($input.path('$.stock_symbol'))\\", \\"include_private_data\\": true}",
    "stateMachineArn": \"""" + stepfunction_arn + """\"
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
    logger.info("✅ Created Step Functions integration (with include_private_data: true)")
    
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
    "message": "Step Function execution started with private company data extraction"
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
    
    # Enable CORS for OPTIONS method
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        authorizationType='NONE'
    )
    
    apigw_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        type='MOCK',
        requestTemplates={
            'application/json': '{"statusCode": 200}'
        }
    )
    
    apigw_client.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': False,
            'method.response.header.Access-Control-Allow-Methods': False,
            'method.response.header.Access-Control-Allow-Origin': False
        }
    )
    
    apigw_client.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
            'method.response.header.Access-Control-Allow-Origin': "'*'"
        }
    )
    logger.info("✅ Enabled CORS")
    
    return resource_id

def main():
    """Main function"""
    print("="*80)
    print("🚀 UPDATING API GATEWAY WITH /extract-private PATH")
    print("="*80)
    print()
    
    # Initialize clients
    session = boto3.Session(profile_name='diligent')
    apigw_client = session.client('apigateway', region_name='us-east-1')
    iam_client = session.client('iam', region_name='us-east-1')
    
    # Get account ID
    account_id = get_account_id(session)
    logger.info(f"Account ID: {account_id}")
    
    # Find existing API Gateway
    api_id, api_name = get_api_gateway_id(apigw_client)
    if not api_id:
        logger.error("❌ API Gateway not found")
        return
    
    logger.info(f"Found API Gateway: {api_name} (ID: {api_id})")
    
    # Get root resource
    resources = apigw_client.get_resources(restApiId=api_id)
    root_id = [r['id'] for r in resources['items'] if r['path'] == '/'][0]
    logger.info(f"Root resource ID: {root_id}")
    
    # Check if /extract-private already exists
    existing_paths = [r['path'] for r in resources['items']]
    if '/extract-private' in existing_paths:
        logger.info("⚠️  /extract-private already exists, skipping creation")
        resource_id = [r['id'] for r in resources['items'] if r['path'] == '/extract-private'][0]
    else:
        # Get IAM role ARN
        role_name = 'APIGatewayStepFunctionsRole'
        role_response = iam_client.get_role(RoleName=role_name)
        role_arn = role_response['Role']['Arn']
        logger.info(f"IAM Role ARN: {role_arn}")
        
        # Get Step Function ARN
        stepfunction_arn = get_stepfunction_arn(account_id)
        logger.info(f"Step Function ARN: {stepfunction_arn}")
        
        print()
        logger.info("Creating /extract-private resource...")
        resource_id = create_private_extract_resource(apigw_client, api_id, root_id, role_arn, stepfunction_arn)
    
    # Deploy to prod stage
    print()
    logger.info("Deploying to 'prod' stage...")
    deployment = apigw_client.create_deployment(
        restApiId=api_id,
        stageName='prod',
        description='Added /extract-private path for private company extraction'
    )
    logger.info(f"✅ Deployed (Deployment ID: {deployment['id']})")
    
    # Get API endpoint
    api_endpoint = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/prod"
    
    print()
    print("="*80)
    print("✅ API GATEWAY UPDATED")
    print("="*80)
    print()
    print(f"API ID: {api_id}")
    print(f"API Name: {api_name}")
    print()
    print("Available Endpoints:")
    print(f"  1. Standard Extraction (SEC + CXO):")
    print(f"     POST {api_endpoint}/extract")
    print()
    print(f"  2. Full Extraction (SEC + CXO + Private): ⭐ NEW")
    print(f"     POST {api_endpoint}/extract-private")
    print()
    print("Request Format (both endpoints):")
    print("  {")
    print('    "company_name": "Tesla",')
    print('    "website_url": "https://www.tesla.com",')
    print('    "stock_symbol": "TSLA"')
    print("  }")
    print()
    print("Difference:")
    print("  • /extract → runs SEC + CXO only")
    print("  • /extract-private → runs SEC + CXO + Private Company Extractor")
    print()

if __name__ == "__main__":
    main()

