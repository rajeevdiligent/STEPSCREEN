#!/usr/bin/env python3
"""
Test API Gateway for Company Data Extraction

This script tests the deployed API Gateway endpoint.
"""

import requests
import json
import time
import sys
import boto3
from datetime import datetime

def load_api_config():
    """Load API Gateway configuration"""
    try:
        with open('api_gateway_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ API Gateway config not found. Please deploy first: python deploy_api_gateway.py")
        sys.exit(1)

def test_api_endpoint(url, payload):
    """Test API Gateway endpoint"""
    print("=" * 80)
    print("🧪 TESTING API GATEWAY")
    print("=" * 80)
    print()
    
    print(f"Endpoint: {url}")
    print(f"Method: POST")
    print()
    print("Request Payload:")
    print(json.dumps(payload, indent=2))
    print()
    print("Sending request...")
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"✅ Response Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("Response Body:")
            print(json.dumps(result, indent=2))
            print()
            
            if 'executionArn' in result:
                execution_arn = result['executionArn']
                print("=" * 80)
                print("✅ STEP FUNCTION EXECUTION STARTED")
                print("=" * 80)
                print()
                print(f"Execution ARN: {execution_arn}")
                print(f"Start Date: {result.get('startDate', 'N/A')}")
                print()
                
                # Extract execution name from ARN
                execution_name = execution_arn.split(':')[-1]
                
                return execution_arn, execution_name
            else:
                print("⚠️  No execution ARN in response")
                return None, None
        else:
            print(f"❌ Error Response:")
            print(response.text)
            return None, None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None, None
    except json.JSONDecodeError:
        print("❌ Invalid JSON response")
        print(f"Raw response: {response.text}")
        return None, None

def monitor_execution(execution_arn):
    """Monitor Step Function execution"""
    print("=" * 80)
    print("📊 MONITORING STEP FUNCTION EXECUTION")
    print("=" * 80)
    print()
    
    session = boto3.Session(profile_name='diligent')
    sfn_client = session.client('stepfunctions', region_name='us-east-1')
    
    print("Waiting for execution to complete...")
    print("(This typically takes 71-92 seconds)")
    print()
    
    start_time = time.time()
    last_status = None
    
    while True:
        try:
            response = sfn_client.describe_execution(executionArn=execution_arn)
            status = response['status']
            
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] Status: {status}")
                last_status = status
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                elapsed = int(time.time() - start_time)
                print()
                print(f"Execution completed in {elapsed} seconds")
                print()
                
                if status == 'SUCCEEDED':
                    print("=" * 80)
                    print("✅ EXECUTION SUCCEEDED")
                    print("=" * 80)
                    print()
                    
                    # Parse output
                    output = json.loads(response.get('output', '{}'))
                    print("Execution Output:")
                    print(json.dumps(output, indent=2))
                    print()
                    
                    # Show S3 files if available
                    if 's3_files' in output:
                        print("📦 S3 Files Created:")
                        for s3_file in output['s3_files']:
                            print(f"  • s3://company-sec-cxo-data-diligent/{s3_file}")
                        print()
                    
                    # Show completeness
                    if 'sec_completeness' in output and 'cxo_completeness' in output:
                        print("📊 Data Quality:")
                        print(f"  • SEC Completeness: {output['sec_completeness']:.1f}%")
                        print(f"  • CXO Completeness: {output['cxo_completeness']:.1f}%")
                        print(f"  • Executives Found: {output.get('executives_count', 'N/A')}")
                        print()
                    
                    return True
                    
                else:
                    print("=" * 80)
                    print(f"❌ EXECUTION {status}")
                    print("=" * 80)
                    print()
                    
                    if 'error' in response:
                        print(f"Error: {response['error']}")
                        print(f"Cause: {response.get('cause', 'N/A')}")
                    
                    return False
            
            time.sleep(5)  # Poll every 5 seconds
            
        except KeyboardInterrupt:
            print()
            print("⚠️  Monitoring interrupted by user")
            print(f"You can check execution status in AWS Console:")
            print(f"https://console.aws.amazon.com/states/home?region=us-east-1#/executions/details/{execution_arn}")
            return False
        except Exception as e:
            print(f"❌ Error monitoring execution: {e}")
            return False

def main():
    """Main test function"""
    # Load API configuration
    config = load_api_config()
    endpoint_url = config['endpoint_url']
    
    # Test payloads
    test_companies = [
        {
            "company_name": "Tesla Inc",
            "website_url": "https://tesla.com",
            "stock_symbol": "TSLA"
        }
    ]
    
    # Allow user to specify company via command line
    if len(sys.argv) >= 3:
        test_companies = [{
            "company_name": sys.argv[1],
            "website_url": sys.argv[2],
            "stock_symbol": sys.argv[3] if len(sys.argv) >= 4 else ""
        }]
    
    # Test each company
    for payload in test_companies:
        execution_arn, execution_name = test_api_endpoint(endpoint_url, payload)
        
        if execution_arn:
            # Ask user if they want to monitor
            print("=" * 80)
            response = input("Monitor execution progress? (y/n): ").strip().lower()
            
            if response == 'y':
                success = monitor_execution(execution_arn)
                
                if success:
                    print("=" * 80)
                    print("🎉 TEST COMPLETED SUCCESSFULLY")
                    print("=" * 80)
                    print()
                    print("Next steps:")
                    print("1. Check S3 bucket for merged data:")
                    print(f"   aws s3 ls s3://company-sec-cxo-data-diligent/company_data/")
                    print()
                    print("2. Download the data:")
                    company_id = payload['company_name'].lower().replace(' ', '_').replace('.', '')
                    print(f"   aws s3 cp s3://company-sec-cxo-data-diligent/company_data/{company_id}_latest.json ./s3output/")
                    print()
            else:
                print()
                print("To monitor execution later, use:")
                print(f"aws stepfunctions describe-execution --execution-arn {execution_arn}")
                print()
        
        print()

if __name__ == "__main__":
    main()

