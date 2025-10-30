"""
AWS Lambda Handler for Sanctions & Watchlist Screening

This Lambda function screens companies and their executives against global sanctions
and watchlists including OFAC SDN, UN Sanctions, EU Sanctions, UK HMT, FinCEN, Interpol, and PEPs.

Input Event:
{
    "company_name": "Wells Fargo"
}

Output:
{
    "statusCode": 200,
    "body": {
        "company_id": "wells_fargo",
        "company_name": "Wells Fargo",
        "total_entities_screened": 15,
        "total_matches_found": 2,
        "company_matches": [...],
        "executive_matches": [...]
    }
}
"""

import json
import logging
import os
import sys
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import the sanctions screener module
from sanctions_screener import SerperSanctionsSearcher


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal objects"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    AWS Lambda handler for Sanctions & Watchlist Screening
    
    Event format:
    {
        "company_name": "Wells Fargo"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "company_id": "wells_fargo",
            "company_name": "Wells Fargo",
            "screening_timestamp": "2025-10-29T12:00:00",
            "total_entities_screened": 15,
            "total_matches_found": 2,
            "company_matches": [ ... ],
            "executive_matches": [ ... ]
        }
    }
    """
    try:
        # Parse event
        if isinstance(event, str):
            event = json.loads(event)
        
        company_name = event.get('company_name')
        
        if not company_name:
            logger.error("Missing required parameter: company_name")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameter: company_name'})
            }
        
        logger.info(f"Starting sanctions screening for: {company_name}")
        
        # Get Serper API key
        api_key = os.getenv('SERPER_API_KEY')
        if not api_key:
            logger.error("SERPER_API_KEY not configured in environment")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'SERPER_API_KEY not configured'})
            }
        
        # Initialize screener (no AWS profile in Lambda - uses IAM role)
        screener = SerperSanctionsSearcher(api_key=api_key, aws_profile=None)
        
        # Perform sanctions screening
        result = screener.screen_company_and_executives(company_name)
        
        if not result:
            logger.error(f"Sanctions screening failed for {company_name}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Sanctions screening failed',
                    'company_name': company_name
                })
            }
        
        # Convert dataclass to dict
        from dataclasses import asdict
        
        response_body = {
            'company_id': result.company_id,
            'company_name': result.company_name,
            'screening_timestamp': result.screening_timestamp,
            'total_entities_screened': result.total_entities_screened,
            'total_matches_found': result.total_matches_found,
            'company_matches': [asdict(m) for m in result.company_matches],
            'executive_matches': [asdict(m) for m in result.executive_matches]
        }
        
        logger.info(f"Sanctions screening completed successfully: {result.total_matches_found} matches found")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to complete sanctions screening',
                'message': str(e)
            })
        }

