#!/usr/bin/env python3
"""
Update API Gateway /extract-private endpoint to use PrivateCompanyDataPipeline
"""

import boto3

def main():
    session = boto3.Session(profile_name='diligent')
    apigw_client = session.client('apigateway', region_name='us-east-1')
    iam_client = session.client('iam', region_name='us-east-1')
    
    # Get account ID
    account_id = '891067072053'
    
    # API Gateway details
    api_id = '0x2t9tdx01'
    
    # Find /extract-private resource
    resources = apigw_client.get_resources(restApiId=api_id)
    resource_id = None
    for resource in resources['items']:
        if resource['path'] == '/extract-private':
            resource_id = resource['id']
            break
    
    if not resource_id:
        print('❌ /extract-private resource not found')
        return
    
    print('='*80)
    print('🔄 UPDATING API GATEWAY /extract-private ENDPOINT')
    print('='*80)
    print()
    print(f'Resource ID: {resource_id}')
    print()
    
    # Get IAM role for API Gateway
    role_name = 'APIGatewayStepFunctionsRole'
    role_response = iam_client.get_role(RoleName=role_name)
    role_arn = role_response['Role']['Arn']
    
    # New Step Function ARN (PrivateCompanyDataPipeline)
    new_stepfunction_arn = f'arn:aws:states:us-east-1:{account_id}:stateMachine:PrivateCompanyDataPipeline'
    
    # Update integration to use new Step Function
    request_template = """{
    "input": "{\\"company_name\\": \\"$util.escapeJavaScript($input.path('$.company_name'))\\", \\"website_url\\": \\"$util.escapeJavaScript($input.path('$.website_url'))\\", \\"stock_symbol\\": \\"$util.escapeJavaScript($input.path('$.stock_symbol'))\\"}",
    "stateMachineArn": \"""" + new_stepfunction_arn + """\"
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
    
    print('✅ Integration updated to use PrivateCompanyDataPipeline')
    print()
    
    # Update integration response message
    response_template = """{
    "executionArn": "$input.path('$.executionArn')",
    "startDate": "$input.path('$.startDate')",
    "message": "Private company data extraction started"
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
    
    print('✅ Integration response updated')
    print()
    
    # Deploy to prod
    deployment = apigw_client.create_deployment(
        restApiId=api_id,
        stageName='prod',
        description='Updated /extract-private to use PrivateCompanyDataPipeline'
    )
    
    print(f'✅ Deployed to prod (Deployment ID: {deployment["id"]})')
    print()
    print('='*80)
    print('CONFIGURATION COMPLETE')
    print('='*80)
    print()
    print('Endpoint: /extract-private')
    print(f'Step Function: PrivateCompanyDataPipeline')
    print('Workflow: Private Company → Export to S3')
    print('='*80)

if __name__ == "__main__":
    main()

