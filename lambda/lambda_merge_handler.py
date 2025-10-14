#!/usr/bin/env python3
"""
AWS Lambda Handler for DynamoDB to S3 Merger
"""

import json
import boto3
from datetime import datetime
import logging

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DynamoDBS3Merger:
    def __init__(self, s3_bucket_name: str, region_name: str = 'us-east-1'):
        self.s3_bucket_name = s3_bucket_name
        self.region_name = region_name
        
        # Lambda uses IAM role, no profile needed
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        self.s3_client = boto3.client('s3', region_name=self.region_name)
        logger.info(f"✅ AWS clients initialized (Region: {self.region_name})")
        
        self.sec_table_name = 'CompanySECData'
        self.cxo_table_name = 'CompanyCXOData'

    def _scan_table(self, table_name: str) -> list:
        """Scans a DynamoDB table and returns all items."""
        table = self.dynamodb.Table(table_name)
        response = table.scan()
        items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        return items

    def _query_by_company_id(self, table_name: str, company_id: str) -> list:
        """Queries a DynamoDB table for a specific company_id."""
        table = self.dynamodb.Table(table_name)
        response = table.query(
            KeyConditionExpression='company_id = :cid',
            ExpressionAttributeValues={':cid': company_id}
        )
        return response['Items']

    def extract_data(self, company_id: str = None):
        """Extracts data from both DynamoDB tables.
        
        Args:
            company_id: Optional. If provided, only extract data for this specific company.
        """
        if company_id:
            logger.info(f"📊 Extracting SEC data for company: {company_id}...")
            sec_data = self._query_by_company_id(self.sec_table_name, company_id)
            if sec_data:
                # Get only the most recent extraction
                sec_data = [max(sec_data, key=lambda x: x['extraction_timestamp'])]
                logger.info(f"✅ Extracted SEC data for {company_id}")
            else:
                logger.warning(f"⚠️  No SEC data found for {company_id}")
                sec_data = []

            logger.info(f"👥 Extracting CXO data for company: {company_id}...")
            cxo_data = self._query_by_company_id(self.cxo_table_name, company_id)
            logger.info(f"✅ Extracted {len(cxo_data)} executives for {company_id}")
        else:
            logger.info("📊 Extracting SEC data for ALL companies from DynamoDB...")
            sec_data = self._scan_table(self.sec_table_name)
            logger.info(f"✅ Extracted SEC data for {len(set(item['company_id'] for item in sec_data))} companies")

            logger.info("👥 Extracting CXO data for ALL companies from DynamoDB...")
            cxo_data = self._scan_table(self.cxo_table_name)
            logger.info(f"✅ Extracted {len(cxo_data)} executives from {len(set(item['company_id'] for item in cxo_data))} companies")
        
        return sec_data, cxo_data

    def merge_data(self, sec_data: list, cxo_data: list) -> dict:
        """Merges SEC and CXO data by company_id."""
        merged_data = {}

        # Process SEC data
        for item in sec_data:
            company_id = item['company_id']
            if company_id not in merged_data:
                merged_data[company_id] = {'company_id': company_id, 'sec_data': {}, 'executives': []}
            
            # Keep the most recent SEC data for each company_id
            current_timestamp = item['extraction_timestamp']
            existing_timestamp = merged_data[company_id]['sec_data'].get('extraction_timestamp', '')
            
            if current_timestamp > existing_timestamp:
                # Remove DynamoDB-specific keys before storing
                sec_info = {k: v for k, v in item.items() if k not in ['company_id', 'extraction_timestamp']}
                merged_data[company_id]['sec_data'] = sec_info
                merged_data[company_id]['sec_data']['extraction_timestamp'] = current_timestamp

        # Process CXO data
        for item in cxo_data:
            company_id = item['company_id']
            if company_id not in merged_data:
                merged_data[company_id] = {'company_id': company_id, 'sec_data': {}, 'executives': []}
            
            # Remove DynamoDB-specific keys before storing
            executive_info = {k: v for k, v in item.items() if k not in ['company_id', 'executive_id', 'extraction_timestamp', 'company_name', 'company_website']}
            merged_data[company_id]['executives'].append(executive_info)
        
        # Clean up extraction_timestamp from sec_data before final output
        for company_id in merged_data:
            if 'extraction_timestamp' in merged_data[company_id]['sec_data']:
                del merged_data[company_id]['sec_data']['extraction_timestamp']

        logger.info(f"✅ Merged data for {len(merged_data)} companies")
        return list(merged_data.values())

    def _upload_to_s3(self, data: dict, key: str):
        """Uploads data to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket_name,
                Key=key,
                Body=json.dumps(data, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )
            logger.info(f"✅ Data saved to S3: s3://{self.s3_bucket_name}/{key}")
        except Exception as e:
            logger.error(f"❌ Error uploading to S3 key '{key}': {e}")
            raise

    def run(self, company_id: str = None):
        """Runs the full merge and save process.
        
        Args:
            company_id: Optional. If provided, only merge this specific company.
        """
        logger.info("======================================================================")
        if company_id:
            logger.info(f"DynamoDB to S3 Data Merger - Single Company: {company_id}")
        else:
            logger.info("DynamoDB to S3 Data Merger - All Companies")
        logger.info("======================================================================")
        
        sec_data, cxo_data = self.extract_data(company_id)
        merged_data = self.merge_data(sec_data, cxo_data)
        
        logger.info(f"💾 Saving merged data to S3 bucket: {self.s3_bucket_name}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build file names with company name if available
        if company_id:
            data_key = f"company_data/{company_id}_{timestamp}.json"
            latest_key = f"company_data/{company_id}_latest.json"
        else:
            data_key = f"company_data/merged_company_data_{timestamp}.json"
            latest_key = "company_data/merged_company_data_latest.json"
        
        self._upload_to_s3(merged_data, data_key)
        self._upload_to_s3(merged_data, latest_key)
        
        logger.info("======================================================================")
        logger.info("✅ EXECUTION COMPLETE")
        logger.info("======================================================================")
        logger.info(f"📊 Total Companies: {len(merged_data)}")
        logger.info(f"📁 Data File: s3://{self.s3_bucket_name}/{data_key}")
        logger.info(f"📁 Latest File: s3://{self.s3_bucket_name}/{latest_key}")
        logger.info("======================================================================")
        
        return {
            'total_companies': len(merged_data),
            'data_file': f"s3://{self.s3_bucket_name}/{data_key}",
            'latest_file': f"s3://{self.s3_bucket_name}/{latest_key}",
            'timestamp': timestamp
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for DynamoDB to S3 merger
    
    Event format:
    {
        "s3_bucket_name": "company-sec-cxo-data-diligent",
        "company_name": "Apple Inc" (optional - if provided, only merge this company)
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "merge_status": "success",
            "total_companies": 1,
            "data_file": "s3://...",
            "latest_file": "s3://...",
            "timestamp": "20251013_142333"
        }
    }
    """
    
    try:
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)
        
        s3_bucket_name = event.get('s3_bucket_name')
        if not s3_bucket_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: s3_bucket_name',
                    'message': 'Please provide s3_bucket_name in the event'
                })
            }
        
        # Get company_name if provided and convert to company_id format
        company_name = event.get('company_name')
        company_id = None
        if company_name:
            # Convert to company_id format (same normalization as extractors)
            company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
            logger.info(f"Starting merge for specific company: {company_name} (ID: {company_id})")
        else:
            logger.info(f"Starting merge for ALL companies in S3 bucket: {s3_bucket_name}")
        
        # Initialize merger
        merger = DynamoDBS3Merger(s3_bucket_name)
        
        # Run merge and save (with optional company_id filter)
        result = merger.run(company_id)
        
        # Prepare response
        response_body = {
            'merge_status': 'success',
            'total_companies': result['total_companies'],
            'data_file': result['data_file'],
            'latest_file': result['latest_file'],
            'timestamp': result['timestamp']
        }
        
        logger.info(f"✅ Merge completed: {result['total_companies']} companies")
        
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
        "s3_bucket_name": "company-sec-cxo-data-diligent"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

