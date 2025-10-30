#!/usr/bin/env python3
"""
Script to clear all data from DynamoDB tables
"""

import boto3
from botocore.exceptions import ClientError
import sys

def delete_all_items(table_name: str, profile_name: str = 'diligent', region_name: str = 'us-east-1'):
    """Delete all items from a DynamoDB table"""
    try:
        # Initialize DynamoDB resource
        session = boto3.Session(profile_name=profile_name)
        dynamodb = session.resource('dynamodb', region_name=region_name)
        table = dynamodb.Table(table_name)
        
        # Get table key schema
        table_info = table.key_schema
        key_names = [key['AttributeName'] for key in table_info]
        
        print(f"\n🔍 Scanning table: {table_name}")
        print(f"   Key fields: {', '.join(key_names)}")
        
        # Scan table to get all items
        response = table.scan()
        items = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        if not items:
            print(f"   ℹ️  Table is already empty (0 items)")
            return 0
        
        print(f"   📊 Found {len(items)} items to delete")
        
        # Delete items in batches
        deleted_count = 0
        with table.batch_writer() as batch:
            for item in items:
                # Extract only the key attributes for deletion
                key = {key_name: item[key_name] for key_name in key_names}
                batch.delete_item(Key=key)
                deleted_count += 1
                
                # Progress indicator
                if deleted_count % 10 == 0:
                    print(f"   🗑️  Deleted {deleted_count}/{len(items)} items...", end='\r')
        
        print(f"   ✅ Successfully deleted {deleted_count} items" + " " * 20)
        return deleted_count
        
    except ClientError as e:
        print(f"   ❌ Error accessing table '{table_name}': {e}")
        return 0
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return 0


def main():
    """Main function to clear all DynamoDB tables"""
    
    print("=" * 70)
    print("DynamoDB Tables Data Cleanup")
    print("=" * 70)
    
    # Check for --yes flag
    skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv
    
    # Confirmation prompt
    print("\n⚠️  WARNING: This will delete ALL data from the following tables:")
    print("   - CompanySECData")
    print("   - CompanyCXOData")
    print("   - CompanyPrivateData")
    print("   - CompanyAdverseMedia")
    print("   - CompanySanctionsScreening")
    print("\nThis action cannot be undone!")
    
    if not skip_confirmation:
        response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\n❌ Operation cancelled")
            sys.exit(0)
    else:
        print("\n✅ Auto-confirmed with --yes flag")
    
    profile_name = 'diligent'
    region_name = 'us-east-1'
    
    print(f"\n✅ Connected to AWS DynamoDB (Profile: {profile_name}, Region: {region_name})")
    print("\n" + "-" * 70)
    
    # Clear CompanySECData table
    print("1️⃣  Clearing SEC Company Data Table...")
    sec_deleted = delete_all_items('CompanySECData', profile_name, region_name)
    
    # Clear CompanyCXOData table
    print("\n2️⃣  Clearing CXO Executive Data Table...")
    cxo_deleted = delete_all_items('CompanyCXOData', profile_name, region_name)
    
    # Clear CompanyPrivateData table
    print("\n3️⃣  Clearing Private Company Data Table...")
    private_deleted = delete_all_items('CompanyPrivateData', profile_name, region_name)
    
    # Clear CompanyAdverseMedia table
    print("\n4️⃣  Clearing Adverse Media Data Table...")
    adverse_deleted = delete_all_items('CompanyAdverseMedia', profile_name, region_name)
    
    # Clear CompanySanctionsScreening table
    print("\n5️⃣  Clearing Sanctions Screening Data Table...")
    sanctions_deleted = delete_all_items('CompanySanctionsScreening', profile_name, region_name)
    
    print("\n" + "=" * 70)
    print("Cleanup Complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   CompanySECData: {sec_deleted} items deleted")
    print(f"   CompanyCXOData: {cxo_deleted} items deleted")
    print(f"   CompanyPrivateData: {private_deleted} items deleted")
    print(f"   CompanyAdverseMedia: {adverse_deleted} items deleted")
    print(f"   CompanySanctionsScreening: {sanctions_deleted} items deleted")
    print(f"   Total: {sec_deleted + cxo_deleted + private_deleted + adverse_deleted + sanctions_deleted} items deleted")
    print("\n✅ All tables are now empty and ready for new data")
    print("=" * 70)


if __name__ == "__main__":
    main()

