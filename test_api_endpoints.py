import boto3
import json
import time

session = boto3.Session(profile_name='diligent')
sfn_client = session.client('stepfunctions', region_name='us-east-1')

# Test data
test_company = {
    "company_name": "Lyft",
    "website_url": "https://www.lyft.com",
    "stock_symbol": "LYFT"
}

api_endpoint = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod"

print('='*80)
print('🧪 TESTING API GATEWAY ENDPOINTS')
print('='*80)
print()

# Test 1: Standard extraction (SEC + CXO only)
print('Test 1: Standard Extraction (/extract)')
print('-'*80)
print(f'Endpoint: {api_endpoint}/extract')
print(f'Request: {json.dumps(test_company, indent=2)}')
print()

import requests
response1 = requests.post(
    f'{api_endpoint}/extract',
    headers={'Content-Type': 'application/json'},
    json=test_company
)

print(f'Status Code: {response1.status_code}')
print(f'Response: {json.dumps(response1.json(), indent=2)}')

if response1.status_code == 200:
    exec_arn1 = response1.json()['executionArn']
    print(f'Execution ARN: {exec_arn1}')
    print('✅ Standard extraction started')
else:
    print('❌ Standard extraction failed')
    exec_arn1 = None

print()
print('='*80)
print()

# Test 2: Full extraction with private company data (SEC + CXO + Private)
print('Test 2: Full Extraction with Private Data (/extract-private)')
print('-'*80)
print(f'Endpoint: {api_endpoint}/extract-private')
print(f'Request: {json.dumps(test_company, indent=2)}')
print()

response2 = requests.post(
    f'{api_endpoint}/extract-private',
    headers={'Content-Type': 'application/json'},
    json=test_company
)

print(f'Status Code: {response2.status_code}')
print(f'Response: {json.dumps(response2.json(), indent=2)}')

if response2.status_code == 200:
    exec_arn2 = response2.json()['executionArn']
    print(f'Execution ARN: {exec_arn2}')
    print('✅ Full extraction started (includes private company data)')
else:
    print('❌ Full extraction failed')
    exec_arn2 = None

print()
print('='*80)
print('📊 MONITORING EXECUTIONS')
print('='*80)
print()

# Monitor both executions
print('Waiting for executions to complete (this may take 1-2 minutes)...')
print()

if exec_arn1:
    print('Checking standard extraction status...')
    for i in range(30):
        time.sleep(3)
        response = sfn_client.describe_execution(executionArn=exec_arn1)
        status = response['status']
        if status in ['SUCCEEDED', 'FAILED', 'ABORTED']:
            print(f'✅ Standard extraction: {status}')
            break
        print(f'   Status: {status}... (waiting)')

print()

if exec_arn2:
    print('Checking full extraction (with private) status...')
    for i in range(30):
        time.sleep(3)
        response = sfn_client.describe_execution(executionArn=exec_arn2)
        status = response['status']
        if status in ['SUCCEEDED', 'FAILED', 'ABORTED']:
            print(f'✅ Full extraction: {status}')
            break
        print(f'   Status: {status}... (waiting)')

print()
print('='*80)
print('✅ TESTING COMPLETE')
print('='*80)
