#!/usr/bin/env python3
"""
AWS Lambda Handler for Private Company Data Extractor

This Lambda function extracts private company data using Nova Pro AI and saves to DynamoDB.
"""

import json
import os
import sys
import logging
from datetime import datetime

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import the main extractor class
from private_company_extractor import PrivateCompanyExtractor

def lambda_handler(event, context):
    """
    Lambda handler function for private company data extraction
    
    Expected event format:
    {
        "company_name": "SpaceX"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "company_name": "SpaceX",
            "company_id": "spacex",
            "extraction_timestamp": "2025-10-14T13:37:07.011972",
            "completeness": "100.0%",
            "completeness_status": "Excellent",
            "message": "Data extracted and saved to DynamoDB successfully"
        }
    }
    """
    try:
        # Extract company name from event
        company_name = event.get('company_name')
        
        if not company_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: company_name'
                })
            }
        
        logger.info(f"Starting private company extraction for: {company_name}")
        
        # Initialize extractor
        extractor = PrivateCompanyExtractor()
        
        # Extract company data
        results = extractor.extract_company_data(company_name)
        
        # Get metadata
        metadata = results.get('extraction_metadata', {})
        completeness_pct = metadata.get('completeness_percentage', 'N/A')
        completeness_status = metadata.get('completeness_status', 'N/A')
        
        # Prepare response
        company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
        
        response = {
            'statusCode': 200,
            'body': {
                'company_name': company_name,
                'company_id': company_id,
                'extraction_timestamp': metadata.get('search_timestamp', datetime.now().isoformat()),
                'completeness': completeness_pct,
                'completeness_status': completeness_status,
                'total_results_found': metadata.get('total_results_found', 0),
                'sources_searched': metadata.get('sources_searched', []),
                'message': 'Data extracted and saved to DynamoDB successfully'
            }
        }
        
        logger.info(f"✅ Successfully extracted data for {company_name}")
        logger.info(f"   Completeness: {completeness_pct}")
        logger.info(f"   Status: {completeness_status}")
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in private company extraction: {str(e)}", exc_info=True)
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
        'company_name': 'SpaceX'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

