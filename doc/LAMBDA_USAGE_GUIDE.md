# AWS Lambda Functions - Usage Guide

## Deployed Functions

### 1. NovaSECExtractor
**Purpose**: Extract company information from SEC filings using AWS Nova Pro

**Function ARN**: `arn:aws:lambda:us-east-1:891067072053:function:NovaSECExtractor`

**Configuration**:
- Runtime: Python 3.11
- Memory: 2048 MB
- Timeout: 900 seconds (15 minutes)
- Region: us-east-1

### 2. CXOWebsiteExtractor
**Purpose**: Extract executive information from company websites using AWS Nova Pro

**Function ARN**: `arn:aws:lambda:us-east-1:891067072053:function:CXOWebsiteExtractor`

**Configuration**:
- Runtime: Python 3.11
- Memory: 3008 MB
- Timeout: 900 seconds (15 minutes)
- Region: us-east-1

### 3. DynamoDBToS3Merger
**Purpose**: Merge SEC and CXO data from DynamoDB and save to S3

**Function ARN**: `arn:aws:lambda:us-east-1:891067072053:function:DynamoDBToS3Merger`

**Configuration**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 300 seconds (5 minutes)
- Region: us-east-1

---

## How to Invoke

### Method 1: AWS CLI

#### Nova SEC Extractor
```bash
aws lambda invoke \
  --function-name NovaSECExtractor \
  --payload '{"company_name": "Intel Corporation", "stock_symbol": "INTC"}' \
  --profile diligent \
  response_sec.json

# View results
cat response_sec.json | python -m json.tool
```

#### CXO Website Extractor
```bash
aws lambda invoke \
  --function-name CXOWebsiteExtractor \
  --payload '{"website_url": "https://www.intel.com", "company_name": "Intel Corporation"}' \
  --profile diligent \
  response_cxo.json

# View results
cat response_cxo.json | python -m json.tool
```

#### DynamoDB to S3 Merger
```bash
aws lambda invoke \
  --function-name DynamoDBToS3Merger \
  --payload '{"s3_bucket_name": "company-sec-cxo-data-diligent"}' \
  --profile diligent \
  response_merge.json

# View results
cat response_merge.json | python -m json.tool
```

### Method 2: Python Boto3

```python
import boto3
import json

# Initialize Lambda client
session = boto3.Session(profile_name='diligent', region_name='us-east-1')
lambda_client = session.client('lambda')

# Invoke SEC Extractor
response = lambda_client.invoke(
    FunctionName='NovaSECExtractor',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'company_name': 'Intel Corporation',
        'stock_symbol': 'INTC'
    })
)

result = json.loads(response['Payload'].read())
body = json.loads(result['body'])
print(f"SEC Extraction: {body['extraction_status']}")
print(f"Completeness: {body['completeness']}%")

# Invoke CXO Extractor
response = lambda_client.invoke(
    FunctionName='CXOWebsiteExtractor',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'website_url': 'https://www.intel.com',
        'company_name': 'Intel Corporation'
    })
)

result = json.loads(response['Payload'].read())
body = json.loads(result['body'])
print(f"CXO Extraction: {body['extraction_status']}")
print(f"Executives found: {body['total_executives']}")

# Invoke Merger
response = lambda_client.invoke(
    FunctionName='DynamoDBToS3Merger',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        's3_bucket_name': 'company-sec-cxo-data-diligent'
    })
)

result = json.loads(response['Payload'].read())
body = json.loads(result['body'])
print(f"Merge: {body['merge_status']}")
print(f"Total companies: {body['total_companies']}")
print(f"Data file: {body['data_file']}")
```

---

## Input Formats

### NovaSECExtractor Input
```json
{
  "company_name": "Intel Corporation",
  "stock_symbol": "INTC",  // Optional
  "year": "2025 OR 2024"    // Optional, defaults to current and previous year
}
```

### CXOWebsiteExtractor Input
```json
{
  "website_url": "https://www.intel.com",
  "company_name": "Intel Corporation"  // Optional, extracted from domain if not provided
}
```

### DynamoDBToS3Merger Input
```json
{
  "s3_bucket_name": "company-sec-cxo-data-diligent"
}
```

---

## Output Formats

### NovaSECExtractor Output (Success)
```json
{
  "statusCode": 200,
  "body": {
    "company_name": "Intel Corporation",
    "extraction_status": "success",
    "completeness": 100.0,
    "extraction_timestamp": "2025-10-13T14:22:24.519605",
    "extraction_method": "Nova Pro SEC Analysis",
    "company_information": {
      "registered_legal_name": "Intel Corporation",
      "country_of_incorporation": "United States",
      "incorporation_date": "July 18, 1968",
      "registered_business_address": "2200 Mission College Blvd, Santa Clara, CA 95054",
      "company_identifiers": {
        "CIK": "0000050863",
        "LEI": "549300Z1ONE5ODC8E083",
        ...
      },
      "business_description": "...",
      "number_of_employees": "131,900",
      "annual_revenue": "$54.2 billion",
      "annual_sales": "$54.2 billion",
      "website_url": "https://www.intel.com"
    },
    "sec_documents_found": 10,
    "search_focus": "Latest 10-K Documents (2025 OR 2024)"
  }
}
```

### CXOWebsiteExtractor Output (Success)
```json
{
  "statusCode": 200,
  "body": {
    "company_name": "Intel Corporation",
    "company_website": "https://www.intel.com",
    "extraction_status": "success",
    "completeness": 100.0,
    "extraction_timestamp": "2025-10-13 14:23:12",
    "extraction_method": "nova_pro",
    "nova_pro_enhanced": true,
    "executives": [
      {
        "name": "Lip-Bu Tan",
        "title": "Chief Executive Officer",
        "role_category": "CEO",
        "description": "...",
        "tenure": "September 2023 - Present",
        "background": "...",
        "education": "...",
        "previous_roles": [...],
        "contact_info": {}
      }
      // ... more executives
    ],
    "total_executives": 9,
    "search_queries_used": 15
  }
}
```

### DynamoDBToS3Merger Output (Success)
```json
{
  "statusCode": 200,
  "body": {
    "merge_status": "success",
    "total_companies": 10,
    "data_file": "s3://company-sec-cxo-data-diligent/company_data/merged_company_data_20251013_142333.json",
    "latest_file": "s3://company-sec-cxo-data-diligent/company_data/merged_company_data_latest.json",
    "timestamp": "20251013_142333"
  }
}
```

---

## Data Storage

Both Lambda functions automatically save extracted data to DynamoDB:

### CompanySECData Table
- **Partition Key**: `company_id` (e.g., "intel_corporation")
- **Sort Key**: `extraction_timestamp`
- Contains: Company information, financial data, identifiers

### CompanyCXOData Table
- **Partition Key**: `company_id` (e.g., "intel_corporation")
- **Sort Key**: `executive_id`
- Contains: Executive profiles, roles, background information

---

## Batch Processing Example

Process multiple companies:

```python
import boto3
import json
import time

session = boto3.Session(profile_name='diligent', region_name='us-east-1')
lambda_client = session.client('lambda')

companies = [
    {"name": "Intel Corporation", "url": "https://www.intel.com", "symbol": "INTC"},
    {"name": "Apple Inc", "url": "https://www.apple.com", "symbol": "AAPL"},
    {"name": "Netflix Inc", "url": "https://www.netflix.com", "symbol": "NFLX"}
]

for company in companies:
    print(f"\nProcessing {company['name']}...")
    
    # Extract SEC data
    sec_response = lambda_client.invoke(
        FunctionName='NovaSECExtractor',
        InvocationType='RequestResponse',
        Payload=json.dumps({
            'company_name': company['name'],
            'stock_symbol': company['symbol']
        })
    )
    
    # Extract CXO data
    cxo_response = lambda_client.invoke(
        FunctionName='CXOWebsiteExtractor',
        InvocationType='RequestResponse',
        Payload=json.dumps({
            'website_url': company['url'],
            'company_name': company['name']
        })
    )
    
    print(f"✅ {company['name']} processed")
    time.sleep(5)  # Rate limiting
```

---

## Monitoring & Logs

View Lambda execution logs:

```bash
# SEC Extractor logs
aws logs tail /aws/lambda/NovaSECExtractor --follow --profile diligent

# CXO Extractor logs
aws logs tail /aws/lambda/CXOWebsiteExtractor --follow --profile diligent
```

---

## Cost Considerations

- **Lambda Execution**: Billed per millisecond of execution time
- **AWS Bedrock (Nova Pro)**: Billed per input/output tokens
- **Serper API**: $5 per 1000 searches (for CXO extractor)
- **DynamoDB**: Pay-per-request billing mode

Estimated cost per extraction:
- SEC Extractor: ~$0.01-0.02 per company
- CXO Extractor: ~$0.08-0.12 per company (includes Serper API)

---

## Troubleshooting

### Common Issues

1. **Timeout errors**: Increase Lambda timeout (max 15 minutes)
2. **Memory errors**: Increase Lambda memory allocation
3. **API key errors**: Verify SERPER_API_KEY environment variable is set
4. **Permission errors**: Verify IAM role has Bedrock, DynamoDB access

### Check Function Configuration

```bash
aws lambda get-function-configuration \
  --function-name NovaSECExtractor \
  --profile diligent
```

---

## Updating Lambda Functions

To redeploy after code changes:

```bash
# Update SEC Extractor
python deploy_lambda_nova_sec.py

# Update CXO Extractor
python deploy_lambda_cxo.py
```

---

## Complete Workflow Example

### Step 1: Extract SEC Data
```bash
aws lambda invoke --function-name NovaSECExtractor \
  --payload '{"company_name": "Intel Corporation", "stock_symbol": "INTC"}' \
  --profile diligent response.json
```

### Step 2: Extract CXO Data
```bash
aws lambda invoke --function-name CXOWebsiteExtractor \
  --payload '{"website_url": "https://www.intel.com", "company_name": "Intel Corporation"}' \
  --profile diligent response.json
```

### Step 3: Merge and Save to S3
```bash
aws lambda invoke --function-name DynamoDBToS3Merger \
  --payload '{"s3_bucket_name": "company-sec-cxo-data-diligent"}' \
  --profile diligent response.json
```

This complete workflow:
1. Extracts SEC filing data → Saves to CompanySECData table
2. Extracts executive data → Saves to CompanyCXOData table
3. Merges both datasets by company_id → Saves to S3 bucket

