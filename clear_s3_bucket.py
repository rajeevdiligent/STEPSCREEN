#!/usr/bin/env python3
"""
Script to clear all data from S3 bucket
"""

import boto3
from botocore.exceptions import ClientError
import sys

def clear_s3_bucket(bucket_name: str, profile_name: str = 'diligent', region_name: str = 'us-east-1'):
    """Clear all objects from an S3 bucket"""
    try:
        # Initialize S3 client
        session = boto3.Session(profile_name=profile_name)
        s3 = session.client('s3', region_name=region_name)
        
        print(f"\n🔍 Scanning bucket: {bucket_name}")
        
        # List all objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])
        
        if not objects_to_delete:
            print(f"   ℹ️  Bucket is already empty (0 objects)")
            return 0
        
        print(f"   📊 Found {len(objects_to_delete)} objects to delete")
        
        # Delete objects in batches (S3 allows up to 1000 objects per delete request)
        deleted_count = 0
        batch_size = 1000
        
        for i in range(0, len(objects_to_delete), batch_size):
            batch = objects_to_delete[i:i + batch_size]
            
            # Delete batch
            response = s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': batch}
            )
            
            deleted_count += len(response.get('Deleted', []))
            print(f"   🗑️  Deleted {deleted_count}/{len(objects_to_delete)} objects...", end='\r')
        
        print(f"   ✅ Successfully deleted {deleted_count} objects" + " " * 20)
        return deleted_count
        
    except ClientError as e:
        print(f"   ❌ Error accessing bucket '{bucket_name}': {e}")
        return 0
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return 0


def clear_local_folder(folder_path: str):
    """Clear all files from local s3output folder"""
    import os
    import shutil
    
    try:
        if not os.path.exists(folder_path):
            print(f"   ℹ️  Folder does not exist: {folder_path}")
            return 0
        
        print(f"\n🔍 Scanning local folder: {folder_path}")
        
        # Count files
        file_count = 0
        for root, dirs, files in os.walk(folder_path):
            file_count += len(files)
        
        if file_count == 0:
            print(f"   ℹ️  Folder is already empty (0 files)")
            return 0
        
        print(f"   📊 Found {file_count} files to delete")
        
        # Delete all contents
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        print(f"   ✅ Successfully deleted {file_count} files")
        return file_count
        
    except Exception as e:
        print(f"   ❌ Error clearing local folder: {e}")
        return 0


def main():
    """Main function to clear S3 bucket and local folder"""
    
    print("=" * 70)
    print("S3 Bucket and Local Folder Cleanup")
    print("=" * 70)
    
    # Check for --yes flag
    skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv
    
    # Confirmation prompt
    print("\n⚠️  WARNING: This will delete ALL data from:")
    print("   - S3 Bucket: company-data-extraction-bucket")
    print("   - Local Folder: s3output/")
    print("\nThis action cannot be undone!")
    
    if not skip_confirmation:
        response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\n❌ Operation cancelled")
            sys.exit(0)
    else:
        print("\n✅ Auto-confirmed with --yes flag")
    
    bucket_name = 'company-data-extraction-bucket'
    profile_name = 'diligent'
    region_name = 'us-east-1'
    
    print(f"\n✅ Connected to AWS S3 (Profile: {profile_name}, Region: {region_name})")
    print("\n" + "-" * 70)
    
    # Clear S3 bucket
    print("1️⃣  Clearing S3 Bucket...")
    s3_deleted = clear_s3_bucket(bucket_name, profile_name, region_name)
    
    # Clear local folder
    print("\n2️⃣  Clearing Local s3output Folder...")
    local_deleted = clear_local_folder('s3output/company_data')
    
    print("\n" + "=" * 70)
    print("Cleanup Complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   S3 Bucket Objects: {s3_deleted} deleted")
    print(f"   Local Files: {local_deleted} deleted")
    print(f"   Total: {s3_deleted + local_deleted} items deleted")
    print("\n✅ S3 bucket and local folder are now empty")
    print("=" * 70)


if __name__ == "__main__":
    main()
