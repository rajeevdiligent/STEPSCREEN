#!/usr/bin/env python3
"""
Test all three Lambda functions:
1. Nova SEC Extractor
2. CXO Website Extractor  
3. Adverse Media Scanner
"""

import boto3
import json
import time

def test_lambda(lambda_client, function_name, payload, description):
    """Test a Lambda function and display results"""
    
    print("=" * 80)
    print(f"🧪 Testing: {description}")
    print("=" * 80)
    print(f"Function: {function_name}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        print("⏳ Invoking Lambda function...")
        start_time = time.time()
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        duration = time.time() - start_time
        
        result = json.loads(response['Payload'].read())
        status_code = result.get('statusCode', 0)
        
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📊 Status Code: {status_code}")
        print()
        
        if status_code == 200:
            body = json.loads(result.get('body', '{}'))
            
            print("✅ SUCCESS!")
            print("-" * 80)
            
            # Print key results based on function type
            if 'company_information' in body:
                # SEC Extractor
                info = body['company_information']
                print(f"Company: {info.get('registered_legal_name')}")
                print(f"Country: {info.get('country_of_incorporation')}")
                print(f"Employees: {info.get('number_of_employees')}")
                print(f"Revenue: {info.get('annual_revenue')}")
                print(f"Website: {info.get('website_url')}")
                
            elif 'total_executives_found' in body:
                # CXO Extractor
                print(f"Company Website: {body.get('company_website')}")
                print(f"Executives Found: {body.get('total_executives_found')}")
                if body.get('executives'):
                    print("\nTop Executives:")
                    for exec in body['executives'][:3]:
                        print(f"  - {exec.get('name')}: {exec.get('title')}")
                        
            elif 'adverse_items_found' in body:
                # Adverse Media Scanner
                print(f"Company: {body.get('company_name')}")
                print(f"Articles Scanned: {body.get('total_articles_scanned')}")
                print(f"Adverse Items Found: {body.get('adverse_items_found')}")
                print(f"Search Period: {body.get('search_period_start')} to {body.get('search_period_end')}")
                
                if body.get('adverse_items'):
                    print(f"\nTop {min(3, len(body['adverse_items']))} Adverse Items:")
                    for item in body['adverse_items'][:3]:
                        print(f"  - {item.get('title')}")
                        print(f"    Category: {item.get('adverse_category')} | Severity: {item.get('severity_score')}")
            
            print()
            return True
            
        else:
            print(f"❌ FAILED!")
            print(f"Response: {json.dumps(result, indent=2)}")
            print()
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Main test function"""
    
    print("\n" + "=" * 80)
    print("TESTING ALL LAMBDA FUNCTIONS")
    print("=" * 80)
    print()
    
    # Initialize AWS Lambda client
    try:
        session = boto3.Session(profile_name='diligent', region_name='us-east-1')
        lambda_client = session.client('lambda')
        print("✅ Connected to AWS Lambda (Profile: diligent, Region: us-east-1)")
        print()
    except Exception as e:
        print(f"❌ Error connecting to AWS: {e}")
        return
    
    # Test company
    test_company = "Microsoft Corporation"
    test_website = "https://www.microsoft.com"
    test_location = "Washington"
    
    results = []
    
    # Test 1: Nova SEC Extractor
    sec_payload = {
        "company_name": test_company,
        "location": test_location
    }
    results.append(test_lambda(
        lambda_client,
        "NovaSECExtractor",
        sec_payload,
        "Nova SEC Extractor"
    ))
    
    time.sleep(2)
    
    # Test 2: CXO Website Extractor
    cxo_payload = {
        "company_name": test_company,
        "website_url": test_website
    }
    results.append(test_lambda(
        lambda_client,
        "CXOWebsiteExtractor",  # Assuming this is the CXO Lambda name
        cxo_payload,
        "CXO Website Extractor"
    ))
    
    time.sleep(2)
    
    # Test 3: Adverse Media Scanner
    adverse_payload = {
        "company_name": test_company,
        "years": 2
    }
    results.append(test_lambda(
        lambda_client,
        "AdverseMediaScanner",
        adverse_payload,
        "Adverse Media Scanner"
    ))
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print()
    
    if all(results):
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

