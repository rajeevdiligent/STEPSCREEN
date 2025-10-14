#!/usr/bin/env python3
"""
Setup S3 Bucket for Company Data Storage

This script creates an S3 bucket for storing merged company data exports.
"""

import boto3
from botocore.exceptions import ClientError
import sys


def create_s3_bucket(bucket_name: str, profile: str = 'diligent', region: str = 'us-east-1'):
    """Create S3 bucket with proper configuration"""
    
    print("="*70)
    print("S3 Bucket Setup for Company Data")
    print("="*70)
    print()
    
    try:
        # Initialize S3 client
        session = boto3.Session(profile_name=profile)
        s3_client = session.client('s3', region_name=region)
        
        print(f"✅ Connected to AWS S3 (Profile: {profile}, Region: {region})")
        print()
        
        # Create bucket
        print(f"Creating S3 bucket: {bucket_name}")
        
        try:
            if region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            print(f"✅ Bucket '{bucket_name}' created successfully!")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"⚠️  Bucket '{bucket_name}' already exists and is owned by you")
            elif e.response['Error']['Code'] == 'BucketAlreadyExists':
                print(f"❌ Bucket '{bucket_name}' already exists (owned by someone else)")
                print(f"   Please choose a different bucket name")
                return False
            else:
                raise
        
        print()
        
        # Enable versioning (recommended)
        print("Enabling versioning...")
        try:
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print("✅ Versioning enabled")
        except Exception as e:
            print(f"⚠️  Could not enable versioning: {e}")
        
        print()
        
        # Set lifecycle policy (optional - archives old data)
        print("Setting lifecycle policy (archives data after 90 days)...")
        try:
            lifecycle_policy = {
                'Rules': [
                    {
                        'Id': 'ArchiveOldExports',
                        'Status': 'Enabled',
                        'Prefix': 'company_data/',
                        'Transitions': [
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            }
                        ]
                    }
                ]
            }
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )
            print("✅ Lifecycle policy configured")
        except Exception as e:
            print(f"⚠️  Could not set lifecycle policy: {e}")
        
        print()
        print("="*70)
        print("Setup Complete!")
        print("="*70)
        print()
        print(f"📦 Bucket Name: {bucket_name}")
        print(f"🌍 Region: {region}")
        print(f"📁 S3 URL: s3://{bucket_name}/")
        print()
        print("You can now run the merge script:")
        print(f"  python merge_and_save_to_s3.py {bucket_name}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("Usage: python setup_s3_bucket.py <bucket_name>")
        print("\nExample:")
        print("  python setup_s3_bucket.py my-company-data-bucket")
        print("\nNote: S3 bucket names must be globally unique")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    
    # Validate bucket name
    if not bucket_name.replace('-', '').replace('.', '').isalnum():
        print("❌ Invalid bucket name. Use only lowercase letters, numbers, hyphens, and periods.")
        sys.exit(1)
    
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        print("❌ Bucket name must be between 3 and 63 characters.")
        sys.exit(1)
    
    # Create bucket
    success = create_s3_bucket(bucket_name)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

