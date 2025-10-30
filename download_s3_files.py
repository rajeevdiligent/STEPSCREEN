#!/usr/bin/env python3
"""
Script to download JSON files from S3 bucket to local s3output folder
"""

import boto3
import os
from pathlib import Path
from botocore.exceptions import ClientError

def download_s3_files(
    bucket_name: str,
    output_dir: str = 's3output',
    profile_name: str = 'diligent',
    region_name: str = 'us-east-1'
):
    """
    Download all JSON files from S3 bucket to local directory
    
    Args:
        bucket_name: Name of the S3 bucket
        output_dir: Local directory to save files
        profile_name: AWS profile name
        region_name: AWS region
    """
    
    print("=" * 80)
    print("📥 S3 TO LOCAL DOWNLOAD")
    print("=" * 80)
    print(f"Bucket: {bucket_name}")
    print(f"Output Directory: {output_dir}")
    print(f"AWS Profile: {profile_name}")
    print(f"Region: {region_name}")
    print()
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory ready: {output_path.absolute()}")
    print()
    
    # Initialize S3 client
    try:
        session = boto3.Session(profile_name=profile_name)
        s3_client = session.client('s3', region_name=region_name)
        print(f"✅ Connected to AWS S3")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to AWS: {e}")
        return
    
    # List all objects in bucket
    try:
        print("🔍 Scanning S3 bucket...")
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in response:
            print("📭 Bucket is empty - no files to download")
            return
        
        files = response['Contents']
        json_files = [f for f in files if f['Key'].endswith('.json')]
        
        print(f"📊 Found {len(files)} total files, {len(json_files)} JSON files")
        print()
        
        if not json_files:
            print("⚠️  No JSON files found to download")
            return
        
        print("-" * 80)
        print("📥 DOWNLOADING FILES")
        print("-" * 80)
        
        downloaded_count = 0
        total_size = 0
        
        for obj in json_files:
            s3_key = obj['Key']
            file_size = obj['Size']
            
            # Create local file path preserving folder structure
            local_file_path = output_path / s3_key
            
            # Create subdirectories if needed
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Download file
                s3_client.download_file(bucket_name, s3_key, str(local_file_path))
                
                downloaded_count += 1
                total_size += file_size
                
                size_kb = file_size / 1024
                print(f"✅ {s3_key}")
                print(f"   → {local_file_path}")
                print(f"   Size: {size_kb:.2f} KB")
                print()
                
            except ClientError as e:
                print(f"❌ Failed to download {s3_key}: {e}")
                print()
        
        print("=" * 80)
        print("DOWNLOAD COMPLETE")
        print("=" * 80)
        print(f"\n📊 Summary:")
        print(f"   Files Downloaded: {downloaded_count}/{len(json_files)}")
        print(f"   Total Size: {total_size / 1024:.2f} KB ({total_size / (1024*1024):.2f} MB)")
        print(f"   Output Location: {output_path.absolute()}")
        print()
        
        # List downloaded files by folder
        print("📂 Downloaded Files by Folder:")
        print("-" * 80)
        
        folders = {}
        for file in json_files:
            folder = file['Key'].split('/')[0] if '/' in file['Key'] else 'root'
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(file['Key'])
        
        for folder, files_list in sorted(folders.items()):
            print(f"\n{folder}/:")
            for file_key in sorted(files_list):
                filename = file_key.split('/')[-1]
                print(f"   • {filename}")
        
        print()
        print("=" * 80)
        print(f"✅ All JSON files downloaded to: {output_path.absolute()}")
        print("=" * 80)
        
    except ClientError as e:
        print(f"❌ Error accessing S3 bucket: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Main function"""
    bucket_name = 'company-sec-cxo-data-diligent'
    output_dir = 's3output'
    
    download_s3_files(
        bucket_name=bucket_name,
        output_dir=output_dir,
        profile_name='diligent',
        region_name='us-east-1'
    )


if __name__ == "__main__":
    main()

