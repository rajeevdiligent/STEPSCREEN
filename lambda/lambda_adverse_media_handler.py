#!/usr/bin/env python3
"""
AWS Lambda Handler for Adverse Media Scanner

This Lambda function scans for adverse media about a company using:
- Serper API for search
- AWS Nova Pro for content evaluation
- DynamoDB for storage
"""

import json
import os
import sys
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler for adverse media scanning
    
    Expected event structure:
    {
        "company_name": "Company Name",
        "years": 5  # Optional, defaults to 5
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "company_name": "Company Name",
            "adverse_items_found": 10,
            "search_timestamp": "2025-10-29T10:00:00",
            "message": "Adverse media scan completed"
        }
    }
    """
    
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)
        
        # Extract parameters
        company_name = event.get('company_name')
        years = event.get('years', 5)
        
        if not company_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: company_name'
                })
            }
        
        logger.info(f"Processing adverse media scan for: {company_name} (last {years} years)")
        
        # Import the adverse media scanner
        # Add parent directory to path to import the scanner
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from adverse_media_scanner import SerperAdverseMediaSearcher, AdverseMediaDynamoDBSaver
        
        # Get API keys from environment
        serper_api_key = os.environ.get('SERPER_API_KEY')
        if not serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        # Initialize searcher (no AWS profile needed in Lambda)
        searcher = SerperAdverseMediaSearcher(
            api_key=serper_api_key,
            aws_profile=None  # Lambda uses IAM role
        )
        
        # Perform adverse media search
        results = searcher.search_adverse_media(company_name, years=years)
        
        # Save to DynamoDB if adverse items found
        if results.adverse_items_found > 0:
            logger.info(f"Saving {results.adverse_items_found} adverse items to DynamoDB")
            AdverseMediaDynamoDBSaver.save_to_dynamodb(results, aws_profile=None)
        else:
            logger.info("No adverse media found - skipping DynamoDB save")
        
        # Prepare response
        response_body = {
            'company_name': results.company_name,
            'adverse_items_found': results.adverse_items_found,
            'total_articles_scanned': results.total_articles_scanned,
            'search_period_start': results.search_period_start,
            'search_period_end': results.search_period_end,
            'search_timestamp': results.search_timestamp,
            'message': f"Adverse media scan completed. Found {results.adverse_items_found} adverse items.",
            'adverse_items': [
                {
                    'title': item.title,
                    'source': item.source,
                    'url': item.url,
                    'published_date': item.published_date,
                    'adverse_category': item.adverse_category,
                    'severity_score': float(item.severity_score),
                    'confidence_score': float(item.confidence_score),
                    'description': item.description[:200] + '...' if len(item.description) > 200 else item.description
                }
                for item in results.adverse_items[:10]  # Return top 10 items
            ]
        }
        
        logger.info(f"Successfully completed adverse media scan for {company_name}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, indent=2)
        }
        
    except Exception as e:
        logger.error(f"Error in adverse media scan: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to complete adverse media scan'
            })
        }


def test_locally():
    """Test the Lambda function locally"""
    
    # Test event
    test_event = {
        'company_name': 'Wells Fargo',
        'years': 5
    }
    
    # Mock context
    class MockContext:
        function_name = 'AdverseMediaScanner'
        memory_limit_in_mb = 512
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:AdverseMediaScanner'
        aws_request_id = 'test-request-id'
    
    print("Testing Lambda function locally...")
    print(f"Event: {json.dumps(test_event, indent=2)}")
    print("-" * 80)
    
    result = lambda_handler(test_event, MockContext())
    
    print("\nLambda Response:")
    print(json.dumps(json.loads(result['body']), indent=2))
    print(f"\nStatus Code: {result['statusCode']}")


if __name__ == "__main__":
    test_locally()

