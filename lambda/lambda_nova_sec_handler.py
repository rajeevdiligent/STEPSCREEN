#!/usr/bin/env python3
"""
AWS Lambda Handler for Nova SEC Extractor
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import logging

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import the main extractor class
from nova_sec_extractor import NovaSECExtractor

def lambda_handler(event, context):
    """
    AWS Lambda handler for Nova SEC extraction
    
    Event format:
    {
        "company_name": "Intel Corporation",
        "stock_symbol": "INTC" (optional),
        "year": "2025 OR 2024" (optional)
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "company_name": "...",
            "extraction_status": "success",
            "completeness": 100.0,
            "data": { ... }
        }
    }
    """
    
    try:
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)
        
        company_name = event.get('company_name')
        if not company_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: company_name',
                    'message': 'Please provide company_name in the event'
                })
            }
        
        stock_symbol = event.get('stock_symbol')
        year = event.get('year')
        
        logger.info(f"Starting Lambda extraction for: {company_name}")
        
        # Initialize extractor
        extractor = NovaSECExtractor()
        
        # Disable local file saving for Lambda (only save to DynamoDB)
        extractor.output_dir = None
        
        # Extract data
        result = extractor.search_and_extract(
            company_name=company_name,
            stock_symbol=stock_symbol,
            year=year
        )
        
        # Check if extraction was successful
        if 'error' in result:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'company_name': company_name,
                    'extraction_status': 'failed',
                    'error': result['error']
                })
            }
        
        # Calculate completeness
        company_info = result.get('company_information', {})
        completeness = extractor._calculate_completeness(company_info)
        
        # Prepare response
        response_body = {
            'company_name': company_name,
            'extraction_status': 'success',
            'completeness': completeness,
            'extraction_timestamp': result.get('search_timestamp'),
            'extraction_method': result.get('extraction_method'),
            'company_information': company_info,
            'sec_documents_found': result.get('sec_documents_found', 0),
            'search_focus': result.get('search_focus')
        }
        
        logger.info(f"✅ Extraction completed: {completeness}% complete")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "company_name": "Intel Corporation",
        "stock_symbol": "INTC"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

