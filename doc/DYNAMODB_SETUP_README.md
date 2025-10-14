# DynamoDB Integration Guide

## Overview

Both extractors (`nova_sec_extractor.py` and `cxo_website_extractor.py`) now save data to **DynamoDB** in addition to JSON files.

## DynamoDB Tables

### 1. CompanySECData
Stores company information from SEC filings.

**Schema:**
- **Partition Key:** `company_id` (String) - Normalized company name
- **Sort Key:** `extraction_timestamp` (String) - ISO timestamp
- **Attributes:**
  - company_name
  - registered_legal_name
  - country_of_incorporation
  - incorporation_date
  - registered_business_address
  - company_identifiers (Map)
  - business_description
  - number_of_employees
  - annual_revenue
  - annual_sales
  - website_url
  - extraction_source

### 2. CompanyCXOData
Stores executive/leadership information.

**Schema:**
- **Partition Key:** `company_id` (String) - Normalized company name
- **Sort Key:** `executive_id` (String) - Unique executive identifier
- **Attributes:**
  - company_name
  - company_website
  - extraction_timestamp
  - name
  - title
  - role_category
  - description
  - tenure
  - background
  - education
  - previous_roles (List)
  - contact_info (Map)
  - extraction_source

## Setup Instructions

### Step 1: Create DynamoDB Tables

Run the setup script:

```bash
python setup_dynamodb_tables.py
```

This will create both tables with:
- **Billing Mode:** PAY_PER_REQUEST (on-demand)
- **Region:** us-east-1
- **Profile:** diligent

### Step 2: Verify Tables

Check AWS Console or use AWS CLI:

```bash
aws dynamodb list-tables --profile diligent --region us-east-1
```

### Step 3: Run Extractors

The extractors will now automatically save to both JSON files and DynamoDB:

```bash
# SEC Data Extraction
python nova_sec_extractor.py "Apple Inc"

# CXO Data Extraction
python cxo_website_extractor.py "https://www.apple.com"
```

## Data Flow

```
┌─────────────────────┐
│  Run Extractor      │
└──────────┬──────────┘
           │
           ├──────────────────────┐
           │                      │
           ▼                      ▼
  ┌────────────────┐    ┌────────────────┐
  │  Save to JSON  │    │ Save to        │
  │  (Backup)      │    │ DynamoDB       │
  └────────────────┘    └────────────────┘
```

## Query Examples

### Get all extractions for a company:

```python
import boto3

session = boto3.Session(profile_name='diligent')
dynamodb = session.resource('dynamodb', region_name='us-east-1')

# Get SEC data
table = dynamodb.Table('CompanySECData')
response = table.query(
    KeyConditionExpression='company_id = :cid',
    ExpressionAttributeValues={':cid': 'apple_inc'}
)
print(response['Items'])

# Get CXO data
table = dynamodb.Table('CompanyCXOData')
response = table.query(
    KeyConditionExpression='company_id = :cid',
    ExpressionAttributeValues={':cid': 'apple'}
)
print(response['Items'])
```

### Get latest extraction:

```python
response = table.query(
    KeyConditionExpression='company_id = :cid',
    ExpressionAttributeValues={':cid': 'apple_inc'},
    ScanIndexForward=False,  # Descending order
    Limit=1
)
latest = response['Items'][0]
```

## Features

✅ **Automatic Saving:** Data is saved to DynamoDB after each extraction
✅ **Backup:** JSON files are still created for debugging/backup
✅ **Error Handling:** If DynamoDB save fails, JSON file is still saved
✅ **Time-Series:** Multiple extractions are stored with timestamps
✅ **On-Demand Billing:** Pay only for what you use

## Troubleshooting

### Table already exists
If you see "Table already exists" error, the tables are already created. You can proceed with extractions.

### Permission errors
Ensure your AWS profile 'diligent' has DynamoDB permissions:
- `dynamodb:PutItem`
- `dynamodb:CreateTable`
- `dynamodb:DescribeTable`

### Connection errors
Check your AWS credentials:
```bash
aws configure list --profile diligent
```

## Cost Estimation

**PAY_PER_REQUEST Mode:**
- Write: $1.25 per million writes
- Read: $0.25 per million reads
- Storage: $0.25 per GB-month

**Example:**
- 100 company extractions/day
- ~1 KB per SEC record + ~1 KB per executive
- Estimated cost: < $1/month

