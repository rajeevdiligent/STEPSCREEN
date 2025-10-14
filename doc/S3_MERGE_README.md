# DynamoDB to S3 Merge Script

## Overview

The `merge_and_save_to_s3.py` script extracts data from both DynamoDB tables, merges them by company, and saves the consolidated data to an S3 bucket.

## Features

✅ **Extracts SEC Data** - From `CompanySECData` table  
✅ **Extracts CXO Data** - From `CompanyCXOData` table  
✅ **Intelligent Merging** - Combines data by company_id  
✅ **S3 Storage** - Saves merged JSON to S3 bucket  
✅ **Summary Reports** - Generates analytics summary  
✅ **Version Control** - Creates timestamped + latest versions  
✅ **Data Completeness** - Tracks which companies have which data

## Prerequisites

1. **DynamoDB Tables** must exist and contain data:
   - `CompanySECData`
   - `CompanyCXOData`

2. **S3 Bucket** must be created:
   ```bash
   aws s3 mb s3://your-bucket-name --profile diligent --region us-east-1
   ```

3. **IAM Permissions** required:
   - `dynamodb:Scan`
   - `s3:PutObject`
   - `s3:GetObject`

## Usage

### Basic Usage

```bash
python merge_and_save_to_s3.py <s3_bucket_name>
```

### With Custom Prefix

```bash
python merge_and_save_to_s3.py <s3_bucket_name> <key_prefix>
```

### Examples

```bash
# Save to default prefix (company_data/)
python merge_and_save_to_s3.py my-company-data-bucket

# Save to custom prefix
python merge_and_save_to_s3.py my-company-data-bucket extractions

# Save to specific subfolder
python merge_and_save_to_s3.py my-company-data-bucket reports/2025
```

## Output Structure

### 1. Merged Data File

**Location:** `s3://{bucket}/{prefix}/merged_company_data_{timestamp}.json`

**Structure:**
```json
[
  {
    "company_id": "apple_inc",
    "sec_data": {
      "company_name": "Apple Inc",
      "registered_legal_name": "Apple Inc.",
      "country_of_incorporation": "United States",
      "incorporation_date": "January 03, 1977",
      "registered_business_address": "One Apple Park Way...",
      "company_identifiers": {
        "CIK": "0000320193",
        "DUNS": "268000088",
        "LEI": "HWUPKR0MPOU8FGXBT394",
        "CUSIP": "037833100"
      },
      "business_description": "...",
      "number_of_employees": "164,000",
      "annual_revenue": "$124.3 billion (Q1 2025)",
      "annual_sales": "$124.3 billion (Q1 2025)",
      "website_url": "https://www.apple.com",
      "extraction_timestamp": "2025-10-13T13:43:36.240Z"
    },
    "executives": [
      {
        "name": "Tim Cook",
        "title": "CEO",
        "role_category": "CEO",
        "description": "...",
        "tenure": "Since August 2011",
        "background": "...",
        "education": "...",
        "previous_roles": [...],
        "contact_info": {}
      }
    ],
    "data_completeness": {
      "has_sec_data": true,
      "has_cxo_data": true,
      "executive_count": 13
    }
  }
]
```

### 2. Latest Version

**Location:** `s3://{bucket}/{prefix}/merged_company_data_latest.json`

Always contains the most recent merge. Perfect for automated processes that need the current data.

### 3. Summary Report

**Location:** `s3://{bucket}/{prefix}/summary_report_{timestamp}.json`

**Structure:**
```json
{
  "generation_timestamp": "2025-10-13T13:50:00.000Z",
  "total_companies": 3,
  "companies_with_sec_data": 3,
  "companies_with_cxo_data": 2,
  "total_executives": 25,
  "company_list": [
    {
      "company_id": "apple_inc",
      "company_name": "Apple Inc",
      "has_sec_data": true,
      "has_cxo_data": true,
      "executive_count": 13
    }
  ]
}
```

## Workflow

```
┌─────────────────────┐
│  DynamoDB Tables    │
├─────────────────────┤
│ CompanySECData      │
│ CompanyCXOData      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Extract & Merge    │
│  (Python Script)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  S3 Bucket          │
├─────────────────────┤
│ - Merged Data       │
│ - Latest Version    │
│ - Summary Report    │
└─────────────────────┘
```

## Data Merging Logic

1. **Extract Latest SEC Data** - Gets the most recent extraction for each company
2. **Extract All Executives** - Gets all executives for each company
3. **Merge by company_id** - Combines SEC and CXO data
4. **Track Completeness** - Records which data is available
5. **Save to S3** - Stores timestamped and latest versions

## Use Cases

### 1. Data Analytics
```python
import boto3
import json

s3 = boto3.client('s3', profile_name='diligent')
response = s3.get_object(Bucket='my-bucket', Key='company_data/merged_company_data_latest.json')
data = json.loads(response['Body'].read())

# Analyze companies with complete data
complete = [c for c in data if c['data_completeness']['has_sec_data'] and c['data_completeness']['has_cxo_data']]
print(f"Companies with complete data: {len(complete)}")
```

### 2. Scheduled Exports
```bash
# Add to cron for daily exports
0 2 * * * python /path/to/merge_and_save_to_s3.py my-bucket daily_exports
```

### 3. Data Pipeline Integration
```python
# Trigger Lambda function after S3 upload
# Use S3 event notifications to process new data
```

## Error Handling

The script includes comprehensive error handling:

- ✅ **Connection Errors** - Logs AWS connection issues
- ✅ **Missing Tables** - Reports if DynamoDB tables don't exist
- ✅ **Empty Tables** - Handles tables with no data
- ✅ **S3 Permissions** - Reports upload permission issues
- ✅ **Pagination** - Handles large datasets (>1MB)

## Performance

- **Scan Operations** - Uses DynamoDB Scan with pagination
- **Memory Efficient** - Streams data to S3
- **Typical Runtime:**
  - 10 companies: ~5 seconds
  - 100 companies: ~15 seconds
  - 1000 companies: ~60 seconds

## Monitoring

### Check S3 Output

```bash
# List all merged files
aws s3 ls s3://my-bucket/company_data/ --profile diligent

# Download latest
aws s3 cp s3://my-bucket/company_data/merged_company_data_latest.json . --profile diligent

# View summary
aws s3 cp s3://my-bucket/company_data/summary_report_latest.json - --profile diligent
```

### Verify Data

```python
import json

# Load and verify
with open('merged_company_data_latest.json') as f:
    data = json.load(f)
    
print(f"Total companies: {len(data)}")
print(f"Companies: {[c['company_id'] for c in data]}")
```

## Troubleshooting

### Issue: "Table not found"
**Solution:** Run `setup_dynamodb_tables.py` first

### Issue: "Bucket does not exist"
**Solution:** Create S3 bucket:
```bash
aws s3 mb s3://my-bucket-name --profile diligent
```

### Issue: "Access Denied" to S3
**Solution:** Check IAM permissions for s3:PutObject

### Issue: "No data in tables"
**Solution:** Run extractors first:
```bash
python nova_sec_extractor.py "Apple Inc"
python cxo_website_extractor.py "https://www.apple.com"
```

## Best Practices

1. **Regular Exports** - Schedule daily/weekly exports
2. **Versioning** - Enable S3 versioning on your bucket
3. **Lifecycle Policies** - Archive old exports to Glacier
4. **Monitoring** - Set up CloudWatch alarms for failures
5. **Data Validation** - Check summary reports regularly

## Cost Estimation

**For 100 companies with 500 executives:**
- DynamoDB Scan: ~$0.01
- S3 Storage: ~$0.001/month (1MB file)
- S3 PUT: ~$0.001
- **Total: < $0.02 per export**

