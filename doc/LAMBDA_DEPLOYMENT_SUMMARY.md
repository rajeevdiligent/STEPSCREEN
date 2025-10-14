# AWS Lambda Deployment Summary

**Deployment Date**: October 13, 2025  
**AWS Account**: 891067072053  
**Region**: us-east-1  
**Profile**: diligent  

---

## ✅ Deployed Lambda Functions

### 1. NovaSECExtractor
**Purpose**: Extracts company information from SEC filings using AWS Nova Pro

- **ARN**: `arn:aws:lambda:us-east-1:891067072053:function:NovaSECExtractor`
- **Runtime**: Python 3.11
- **Memory**: 2048 MB
- **Timeout**: 900 seconds (15 minutes)
- **Handler**: `lambda_handler.lambda_handler`
- **Package Size**: 16.52 MB
- **IAM Role**: NovaSECExtractorRole
- **Permissions**: 
  - AWSLambdaBasicExecutionRole
  - AmazonBedrockFullAccess
  - AmazonDynamoDBFullAccess

**Key Features**:
- ✅ Automatic retry with 95% completeness threshold
- ✅ Extracts from SEC 10-K, 10-Q, 8-K filings
- ✅ Saves to DynamoDB (CompanySECData table)
- ✅ Returns completeness score

---

### 2. CXOWebsiteExtractor
**Purpose**: Extracts executive information from company websites using AWS Nova Pro

- **ARN**: `arn:aws:lambda:us-east-1:891067072053:function:CXOWebsiteExtractor`
- **Runtime**: Python 3.11
- **Memory**: 3008 MB
- **Timeout**: 900 seconds (15 minutes)
- **Handler**: `lambda_handler.lambda_handler`
- **Package Size**: 16.52 MB
- **IAM Role**: CXOWebsiteExtractorRole
- **Permissions**: 
  - AWSLambdaBasicExecutionRole
  - AmazonBedrockFullAccess
  - AmazonDynamoDBFullAccess

**Key Features**:
- ✅ Automatic retry with 95% completeness threshold
- ✅ Uses Serper API for web search
- ✅ Fetches full page content with BeautifulSoup
- ✅ Saves to DynamoDB (CompanyCXOData table)
- ✅ Returns completeness score

---

### 3. DynamoDBToS3Merger
**Purpose**: Merges SEC and CXO data from DynamoDB and saves to S3

- **ARN**: `arn:aws:lambda:us-east-1:891067072053:function:DynamoDBToS3Merger`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 300 seconds (5 minutes)
- **Handler**: `lambda_handler.lambda_handler`
- **Package Size**: 2.38 KB
- **IAM Role**: DynamoDBToS3MergerRole
- **Permissions**: 
  - AWSLambdaBasicExecutionRole
  - AmazonDynamoDBReadOnlyAccess
  - AmazonS3FullAccess

**Key Features**:
- ✅ Merges data by company_id
- ✅ Keeps most recent SEC data per company
- ✅ Combines all executives per company
- ✅ Saves timestamped and latest versions to S3

---

## 📊 DynamoDB Tables

### CompanySECData
- **Partition Key**: company_id (String)
- **Sort Key**: extraction_timestamp (String)
- **Billing Mode**: PAY_PER_REQUEST
- **Data**: Company information, financials, identifiers

### CompanyCXOData
- **Partition Key**: company_id (String)
- **Sort Key**: executive_id (String)
- **Billing Mode**: PAY_PER_REQUEST
- **Data**: Executive profiles, roles, background

---

## 📦 S3 Bucket

**Bucket Name**: company-sec-cxo-data-diligent
**Region**: us-east-1
**Versioning**: Enabled

**Structure**:
```
company_data/
├── merged_company_data_latest.json (always current)
├── merged_company_data_20251013_142333.json (timestamped)
└── ... (historical versions)
```

---

## 🚀 Quick Start

### Extract Data for One Company
```bash
# Step 1: Extract SEC data
aws lambda invoke --function-name NovaSECExtractor \
  --payload '{"company_name": "Intel Corporation", "stock_symbol": "INTC"}' \
  --profile diligent response.json

# Step 2: Extract CXO data
aws lambda invoke --function-name CXOWebsiteExtractor \
  --payload '{"website_url": "https://www.intel.com", "company_name": "Intel Corporation"}' \
  --profile diligent response.json

# Step 3: Merge to S3
aws lambda invoke --function-name DynamoDBToS3Merger \
  --payload '{"s3_bucket_name": "company-sec-cxo-data-diligent"}' \
  --profile diligent response.json
```

### Batch Processing Multiple Companies
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
    print(f"\n{'='*60}")
    print(f"Processing: {company['name']}")
    print(f"{'='*60}")
    
    # Extract SEC data
    print("1. Extracting SEC data...")
    lambda_client.invoke(
        FunctionName='NovaSECExtractor',
        InvocationType='Event',  # Async
        Payload=json.dumps({
            'company_name': company['name'],
            'stock_symbol': company['symbol']
        })
    )
    
    # Extract CXO data
    print("2. Extracting CXO data...")
    lambda_client.invoke(
        FunctionName='CXOWebsiteExtractor',
        InvocationType='Event',  # Async
        Payload=json.dumps({
            'website_url': company['url'],
            'company_name': company['name']
        })
    )
    
    print(f"✅ {company['name']} extraction initiated")
    time.sleep(2)  # Rate limiting

# Wait for all extractions to complete (check CloudWatch or DynamoDB)
print("\n⏳ Waiting for extractions to complete...")
time.sleep(60)  # Adjust based on needs

# Merge all data
print("\n3. Merging data to S3...")
response = lambda_client.invoke(
    FunctionName='DynamoDBToS3Merger',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        's3_bucket_name': 'company-sec-cxo-data-diligent'
    })
)

result = json.loads(response['Payload'].read())
body = json.loads(result['body'])
print(f"\n✅ Merge complete!")
print(f"   Total companies: {body['total_companies']}")
print(f"   S3 file: {body['latest_file']}")
```

---

## 💰 Cost Estimates

### Per Company Extraction
- **NovaSECExtractor**: ~$0.01-0.02
  - Lambda: ~$0.001 (execution time)
  - Bedrock Nova Pro: ~$0.01 (tokens)
  - DynamoDB: <$0.001 (writes)

- **CXOWebsiteExtractor**: ~$0.08-0.12
  - Lambda: ~$0.002 (execution time)
  - Bedrock Nova Pro: ~$0.02 (tokens)
  - Serper API: ~$0.06 (searches)
  - DynamoDB: <$0.001 (writes)

- **DynamoDBToS3Merger**: ~$0.001
  - Lambda: <$0.001 (execution time)
  - DynamoDB: <$0.001 (scans)
  - S3: <$0.001 (storage/requests)

**Total per company**: ~$0.10-0.15

---

## 📝 Deployment Files

### Lambda Handlers
- `lambda_nova_sec_handler.py` - SEC extractor handler
- `lambda_cxo_handler.py` - CXO extractor handler
- `lambda_merge_handler.py` - Merge handler

### Deployment Scripts
- `deploy_lambda_nova_sec.py` - Deploy SEC Lambda
- `deploy_lambda_cxo.py` - Deploy CXO Lambda
- `deploy_lambda_merge.py` - Deploy Merge Lambda

### Documentation
- `LAMBDA_USAGE_GUIDE.md` - Complete usage guide
- `LAMBDA_DEPLOYMENT_SUMMARY.md` - This file

### Utilities
- `clear_dynamodb_tables.py` - Clear all DynamoDB data
- `setup_dynamodb_tables.py` - Create DynamoDB tables
- `setup_s3_bucket.py` - Create S3 bucket

---

## 🔧 Monitoring & Logs

### CloudWatch Logs
```bash
# SEC Extractor
aws logs tail /aws/lambda/NovaSECExtractor --follow --profile diligent

# CXO Extractor
aws logs tail /aws/lambda/CXOWebsiteExtractor --follow --profile diligent

# Merger
aws logs tail /aws/lambda/DynamoDBToS3Merger --follow --profile diligent
```

### View Lambda Metrics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=NovaSECExtractor \
  --start-time 2025-10-13T00:00:00Z \
  --end-time 2025-10-14T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --profile diligent
```

---

## 🔄 Update Lambdas

To redeploy after code changes:

```bash
# Update SEC Extractor
python deploy_lambda_nova_sec.py

# Update CXO Extractor
python deploy_lambda_cxo.py

# Update Merger
python deploy_lambda_merge.py
```

---

## 🎯 Next Steps

1. **Schedule regular extractions**: Use EventBridge to trigger Lambda functions on a schedule
2. **Add error notifications**: Set up SNS topics for Lambda failures
3. **Implement API Gateway**: Expose Lambda functions via REST API
4. **Add Step Functions**: Orchestrate the complete workflow (SEC → CXO → Merge)
5. **Enable X-Ray tracing**: Monitor performance and debug issues

---

## 📞 Support & Troubleshooting

### Common Issues

**Lambda Timeout**:
- Increase timeout in deployment script
- Current: 900s (SEC/CXO), 300s (Merge)

**Memory Issues**:
- Increase memory allocation
- Current: 2048MB (SEC), 3008MB (CXO), 512MB (Merge)

**Permission Errors**:
- Verify IAM role has correct policies
- Check CloudWatch logs for specific errors

**API Key Errors**:
- Ensure SERPER_API_KEY is set in Lambda environment variables
- Update via AWS Console or deployment script

---

**Deployment Status**: ✅ ALL SYSTEMS OPERATIONAL

