#!/usr/bin/env python3
"""
Test AWS Step Functions State Machine for Company Data Extraction Pipeline
"""

import boto3
import json
import sys
import time
from datetime import datetime
from botocore.exceptions import ClientError

def start_execution(sfn_client, state_machine_arn, company_name, website_url, stock_symbol=None):
    """Start a Step Functions execution"""
    
    execution_name = f"extraction-{company_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Prepare input
    input_data = {
        "company_name": company_name,
        "website_url": website_url
    }
    
    if stock_symbol:
        input_data["stock_symbol"] = stock_symbol
    
    print(f"\n🚀 Starting execution: {execution_name}")
    print(f"   Company: {company_name}")
    print(f"   Website: {website_url}")
    if stock_symbol:
        print(f"   Stock Symbol: {stock_symbol}")
    print(f"\n   Input: {json.dumps(input_data, indent=2)}")
    
    try:
        response = sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(input_data)
        )
        
        execution_arn = response['executionArn']
        print(f"\n✅ Execution started successfully")
        print(f"   Execution ARN: {execution_arn}")
        
        return execution_arn
        
    except ClientError as e:
        print(f"\n❌ Failed to start execution: {e}")
        raise


def monitor_execution(sfn_client, execution_arn, poll_interval=10):
    """Monitor execution status"""
    
    print(f"\n⏳ Monitoring execution (polling every {poll_interval} seconds)...")
    print("   Press Ctrl+C to stop monitoring (execution will continue)")
    
    start_time = time.time()
    
    try:
        while True:
            response = sfn_client.describe_execution(
                executionArn=execution_arn
            )
            
            status = response['status']
            elapsed = int(time.time() - start_time)
            
            if status == 'RUNNING':
                print(f"   [{elapsed}s] Status: {status} ⏳")
                time.sleep(poll_interval)
            elif status == 'SUCCEEDED':
                print(f"   [{elapsed}s] Status: {status} ✅")
                print(f"\n✅ Execution completed successfully!")
                
                # Parse and display output
                output = json.loads(response.get('output', '{}'))
                print(f"\n📊 Output:")
                print(json.dumps(output, indent=2))
                
                break
            elif status == 'FAILED':
                print(f"   [{elapsed}s] Status: {status} ❌")
                print(f"\n❌ Execution failed!")
                
                if 'error' in response:
                    print(f"   Error: {response.get('error')}")
                if 'cause' in response:
                    print(f"   Cause: {response.get('cause')}")
                
                break
            elif status == 'TIMED_OUT':
                print(f"   [{elapsed}s] Status: {status} ⏱️")
                print(f"\n⏱️  Execution timed out!")
                break
            elif status == 'ABORTED':
                print(f"   [{elapsed}s] Status: {status} 🛑")
                print(f"\n🛑 Execution was aborted!")
                break
            else:
                print(f"   [{elapsed}s] Status: {status}")
                time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Monitoring stopped (execution continues in background)")
        print(f"   Check status in AWS Console or run:")
        print(f"   aws stepfunctions describe-execution --execution-arn {execution_arn} --profile diligent")


def get_execution_history(sfn_client, execution_arn):
    """Get execution history for detailed debugging"""
    
    print(f"\n📋 Execution History:")
    
    try:
        response = sfn_client.get_execution_history(
            executionArn=execution_arn,
            maxResults=100,
            reverseOrder=False
        )
        
        for event in response['events']:
            event_type = event['type']
            timestamp = event['timestamp'].strftime('%H:%M:%S')
            event_id = event['id']
            
            # Filter for important events
            if event_type in [
                'ExecutionStarted',
                'ParallelStateEntered',
                'TaskStateEntered',
                'TaskScheduled',
                'TaskSucceeded',
                'TaskFailed',
                'ChoiceStateEntered',
                'ExecutionSucceeded',
                'ExecutionFailed'
            ]:
                print(f"   [{timestamp}] {event_type}")
                
                # Show task details
                if 'lambdaFunctionScheduledEventDetails' in event:
                    details = event['lambdaFunctionScheduledEventDetails']
                    print(f"              Lambda: {details.get('resource', 'N/A')}")
                
                if 'taskSucceededEventDetails' in event:
                    details = event['taskSucceededEventDetails']
                    if 'output' in details:
                        try:
                            output = json.loads(details['output'])
                            if 'statusCode' in output:
                                print(f"              Status: {output['statusCode']}")
                        except:
                            pass
        
    except Exception as e:
        print(f"   ⚠️  Could not retrieve history: {e}")


def main():
    """Main test function"""
    
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python test_stepfunction.py <company_name> <website_url> [stock_symbol]")
        print("\nExamples:")
        print("  python test_stepfunction.py 'Apple Inc' 'https://www.apple.com' 'AAPL'")
        print("  python test_stepfunction.py 'Netflix Inc' 'https://www.netflix.com' 'NFLX'")
        print("  python test_stepfunction.py 'Intel Corporation' 'https://www.intel.com' 'INTC'")
        sys.exit(1)
    
    company_name = sys.argv[1]
    website_url = sys.argv[2]
    stock_symbol = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("\n" + "="*70)
    print("AWS Step Functions Test - Company Data Extraction Pipeline")
    print("="*70)
    
    # Initialize AWS client
    session = boto3.Session(profile_name='diligent', region_name='us-east-1')
    sfn_client = session.client('stepfunctions')
    
    # Get state machine ARN
    state_machine_name = "CompanyDataExtractionPipeline"
    
    try:
        response = sfn_client.list_state_machines()
        state_machine_arn = None
        
        for sm in response['stateMachines']:
            if sm['name'] == state_machine_name:
                state_machine_arn = sm['stateMachineArn']
                break
        
        if not state_machine_arn:
            print(f"\n❌ State machine '{state_machine_name}' not found!")
            print("   Please deploy it first using: python deploy_stepfunction.py")
            sys.exit(1)
        
        print(f"\n✅ Found state machine: {state_machine_name}")
        print(f"   ARN: {state_machine_arn}")
        
        # Start execution
        execution_arn = start_execution(
            sfn_client,
            state_machine_arn,
            company_name,
            website_url,
            stock_symbol
        )
        
        # Monitor execution
        monitor_execution(sfn_client, execution_arn)
        
        # Get execution history (optional)
        print("\n" + "="*70)
        response = input("\nShow detailed execution history? (y/n): ").strip().lower()
        if response == 'y':
            get_execution_history(sfn_client, execution_arn)
        
        print("\n" + "="*70)
        print("Test completed!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

