# STEPSCREEN - Quick Reference Card

## API Endpoints

### Standard Extraction (SEC + CXO)
```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Tesla", "website_url": "https://tesla.com", "stock_symbol": "TSLA"}'
```
- **Duration**: 71-92 seconds
- **Cost**: ~$0.16
- **Data**: SEC filings + Executives

---

### Full Extraction (SEC + CXO + Private)
```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract-private \
  -H "Content-Type: application/json" \
  -d '{"company_name": "SpaceX", "website_url": "https://spacex.com", "stock_symbol": ""}'
```
- **Duration**: 90-120 seconds
- **Cost**: ~$0.25
- **Data**: SEC + Executives + Private company data

---

## Python Usage

```python
import requests

api = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod"

# Standard
response = requests.post(f'{api}/extract', json={
    "company_name": "Tesla",
    "website_url": "https://www.tesla.com",
    "stock_symbol": "TSLA"
})

# Full (with private data)
response = requests.post(f'{api}/extract-private', json={
    "company_name": "SpaceX",
    "website_url": "https://www.spacex.com",
    "stock_symbol": ""
})

# Get execution ARN
exec_arn = response.json()['executionArn']
```

---

## System Architecture

```
API Gateway (/extract)           API Gateway (/extract-private)
       ↓                                    ↓
  Step Function                        Step Function
       ↓                                    ↓
  ┌─────────┐                    ┌──────────────────┐
  │ Parallel│                    │    Parallel      │
  │         │                    │                  │
  │  SEC    │                    │  SEC   CXO   PVT │
  │  CXO    │                    │                  │
  └─────────┘                    └──────────────────┘
       ↓                                    ↓
   DynamoDB                            DynamoDB
  (2 tables)                          (3 tables)
       ↓                                    ↓
    S3 Bucket                           S3 Bucket
```

---

## When to Use Which Endpoint?

| Scenario | Use | Why |
|----------|-----|-----|
| Public company (TSLA, AAPL) | `/extract` | Faster, cheaper, good SEC data |
| Private company (SpaceX, Stripe) | `/extract-private` | Need private data extractor |
| Maximum data completeness | `/extract-private` | Get all possible information |

---

## Quick Commands

### List executions
```bash
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:891067072053:stateMachine:CompanyDataExtractionPipeline \
  --profile diligent
```

### Check execution status
```bash
aws stepfunctions describe-execution \
  --execution-arn "EXECUTION_ARN" \
  --profile diligent
```

### View CloudWatch logs
```bash
aws logs tail /aws/lambda/NovaSECExtractor --follow --profile diligent
aws logs tail /aws/lambda/CXOWebsiteExtractor --follow --profile diligent
aws logs tail /aws/lambda/PrivateCompanyExtractor --follow --profile diligent
```

### Query DynamoDB
```python
import boto3
session = boto3.Session(profile_name='diligent')
dynamodb = session.resource('dynamodb', region_name='us-east-1')

# SEC data
table = dynamodb.Table('CompanySECData')
response = table.query(KeyConditionExpression='company_id = :cid',
                       ExpressionAttributeValues={':cid': 'tesla'})

# CXO data
table = dynamodb.Table('CompanyCXOData')
response = table.query(KeyConditionExpression='company_id = :cid',
                       ExpressionAttributeValues={':cid': 'tesla'})

# Private data
table = dynamodb.Table('CompanyPrivateData')
response = table.query(KeyConditionExpression='company_id = :cid',
                       ExpressionAttributeValues={':cid': 'spacex'})
```

### Download from S3
```bash
aws s3 cp s3://company-sec-cxo-data-diligent/company_data/tesla_latest.json . --profile diligent
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 403 Error | Wait 30-60s for API Gateway cache |
| Execution Failed | Check CloudWatch logs for specific Lambda |
| No data in DynamoDB | Verify execution succeeded, check Lambda logs |
| Slow response | Normal, extraction takes 1-2 minutes |

---

## System Status

- **Lambdas**: 4 (NovaSEC, CXO, Private, Merger)
- **Endpoints**: 2 (/extract, /extract-private)
- **DynamoDB Tables**: 3
- **S3 Bucket**: company-sec-cxo-data-diligent
- **Region**: us-east-1
- **Profile**: diligent

**All systems operational** ✅

