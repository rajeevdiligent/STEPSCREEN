#!/usr/bin/env python3
"""
Download files from S3 bucket to local s3output folder
"""

import boto3
import os
import json
from pathlib import Path
from datetime import datetime

def download_s3_files(bucket_name: str, prefix: str = '', output_dir: str = 's3output', profile_name: str = 'diligent'):
    """
    Download files from S3 bucket to local directory
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: Optional prefix to filter files (e.g., 'company_data/')
        output_dir: Local directory to save files
        profile_name: AWS profile name
    """
    
    # Initialize S3 client
    session = boto3.Session(profile_name=profile_name)
    s3_client = session.client('s3', region_name='us-east-1')
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print(f"Downloading files from S3 bucket: {bucket_name}")
    print("=" * 80)
    print(f"Prefix: {prefix if prefix else '(all files)'}")
    print(f"Output directory: {output_dir}")
    print()
    
    try:
        # List objects in bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        downloaded_count = 0
        total_size = 0
        
        for page in pages:
            if 'Contents' not in page:
                continue
            
            for obj in page['Contents']:
                key = obj['Key']
                size = obj['Size']
                
                # Skip if it's just a folder marker
                if key.endswith('/'):
                    continue
                
                # Create local file path maintaining S3 structure
                local_file = output_path / key
                local_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Download file
                print(f"📥 Downloading: {key}")
                print(f"   Size: {size:,} bytes")
                
                s3_client.download_file(bucket_name, key, str(local_file))
                
                downloaded_count += 1
                total_size += size
                
                print(f"   ✅ Saved to: {local_file}")
                print()
        
        print("=" * 80)
        print("Download Complete!")
        print("=" * 80)
        print(f"📊 Summary:")
        print(f"   Files downloaded: {downloaded_count}")
        print(f"   Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
        print(f"   Output directory: {output_path.absolute()}")
        print("=" * 80)
        
        return downloaded_count
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0


def list_s3_files(bucket_name: str, prefix: str = '', profile_name: str = 'diligent'):
    """
    List files in S3 bucket
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: Optional prefix to filter files
        profile_name: AWS profile name
    """
    
    # Initialize S3 client
    session = boto3.Session(profile_name=profile_name)
    s3_client = session.client('s3', region_name='us-east-1')
    
    print("=" * 80)
    print(f"Listing files in S3 bucket: {bucket_name}")
    print("=" * 80)
    print(f"Prefix: {prefix if prefix else '(all files)'}")
    print()
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            print("No files found.")
            return
        
        # Sort by last modified, newest first
        objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
        
        print(f"Found {len(objects)} files:")
        print()
        
        for obj in objects:
            key = obj['Key']
            size = obj['Size']
            modified = obj['LastModified']
            
            if key.endswith('/'):
                continue
            
            print(f"📄 {key}")
            print(f"   Size: {size:,} bytes | Modified: {modified}")
            print()
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main function"""
    
    import sys
    
    bucket_name = 'company-sec-cxo-data-diligent'
    prefix = 'company_data/'  # Only download merged company data
    output_dir = 's3output'
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            # List files only
            list_s3_files(bucket_name, prefix)
            return
        elif sys.argv[1] == '--all':
            # Download all files (no prefix filter)
            prefix = ''
    
    # Download files
    downloaded = download_s3_files(bucket_name, prefix, output_dir)
    
    if downloaded > 0:
        print(f"\n✅ Successfully downloaded {downloaded} files to {output_dir}/")
    else:
        print("\n⚠️  No files were downloaded.")


if __name__ == "__main__":
    main()

