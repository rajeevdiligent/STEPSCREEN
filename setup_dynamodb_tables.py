#!/usr/bin/env python3
"""
Setup DynamoDB Tables for Company Data Extraction

This script creates the necessary DynamoDB tables for storing:
1. Company SEC data
2. Company CXO/Executive data
"""

import boto3
from botocore.exceptions import ClientError

def create_sec_table(dynamodb):
    """Create table for SEC company data"""
    table_name = 'CompanySECData'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'company_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'extraction_timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'company_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'extraction_timestamp',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   Partition Key: company_id")
        print(f"   Sort Key: extraction_timestamp")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table '{table_name}' already exists")
        else:
            print(f"❌ Error creating table '{table_name}': {e}")

def create_cxo_table(dynamodb):
    """Create table for CXO/Executive data"""
    table_name = 'CompanyCXOData'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'company_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'executive_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'company_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'executive_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   Partition Key: company_id")
        print(f"   Sort Key: executive_id")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table '{table_name}' already exists")
        else:
            print(f"❌ Error creating table '{table_name}': {e}")

def create_private_company_table(dynamodb):
    """Create table for Private Company data"""
    table_name = 'CompanyPrivateData'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'company_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'extraction_timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'company_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'extraction_timestamp',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   Partition Key: company_id")
        print(f"   Sort Key: extraction_timestamp")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table '{table_name}' already exists")
        else:
            print(f"❌ Error creating table '{table_name}': {e}")

def create_adverse_media_table(dynamodb):
    """Create table for adverse media findings"""
    table_name = 'CompanyAdverseMedia'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'company_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'adverse_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'company_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'adverse_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   Partition Key: company_id")
        print(f"   Sort Key: adverse_id")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"ℹ️  Table '{table_name}' already exists")
        else:
            print(f"❌ Error creating table: {e}")

def create_source_list_table(dynamodb):
    """Create table for source list management"""
    table_name = 'sourcelist'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'source_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'source_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   Partition Key: source_id")
        print(f"   Sort Key: timestamp")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"ℹ️  Table '{table_name}' already exists")
        else:
            print(f"❌ Error creating table: {e}")

def create_sanctions_screening_table(dynamodb):
    """Create table for sanctions and watchlist screening results"""
    table_name = 'CompanySanctionsScreening'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'company_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'screening_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'company_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'screening_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"✅ Table '{table_name}' created successfully!")
        print(f"   Partition Key: company_id")
        print(f"   Sort Key: screening_id")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"ℹ️  Table '{table_name}' already exists")
        else:
            print(f"❌ Error creating table: {e}")

def main():
    """Main function to create DynamoDB tables"""
    print("="*70)
    print("DynamoDB Table Setup for Company Data Extraction")
    print("="*70)
    print()
    
    # Initialize DynamoDB resource using diligent profile
    try:
        session = boto3.Session(profile_name='diligent')
        dynamodb = session.resource('dynamodb', region_name='us-east-1')
        print(f"✅ Connected to AWS DynamoDB (Profile: diligent, Region: us-east-1)")
        print()
    except Exception as e:
        print(f"❌ Error connecting to AWS: {e}")
        return
    
    # Create tables
    print("Creating DynamoDB Tables...")
    print("-" * 70)
    
    print("\n1. Creating SEC Company Data Table...")
    create_sec_table(dynamodb)
    
    print("\n2. Creating CXO Executive Data Table...")
    create_cxo_table(dynamodb)
    
    print("\n3. Creating Private Company Data Table...")
    create_private_company_table(dynamodb)
    
    print("\n4. Creating Adverse Media Table...")
    create_adverse_media_table(dynamodb)
    
    print("\n5. Creating Source List Table...")
    create_source_list_table(dynamodb)
    
    print("\n6. Creating Sanctions Screening Table...")
    create_sanctions_screening_table(dynamodb)
    
    print("\n" + "="*70)
    print("Setup Complete!")
    print("="*70)
    print()
    print("Table Schemas:")
    print()
    print("📊 CompanySECData:")
    print("   - company_id (String) - Partition Key")
    print("   - extraction_timestamp (String) - Sort Key")
    print("   - Stores: Public company info, financials, identifiers")
    print()
    print("👥 CompanyCXOData:")
    print("   - company_id (String) - Partition Key")
    print("   - executive_id (String) - Sort Key")
    print("   - Stores: Executive profiles, roles, background")
    print()
    print("🔒 CompanyPrivateData:")
    print("   - company_id (String) - Partition Key")
    print("   - extraction_timestamp (String) - Sort Key")
    print("   - Stores: Private company info, funding, valuation, leadership")
    print()
    print("🚨 CompanyAdverseMedia:")
    print("   - company_id (String) - Partition Key")
    print("   - adverse_id (String) - Sort Key")
    print("   - Stores: Adverse media findings, severity, categories, analysis")
    print()
    print("📋 sourcelist:")
    print("   - source_id (String) - Partition Key")
    print("   - timestamp (String) - Sort Key")
    print("   - Stores: Source references, URLs, metadata, company associations")
    print()
    print("🛡️  CompanySanctionsScreening:")
    print("   - company_id (String) - Partition Key")
    print("   - screening_id (String) - Sort Key")
    print("   - Stores: Sanctions/watchlist matches, confidence levels, PEP status")
    print("   - Sources: OFAC SDN, UN, EU, UK HMT, FinCEN, Interpol, PEPs")
    print()
    print("All tables use PAY_PER_REQUEST billing mode")
    print()

if __name__ == "__main__":
    main()

