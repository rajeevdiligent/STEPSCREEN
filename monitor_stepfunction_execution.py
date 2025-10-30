#!/usr/bin/env python3
"""
Monitor Step Function Execution
"""

import boto3
import json
import time
import sys

def monitor_execution(sfn_client, execution_arn, max_wait_time=120):
    """Monitor a Step Function execution until completion or timeout"""
    
    print(f"Monitoring execution: {execution_arn}")
    print("-" * 80)
    
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_wait_time:
            print(f"\n⏰ Timeout reached ({max_wait_time} seconds)")
            print("Execution is still running. Check AWS Console for status.")
            break
        
        # Get execution status
        execution = sfn_client.describe_execution(executionArn=execution_arn)
        status = execution['status']
        
        print(f"\r⏳ Status: {status} | Elapsed: {int(elapsed)}s", end='', flush=True)
        
        if status == 'SUCCEEDED':
            print(f"\n\n✅ Execution SUCCEEDED!")
            print("-" * 80)
            
            output = json.loads(execution.get('output', '{}'))
            print("Output:")
            print(json.dumps(output, indent=2))
            
            return True
            
        elif status == 'FAILED':
            print(f"\n\n❌ Execution FAILED")
            print("-" * 80)
            
            if 'cause' in execution:
                print(f"Cause: {execution['cause']}")
            if 'error' in execution:
                print(f"Error: {execution['error']}")
            
            # Get execution history for more details
            history = sfn_client.get_execution_history(
                executionArn=execution_arn,
                reverseOrder=True,
                maxResults=10
            )
            
            print("\nRecent Events:")
            for event in history['events'][:5]:
                print(f"  - {event['type']}")
                if 'lambdaFunctionFailedEventDetails' in event:
                    details = event['lambdaFunctionFailedEventDetails']
                    print(f"    Cause: {details.get('cause', 'N/A')}")
            
            return False
            
        elif status == 'TIMED_OUT':
            print(f"\n\n⏰ Execution TIMED OUT")
            return False
            
        elif status == 'ABORTED':
            print(f"\n\n🛑 Execution ABORTED")
            return False
        
        time.sleep(3)  # Poll every 3 seconds
    
    return False


def main():
    """Main monitoring function"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 monitor_stepfunction_execution.py <execution_arn>")
        print("\nOr to start a new execution:")
        print("python3 monitor_stepfunction_execution.py --start '<company_name>' '<location>'")
        sys.exit(1)
    
    # Initialize AWS client
    session = boto3.Session(profile_name='diligent', region_name='us-east-1')
    sfn_client = session.client('stepfunctions')
    
    if sys.argv[1] == '--start':
        # Start a new execution
        if len(sys.argv) < 4:
            print("Error: Please provide company_name and location")
            sys.exit(1)
        
        company_name = sys.argv[2]
        location = sys.argv[3]
        
        state_machine_arn = 'arn:aws:states:us-east-1:891067072053:stateMachine:CompleteCompanyDataExtraction'
        
        print(f"Starting execution for: {company_name} ({location})")
        
        response = sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps({
                'company_name': company_name,
                'location': location
            })
        )
        
        execution_arn = response['executionArn']
        print(f"Execution ARN: {execution_arn}\n")
        
        # Wait a moment for it to start
        time.sleep(2)
        
        # Monitor the execution
        monitor_execution(sfn_client, execution_arn, max_wait_time=180)
    else:
        # Monitor existing execution
        execution_arn = sys.argv[1]
        monitor_execution(sfn_client, execution_arn, max_wait_time=180)


if __name__ == "__main__":
    main()

