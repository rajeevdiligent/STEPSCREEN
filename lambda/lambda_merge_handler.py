#!/usr/bin/env python3
"""
AWS Lambda Handler for DynamoDB to S3 Merger
"""

import json
import boto3
from datetime import datetime
import logging
from decimal import Decimal

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

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
        self.private_table_name = 'CompanyPrivateData'
        self.adverse_table_name = 'CompanyAdverseMedia'
        self.sanctions_table_name = 'CompanySanctionsScreening'

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
        """Extracts data from all DynamoDB tables (SEC, CXO, Adverse Media, Sanctions).
        
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
            
            logger.info(f"⚠️  Extracting Adverse Media data for company: {company_id}...")
            adverse_data = self._query_by_company_id(self.adverse_table_name, company_id)
            logger.info(f"✅ Extracted {len(adverse_data)} adverse media items for {company_id}")
            
            logger.info(f"🛡️  Extracting Sanctions Screening data for company: {company_id}...")
            sanctions_data = self._query_by_company_id(self.sanctions_table_name, company_id)
            if sanctions_data:
                # Get only the most recent screening
                sanctions_data = [max(sanctions_data, key=lambda x: x['screening_timestamp'])]
                logger.info(f"✅ Extracted sanctions screening for {company_id}")
            else:
                logger.info(f"ℹ️  No sanctions screening data found for {company_id}")
                sanctions_data = []
        else:
            logger.info("📊 Extracting SEC data for ALL companies from DynamoDB...")
            sec_data = self._scan_table(self.sec_table_name)
            logger.info(f"✅ Extracted SEC data for {len(set(item['company_id'] for item in sec_data))} companies")

            logger.info("👥 Extracting CXO data for ALL companies from DynamoDB...")
            cxo_data = self._scan_table(self.cxo_table_name)
            logger.info(f"✅ Extracted {len(cxo_data)} executives from {len(set(item['company_id'] for item in cxo_data))} companies")
            
            logger.info("⚠️  Extracting Adverse Media data for ALL companies from DynamoDB...")
            adverse_data = self._scan_table(self.adverse_table_name)
            logger.info(f"✅ Extracted {len(adverse_data)} adverse media items from {len(set(item['company_id'] for item in adverse_data))} companies")
            
            logger.info("🛡️  Extracting Sanctions Screening data for ALL companies from DynamoDB...")
            sanctions_data = self._scan_table(self.sanctions_table_name)
            logger.info(f"✅ Extracted {len(sanctions_data)} sanctions screenings from {len(set(item['company_id'] for item in sanctions_data))} companies")
        
        return sec_data, cxo_data, adverse_data, sanctions_data

    def merge_data(self, sec_data: list, cxo_data: list, adverse_data: list, sanctions_data: list) -> dict:
        """Merges SEC, CXO, Adverse Media, and Sanctions data by company_id."""
        merged_data = {}

        # Process SEC data
        for item in sec_data:
            company_id = item['company_id']
            if company_id not in merged_data:
                merged_data[company_id] = {
                    'company_id': company_id,
                    'sec_data': {},
                    'executives': [],
                    'adverse_media': [],
                    'sanctions_screening': {}
                }
            
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
                merged_data[company_id] = {
                    'company_id': company_id,
                    'sec_data': {},
                    'executives': [],
                    'adverse_media': [],
                    'sanctions_screening': {}
                }
            
            # Remove DynamoDB-specific keys before storing
            executive_info = {k: v for k, v in item.items() if k not in ['company_id', 'executive_id', 'extraction_timestamp', 'company_name', 'company_website']}
            merged_data[company_id]['executives'].append(executive_info)
        
        # Process Adverse Media data
        for item in adverse_data:
            company_id = item['company_id']
            if company_id not in merged_data:
                merged_data[company_id] = {
                    'company_id': company_id,
                    'sec_data': {},
                    'executives': [],
                    'adverse_media': [],
                    'sanctions_screening': {}
                }
            
            # Remove DynamoDB-specific keys before storing
            adverse_info = {k: v for k, v in item.items() if k not in ['company_id', 'adverse_id']}
            merged_data[company_id]['adverse_media'].append(adverse_info)
        
        # Process Sanctions Screening data
        for item in sanctions_data:
            company_id = item['company_id']
            if company_id not in merged_data:
                merged_data[company_id] = {
                    'company_id': company_id,
                    'sec_data': {},
                    'executives': [],
                    'adverse_media': [],
                    'sanctions_screening': {}
                }
            
            # Keep the most recent sanctions screening
            current_timestamp = item.get('screening_timestamp', '')
            existing_timestamp = merged_data[company_id]['sanctions_screening'].get('screening_timestamp', '')
            
            if current_timestamp > existing_timestamp:
                # Remove DynamoDB-specific keys before storing
                sanctions_info = {k: v for k, v in item.items() if k not in ['company_id', 'screening_id']}
                merged_data[company_id]['sanctions_screening'] = sanctions_info
        
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
                Body=json.dumps(data, indent=2, ensure_ascii=False, cls=DecimalEncoder),
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
        
        sec_data, cxo_data, adverse_data, sanctions_data = self.extract_data(company_id)
        merged_data = self.merge_data(sec_data, cxo_data, adverse_data, sanctions_data)
        
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
    
    def run_private_only(self, company_name: str):
        """Extract and save only private company data to S3
        
        Args:
            company_name: Company name to extract
        """
        logger.info("======================================================================")
        logger.info("PRIVATE COMPANY DATA TO S3")
        logger.info("======================================================================")
        
        # Normalize company name to company_id
        company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
        logger.info(f"🏢 Company: {company_name} (ID: {company_id})")
        
        # Extract private company data
        private_data = self._query_by_company_id(self.private_table_name, company_id)
        
        if not private_data:
            logger.warning(f"⚠️  No private company data found for {company_name}")
            return {
                'status': 'no_data',
                'company_id': company_id,
                'company_name': company_name,
                'message': f'No data found in CompanyPrivateData table for {company_name}'
            }
        
        # Get the most recent data
        company_data = max(private_data, key=lambda x: x['extraction_timestamp'])
        
        # Prepare output data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        output_data = {
            'company_id': company_id,
            'company_name': company_name,
            'extraction_timestamp': company_data.get('extraction_timestamp', ''),
            'export_timestamp': datetime.now().isoformat(),
            'data_source': 'CompanyPrivateData',
            'private_company_data': {}
        }
        
        # Copy all private company fields
        for key, value in company_data.items():
            if key not in ['company_id', 'extraction_timestamp', 'extraction_source']:
                # Handle leadership_team JSON string
                if key == 'leadership_team' and isinstance(value, str):
                    try:
                        output_data['private_company_data'][key] = json.loads(value)
                    except:
                        output_data['private_company_data'][key] = value
                else:
                    output_data['private_company_data'][key] = value
        
        # Save to S3
        json_data = json.dumps(output_data, indent=2, ensure_ascii=False, cls=DecimalEncoder)
        
        # File naming: private_company_data/{company_name}_{timestamp}.json
        safe_company_name = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
        key_prefix = 'private_company_data'
        s3_key_timestamped = f"{key_prefix}/{safe_company_name}_{timestamp}.json"
        s3_key_latest = f"{key_prefix}/{safe_company_name}_latest.json"
        
        # Upload timestamped version
        self.s3_client.put_object(
            Bucket=self.s3_bucket_name,
            Key=s3_key_timestamped,
            Body=json_data.encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'company_name': company_name,
                'company_id': company_id,
                'extraction_timestamp': company_data.get('extraction_timestamp', ''),
                'export_timestamp': datetime.now().isoformat(),
                'source': 'private_company_extractor'
            }
        )
        
        logger.info(f"✅ Private company data saved: s3://{self.s3_bucket_name}/{s3_key_timestamped}")
        
        # Upload latest version
        self.s3_client.put_object(
            Bucket=self.s3_bucket_name,
            Key=s3_key_latest,
            Body=json_data.encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'company_name': company_name,
                'company_id': company_id,
                'extraction_timestamp': company_data.get('extraction_timestamp', ''),
                'export_timestamp': datetime.now().isoformat(),
                'source': 'private_company_extractor'
            }
        )
        
        logger.info(f"✅ Latest version saved: s3://{self.s3_bucket_name}/{s3_key_latest}")
        
        logger.info("======================================================================")
        logger.info("✅ PRIVATE COMPANY DATA EXPORT COMPLETE")
        logger.info("======================================================================")
        logger.info(f"🏢 Company: {company_name}")
        logger.info(f"📁 Timestamped File: {s3_key_timestamped}")
        logger.info(f"📁 Latest File: {s3_key_latest}")
        logger.info("======================================================================")
        
        return {
            'status': 'success',
            'company_id': company_id,
            'company_name': company_name,
            's3_url_timestamped': f"s3://{self.s3_bucket_name}/{s3_key_timestamped}",
            's3_url_latest': f"s3://{self.s3_bucket_name}/{s3_key_latest}",
            'extraction_timestamp': company_data.get('extraction_timestamp', ''),
            'export_timestamp': datetime.now().isoformat()
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for DynamoDB to S3 merger
    
    Event format:
    Standard Merge (SEC + CXO + Adverse Media + Sanctions):
    {
        "s3_bucket_name": "company-sec-cxo-data-diligent",
        "company_name": "Apple Inc" (optional - if provided, only merge this company)
    }
    
    Private Company Only:
    {
        "s3_bucket_name": "company-sec-cxo-data-diligent",
        "company_name": "SpaceX",
        "private_only": true
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
        
        # Check if private_only mode
        private_only = event.get('private_only', False)
        company_name = event.get('company_name')
        
        # Initialize merger
        merger = DynamoDBS3Merger(s3_bucket_name)
        
        if private_only:
            # Private company only mode
            if not company_name:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: company_name',
                        'message': 'company_name is required for private_only mode'
                    })
                }
            
            logger.info(f"🏢 Starting PRIVATE ONLY export for: {company_name}")
            result = merger.run_private_only(company_name)
            
            if result['status'] == 'no_data':
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'No data found',
                        'message': result['message'],
                        'company_name': company_name
                    })
                }
            
            # Prepare response
            response_body = {
                'export_status': 'success',
                'company_name': result['company_name'],
                'company_id': result['company_id'],
                'data_file_timestamped': result['s3_url_timestamped'],
                'data_file_latest': result['s3_url_latest'],
                'extraction_timestamp': result['extraction_timestamp'],
                'export_timestamp': result['export_timestamp']
            }
            
            logger.info(f"✅ Private company export completed for {company_name}")
            
        else:
            # Standard merge mode (SEC + CXO)
            company_id = None
            if company_name:
                # Convert to company_id format (same normalization as extractors)
                company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
                logger.info(f"Starting merge for specific company: {company_name} (ID: {company_id})")
            else:
                logger.info(f"Starting merge for ALL companies in S3 bucket: {s3_bucket_name}")
            
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
            'body': json.dumps(response_body, cls=DecimalEncoder, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            }, cls=DecimalEncoder)
        }


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "s3_bucket_name": "company-sec-cxo-data-diligent"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

