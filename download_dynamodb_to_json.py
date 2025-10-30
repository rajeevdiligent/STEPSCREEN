#!/usr/bin/env python3
"""
Download data from DynamoDB tables and save as JSON files to s3output folder
"""

import boto3
import json
import os
from datetime import datetime
from pathlib import Path
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def download_dynamodb_data(profile_name='diligent', region_name='us-east-1'):
    """
    Download data from all DynamoDB tables and save to s3output folder
    """
    print("=" * 80)
    print("DYNAMODB TO JSON EXPORTER")
    print("=" * 80)
    
    # Create output directory
    output_dir = Path('s3output/dynamodb_data')
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print()
    
    # Initialize DynamoDB
    try:
        session = boto3.Session(profile_name=profile_name)
        dynamodb = session.resource('dynamodb', region_name=region_name)
        print(f"✅ Connected to DynamoDB using profile: {profile_name}")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to DynamoDB: {e}")
        return
    
    # Define tables to export
    tables = {
        'CompanySECData': 'sec_data',
        'CompanyCXOData': 'cxo_data',
        'CompanyPrivateData': 'private_data'
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    total_items = 0
    
    for table_name, file_prefix in tables.items():
        try:
            print(f"📊 Processing table: {table_name}")
            table = dynamodb.Table(table_name)
            
            # Scan the entire table
            response = table.scan()
            items = response['Items']
            
            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response['Items'])
            
            if not items:
                print(f"   ⚠️  No data found in {table_name}")
                print()
                continue
            
            print(f"   ✅ Retrieved {len(items)} items")
            
            # Group items by company_id
            companies = {}
            for item in items:
                company_id = item.get('company_id', 'unknown')
                if company_id not in companies:
                    companies[company_id] = []
                companies[company_id].append(item)
            
            # Save each company's data to a separate file
            for company_id, company_items in companies.items():
                # Sort by extraction_timestamp to get latest
                sorted_items = sorted(
                    company_items, 
                    key=lambda x: x.get('extraction_timestamp', ''),
                    reverse=True
                )
                
                # Use the latest item
                latest_item = sorted_items[0]
                
                # Create filename
                filename = f"{file_prefix}_{company_id}_{timestamp}.json"
                filepath = output_dir / filename
                
                # Save to JSON file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(latest_item, f, indent=2, cls=DecimalEncoder, ensure_ascii=False)
                
                print(f"   💾 Saved: {filename}")
                total_items += 1
            
            print()
            
        except Exception as e:
            print(f"   ❌ Error processing {table_name}: {e}")
            print()
            continue
    
    print("=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"Total files created: {total_items}")
    print(f"Output directory: {output_dir.absolute()}")
    print()
    
    # List all created files
    if total_items > 0:
        print("Created files:")
        for file in sorted(output_dir.glob('*.json')):
            size_kb = file.stat().st_size / 1024
            print(f"  • {file.name} ({size_kb:.2f} KB)")
    
    print("=" * 80)

if __name__ == "__main__":
    download_dynamodb_data()

