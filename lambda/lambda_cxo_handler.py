#!/usr/bin/env python3
"""
AWS Lambda Handler for CXO Website Extractor
"""

import json
import os
import sys
from datetime import datetime
import logging
import boto3

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import the main extractor class
from cxo_website_extractor import SerperCxOSearcher, CxOResultsFormatter

def get_website_from_dynamodb(company_name, aws_profile=None):
    """Query DynamoDB to get website_url for a company"""
    try:
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
            dynamodb = session.client('dynamodb', region_name='us-east-1')
        else:
            dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        
        # Normalize company name to match company_id format (lowercase, simplified)
        # Try multiple variations
        company_ids_to_try = [
            company_name.lower().replace(' ', '').replace(',', '').replace('.', '').replace('inc', '').replace('corp', '').replace('corporation', '').strip(),
            company_name.lower().split()[0],  # First word
            company_name.lower().replace(' ', ''),  # No spaces
        ]
        
        for company_id in company_ids_to_try:
            # Query CompanySECData table for the most recent entry
            response = dynamodb.query(
                TableName='CompanySECData',
                KeyConditionExpression='company_id = :company_id',
                ExpressionAttributeValues={
                    ':company_id': {'S': company_id}
                },
                ScanIndexForward=False,  # Sort descending by timestamp
                Limit=1
            )
            
            if response['Items']:
                item = response['Items'][0]
                
                # Website URL is stored as a top-level field
                if 'website_url' in item and 'S' in item['website_url']:
                    website_url = item['website_url']['S']
                    logger.info(f"Retrieved website_url from DynamoDB using company_id '{company_id}': {website_url}")
                    return website_url
        
        logger.warning(f"No SEC data found in DynamoDB for {company_name} (tried: {company_ids_to_try})")
        return None
            
    except Exception as e:
        logger.error(f"Error querying DynamoDB: {e}")
        return None

def lambda_handler(event, context):
    """
    AWS Lambda handler for CXO website extraction
    
    Event format:
    {
        "website_url": "https://www.intel.com",
        "company_name": "Intel Corporation" (optional - if not provided, extracted from domain)
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "company_name": "...",
            "extraction_status": "success",
            "completeness": 100.0,
            "executives": [ ... ],
            "total_executives": 9
        }
    }
    """
    
    try:
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)
        
        company_name = event.get('company_name')
        website_url = event.get('website_url')
        
        # If website_url not provided, try to get it from DynamoDB
        if not website_url and company_name:
            logger.info(f"website_url not provided, querying DynamoDB for {company_name}")
            website_url = get_website_from_dynamodb(company_name)
        
        if not website_url:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: website_url',
                    'message': 'Please provide website_url in the event'
                })
            }
        
        company_name = event.get('company_name')
        
        logger.info(f"Starting Lambda extraction for: {website_url}")
        
        # Get API key from environment
        api_key = os.getenv('SERPER_API_KEY')
        if not api_key:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Configuration error',
                    'message': 'SERPER_API_KEY not configured in Lambda environment'
                })
            }
        
        # Initialize searcher
        searcher = SerperCxOSearcher(
            api_key=api_key,
            use_nova_pro=True,
            aws_profile=None  # Lambda uses IAM role, not profile
        )
        
        # Extract data
        results = searcher.search_cxo_from_website(
            website_url=website_url,
            company_name=company_name
        )
        
        # Calculate completeness
        completeness = searcher._calculate_completeness(results.executives)
        
        # Save to DynamoDB
        try:
            CxOResultsFormatter.save_to_dynamodb(results)
            logger.info(f"✅ Data saved to DynamoDB table: CompanyCXOData")
        except Exception as e:
            logger.error(f"❌ DynamoDB save failed: {e}")
            # Continue anyway to return the data
        
        # Prepare executive data (remove internal fields)
        executives_data = []
        for exec_info in results.executives:
            exec_dict = {
                'name': exec_info.name,
                'title': exec_info.title,
                'role_category': exec_info.role_category,
                'description': exec_info.description,
                'tenure': exec_info.tenure,
                'background': exec_info.background,
                'education': exec_info.education,
                'previous_roles': exec_info.previous_roles,
                'contact_info': exec_info.contact_info
            }
            executives_data.append(exec_dict)
        
        # Prepare response
        response_body = {
            'company_name': results.company_name,
            'company_website': results.company_website,
            'extraction_status': 'success',
            'completeness': completeness,
            'extraction_timestamp': results.search_timestamp,
            'extraction_method': results.extraction_method,
            'nova_pro_enhanced': results.nova_pro_enhanced,
            'executives': executives_data,
            'total_executives': results.total_executives_found,
            'search_queries_used': len(results.search_queries_used)
        }
        
        logger.info(f"✅ Extraction completed: {completeness}% complete, {len(executives_data)} executives found")
        
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
        "website_url": "https://www.intel.com",
        "company_name": "Intel Corporation"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

