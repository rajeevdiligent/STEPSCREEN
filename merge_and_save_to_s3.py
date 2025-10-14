#!/usr/bin/env python3
"""
Merge DynamoDB Data and Save to S3

This script:
1. Extracts company SEC data from CompanySECData table
2. Extracts executive CXO data from CompanyCXOData table
3. Merges the data by company_id
4. Saves the merged JSON to S3 bucket
"""

import boto3
import json
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DynamoDBToS3Merger:
    """Merge DynamoDB tables and save to S3"""
    
    def __init__(self, profile: str = 'diligent', region: str = 'us-east-1'):
        """Initialize AWS clients"""
        self.profile = profile
        self.region = region
        
        # Initialize AWS session
        session = boto3.Session(profile_name=profile)
        
        # Initialize DynamoDB resource
        self.dynamodb = session.resource('dynamodb', region_name=region)
        
        # Initialize S3 client
        self.s3_client = session.client('s3', region_name=region)
        
        logger.info(f"✅ AWS clients initialized (Profile: {profile}, Region: {region})")
    
    def extract_sec_data(self, company_id: str = None) -> Dict[str, Dict]:
        """Extract SEC data from CompanySECData table
        
        Args:
            company_id: Optional. If provided, only extract data for this specific company.
                       If None, extract all companies.
        """
        if company_id:
            logger.info(f"📊 Extracting SEC data for company: {company_id}...")
            table = self.dynamodb.Table('CompanySECData')
            
            # Query for specific company
            response = table.query(
                KeyConditionExpression='company_id = :cid',
                ExpressionAttributeValues={':cid': company_id},
                ScanIndexForward=False,  # Sort by timestamp descending
                Limit=1  # Get only the latest
            )
            
            items = response['Items']
            sec_data_by_company = {}
            if items:
                sec_data_by_company[company_id] = items[0]
                logger.info(f"✅ Extracted SEC data for {company_id}")
            else:
                logger.warning(f"⚠️  No SEC data found for {company_id}")
            
            return sec_data_by_company
        else:
            logger.info("📊 Extracting SEC data for ALL companies from DynamoDB...")
            table = self.dynamodb.Table('CompanySECData')
            
            # Scan entire table
            response = table.scan()
            items = response['Items']
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response['Items'])
            
            # Group by company_id and get the latest extraction for each company
            sec_data_by_company = {}
            for item in items:
                cid = item.get('company_id')
                timestamp = item.get('extraction_timestamp')
                
                # Keep only the latest extraction for each company
                if cid not in sec_data_by_company or \
                   timestamp > sec_data_by_company[cid].get('extraction_timestamp', ''):
                    sec_data_by_company[cid] = item
            
            logger.info(f"✅ Extracted SEC data for {len(sec_data_by_company)} companies")
            return sec_data_by_company
    
    def extract_cxo_data(self, company_id: str = None) -> Dict[str, List[Dict]]:
        """Extract CXO data from CompanyCXOData table
        
        Args:
            company_id: Optional. If provided, only extract data for this specific company.
                       If None, extract all companies.
        """
        table = self.dynamodb.Table('CompanyCXOData')
        
        if company_id:
            logger.info(f"👥 Extracting CXO data for company: {company_id}...")
            
            # Query for specific company
            response = table.query(
                KeyConditionExpression='company_id = :cid',
                ExpressionAttributeValues={':cid': company_id}
            )
            
            items = response['Items']
            logger.info(f"✅ Found {len(items)} executives for {company_id}")
        else:
            logger.info("👥 Extracting CXO data for ALL companies from DynamoDB...")
            
            # Scan entire table
            response = table.scan()
            items = response['Items']
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response['Items'])
            
            logger.info(f"✅ Found {len(items)} total executives")
        
        # Group executives by company_id
        cxo_data_by_company = defaultdict(list)
        for item in items:
            cid = item.get('company_id')
            
            # Clean up executive data (remove DynamoDB-specific fields)
            executive = {
                'name': item.get('name', ''),
                'title': item.get('title', ''),
                'role_category': item.get('role_category', ''),
                'description': item.get('description', ''),
                'tenure': item.get('tenure', ''),
                'background': item.get('background', ''),
                'education': item.get('education', ''),
                'previous_roles': item.get('previous_roles', []),
                'contact_info': item.get('contact_info', {}),
                'extraction_source': item.get('extraction_source', 'cxo_website_extractor')
            }
            
            cxo_data_by_company[cid].append(executive)
        
        total_executives = sum(len(execs) for execs in cxo_data_by_company.values())
        logger.info(f"✅ Extracted {total_executives} executives from {len(cxo_data_by_company)} companies")
        return dict(cxo_data_by_company)
    
    def merge_data(self, sec_data: Dict[str, Dict], cxo_data: Dict[str, List[Dict]]) -> List[Dict]:
        """Merge SEC and CXO data by company_id"""
        logger.info("🔄 Merging SEC and CXO data...")
        
        merged_data = []
        
        # Get all unique company IDs from both datasets
        all_company_ids = set(sec_data.keys()) | set(cxo_data.keys())
        
        for company_id in all_company_ids:
            company_record = {
                'company_id': company_id,
                'sec_data': {},
                'executives': [],
                'data_completeness': {}
            }
            
            # Add SEC data if available
            if company_id in sec_data:
                sec_item = sec_data[company_id]
                company_record['sec_data'] = {
                    'company_name': sec_item.get('company_name', ''),
                    'registered_legal_name': sec_item.get('registered_legal_name', ''),
                    'country_of_incorporation': sec_item.get('country_of_incorporation', ''),
                    'incorporation_date': sec_item.get('incorporation_date', ''),
                    'registered_business_address': sec_item.get('registered_business_address', ''),
                    'company_identifiers': sec_item.get('company_identifiers', {}),
                    'business_description': sec_item.get('business_description', ''),
                    'number_of_employees': sec_item.get('number_of_employees', ''),
                    'annual_revenue': sec_item.get('annual_revenue', ''),
                    'annual_sales': sec_item.get('annual_sales', ''),
                    'website_url': sec_item.get('website_url', ''),
                    'extraction_timestamp': sec_item.get('extraction_timestamp', '')
                }
                company_record['data_completeness']['has_sec_data'] = True
            else:
                company_record['data_completeness']['has_sec_data'] = False
            
            # Add CXO data if available
            if company_id in cxo_data:
                company_record['executives'] = cxo_data[company_id]
                company_record['data_completeness']['has_cxo_data'] = True
                company_record['data_completeness']['executive_count'] = len(cxo_data[company_id])
            else:
                company_record['data_completeness']['has_cxo_data'] = False
                company_record['data_completeness']['executive_count'] = 0
            
            merged_data.append(company_record)
        
        logger.info(f"✅ Merged data for {len(merged_data)} companies")
        return merged_data
    
    def save_to_s3(self, data: List[Dict], bucket_name: str, key_prefix: str = 'company_data') -> str:
        """Save merged data to S3 bucket"""
        logger.info(f"💾 Saving merged data to S3 bucket: {bucket_name}")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"{key_prefix}/merged_company_data_{timestamp}.json"
        
        # Convert data to JSON
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        
        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'extraction_timestamp': timestamp,
                    'record_count': str(len(data)),
                    'source': 'dynamodb_merger'
                }
            )
            
            s3_url = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"✅ Data saved to S3: {s3_url}")
            
            # Also save a "latest" version
            latest_key = f"{key_prefix}/merged_company_data_latest.json"
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=latest_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'extraction_timestamp': timestamp,
                    'record_count': str(len(data)),
                    'source': 'dynamodb_merger'
                }
            )
            logger.info(f"✅ Latest version saved: s3://{bucket_name}/{latest_key}")
            
            return s3_url
            
        except Exception as e:
            logger.error(f"❌ Error saving to S3: {e}")
            raise
    
    def save_summary_to_s3(self, data: List[Dict], bucket_name: str, key_prefix: str = 'company_data') -> str:
        """Save a summary report to S3"""
        logger.info("📋 Creating summary report...")
        
        # Generate summary statistics
        summary = {
            'generation_timestamp': datetime.now().isoformat(),
            'total_companies': len(data),
            'companies_with_sec_data': sum(1 for c in data if c['data_completeness']['has_sec_data']),
            'companies_with_cxo_data': sum(1 for c in data if c['data_completeness']['has_cxo_data']),
            'total_executives': sum(c['data_completeness']['executive_count'] for c in data),
            'company_list': []
        }
        
        # Add company-level summary
        for company in data:
            company_summary = {
                'company_id': company['company_id'],
                'company_name': company['sec_data'].get('company_name', 'N/A'),
                'has_sec_data': company['data_completeness']['has_sec_data'],
                'has_cxo_data': company['data_completeness']['has_cxo_data'],
                'executive_count': company['data_completeness']['executive_count']
            }
            summary['company_list'].append(company_summary)
        
        # Save summary to S3
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_key = f"{key_prefix}/summary_report_{timestamp}.json"
        
        json_summary = json.dumps(summary, indent=2, ensure_ascii=False)
        
        self.s3_client.put_object(
            Bucket=bucket_name,
            Key=summary_key,
            Body=json_summary.encode('utf-8'),
            ContentType='application/json'
        )
        
        logger.info(f"✅ Summary report saved: s3://{bucket_name}/{summary_key}")
        return f"s3://{bucket_name}/{summary_key}"
    
    def run(self, bucket_name: str, key_prefix: str = 'company_data'):
        """Main execution method"""
        logger.info("="*70)
        logger.info("DynamoDB to S3 Data Merger")
        logger.info("="*70)
        
        try:
            # Step 1: Extract SEC data
            sec_data = self.extract_sec_data()
            
            # Step 2: Extract CXO data
            cxo_data = self.extract_cxo_data()
            
            # Step 3: Merge data
            merged_data = self.merge_data(sec_data, cxo_data)
            
            # Step 4: Save to S3
            s3_url = self.save_to_s3(merged_data, bucket_name, key_prefix)
            
            # Step 5: Save summary report
            summary_url = self.save_summary_to_s3(merged_data, bucket_name, key_prefix)
            
            # Display results
            logger.info("\n" + "="*70)
            logger.info("✅ EXECUTION COMPLETE")
            logger.info("="*70)
            logger.info(f"📊 Total Companies: {len(merged_data)}")
            logger.info(f"📁 Data File: {s3_url}")
            logger.info(f"📋 Summary Report: {summary_url}")
            logger.info("="*70)
            
            return merged_data
            
        except Exception as e:
            logger.error(f"❌ Error during execution: {e}")
            raise


def main():
    """Main function"""
    import sys
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python merge_and_save_to_s3.py <s3_bucket_name> [key_prefix]")
        print("\nExample:")
        print("  python merge_and_save_to_s3.py my-company-data-bucket")
        print("  python merge_and_save_to_s3.py my-company-data-bucket extractions")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    key_prefix = sys.argv[2] if len(sys.argv) > 2 else 'company_data'
    
    try:
        # Initialize merger
        merger = DynamoDBToS3Merger(profile='diligent', region='us-east-1')
        
        # Run the merge and save process
        merger.run(bucket_name, key_prefix)
        
    except Exception as e:
        logger.error(f"Failed to complete operation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

