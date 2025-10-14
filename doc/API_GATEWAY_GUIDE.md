# API Gateway Usage Guide

**Service:** Company Data Extraction API  
**Endpoint:** `https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract`  
**Method:** POST  
**Authentication:** None (currently public)  
**Region:** us-east-1  

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Request Format](#request-format)
3. [Response Format](#response-format)
4. [Usage Examples](#usage-examples)
5. [Monitoring Execution](#monitoring-execution)
6. [Error Handling](#error-handling)
7. [Architecture](#architecture)

---

## Quick Start

### Using curl

```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tesla Inc",
    "website_url": "https://tesla.com",
    "stock_symbol": "TSLA"
  }'
```

### Using Python (requests)

```python
import requests
import json

url = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract"

payload = {
    "company_name": "Tesla Inc",
    "website_url": "https://tesla.com",
    "stock_symbol": "TSLA"
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
```

### Using JavaScript (fetch)

```javascript
const url = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract";

const payload = {
  company_name: "Tesla Inc",
  website_url: "https://tesla.com",
  stock_symbol: "TSLA"
};

fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

---

## Request Format

### Endpoint
```
POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract
```

### Headers
```
Content-Type: application/json
```

### Body (JSON)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `company_name` | string | Yes | Full legal name of the company | "Apple Inc" |
| `website_url` | string | Yes | Company's official website URL | "https://apple.com" |
| `stock_symbol` | string | No | Stock ticker symbol (if public company) | "AAPL" |

**Example Request Body:**
```json
{
  "company_name": "Apple Inc",
  "website_url": "https://apple.com",
  "stock_symbol": "AAPL"
}
```

**For Private Companies (no stock symbol):**
```json
{
  "company_name": "SpaceX",
  "website_url": "https://spacex.com",
  "stock_symbol": ""
}
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "executionArn": "arn:aws:states:us-east-1:891067072053:execution:CompanyDataExtractionPipeline:e9b0fc3c-1411-4ccc-8564-d12278ca441e",
  "startDate": "1.760418063538E9",
  "message": "Step Function execution started successfully"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `executionArn` | string | ARN of the Step Function execution (use this to track progress) |
| `startDate` | number | Unix epoch timestamp when execution started |
| `message` | string | Confirmation message |

### Error Response (500 Internal Server Error)

```json
{
  "error": "Step Function execution failed",
  "message": "Invalid input format"
}
```

---

## Usage Examples

### Example 1: Extract Public Company Data (Tesla)

**Request:**
```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tesla Inc",
    "website_url": "https://tesla.com",
    "stock_symbol": "TSLA"
  }'
```

**Response:**
```json
{
  "executionArn": "arn:aws:states:us-east-1:891067072053:execution:CompanyDataExtractionPipeline:abc123...",
  "startDate": "1.760418063538E9",
  "message": "Step Function execution started successfully"
}
```

**Expected Execution Time:** 71-92 seconds

**Output Location:**
- S3 Bucket: `s3://company-sec-cxo-data-diligent/company_data/`
- Files:
  - `tesla_inc_20251014_103000.json` (timestamped)
  - `tesla_inc_latest.json` (always latest version)

### Example 2: Extract Public Company Data (Microsoft)

**Request:**
```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Microsoft Corporation",
    "website_url": "https://microsoft.com",
    "stock_symbol": "MSFT"
  }'
```

### Example 3: Extract Private Company Data (SpaceX)

**Request:**
```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "SpaceX",
    "website_url": "https://spacex.com",
    "stock_symbol": ""
  }'
```

**Note:** For private companies, SEC data extraction will be skipped, but CXO data will still be extracted from the website.

### Example 4: Batch Processing (Python)

```python
import requests
import json
import time

url = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract"

companies = [
    {"company_name": "Apple Inc", "website_url": "https://apple.com", "stock_symbol": "AAPL"},
    {"company_name": "Google", "website_url": "https://google.com", "stock_symbol": "GOOGL"},
    {"company_name": "Amazon", "website_url": "https://amazon.com", "stock_symbol": "AMZN"},
]

execution_arns = []

for company in companies:
    print(f"Processing: {company['company_name']}")
    
    response = requests.post(url, json=company)
    
    if response.status_code == 200:
        result = response.json()
        execution_arns.append({
            'company': company['company_name'],
            'execution_arn': result['executionArn']
        })
        print(f"  ✅ Started: {result['executionArn']}")
    else:
        print(f"  ❌ Failed: {response.text}")
    
    # Small delay to avoid rate limiting
    time.sleep(1)

print(f"\n📊 Started {len(execution_arns)} executions")
print("\nExecution ARNs:")
for item in execution_arns:
    print(f"  {item['company']}: {item['execution_arn']}")
```

---

## Monitoring Execution

### Method 1: Using AWS CLI

```bash
# Get execution details
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:us-east-1:891067072053:execution:CompanyDataExtractionPipeline:abc123..." \
  --profile diligent

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn "arn:aws:states:us-east-1:891067072053:stateMachine:CompanyDataExtractionPipeline" \
  --max-results 10 \
  --profile diligent
```

### Method 2: Using Python (boto3)

```python
import boto3
import json
import time

session = boto3.Session(profile_name='diligent')
sfn_client = session.client('stepfunctions', region_name='us-east-1')

execution_arn = "arn:aws:states:us-east-1:891067072053:execution:CompanyDataExtractionPipeline:abc123..."

# Poll for completion
while True:
    response = sfn_client.describe_execution(executionArn=execution_arn)
    status = response['status']
    
    print(f"Status: {status}")
    
    if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
        if status == 'SUCCEEDED':
            output = json.loads(response.get('output', '{}'))
            print("\n✅ Execution succeeded!")
            print(json.dumps(output, indent=2))
        else:
            print(f"\n❌ Execution {status}")
            if 'error' in response:
                print(f"Error: {response['error']}")
                print(f"Cause: {response.get('cause', 'N/A')}")
        break
    
    time.sleep(5)  # Poll every 5 seconds
```

### Method 3: AWS Console

1. Open AWS Step Functions Console:
   https://console.aws.amazon.com/states/home?region=us-east-1

2. Click on "CompanyDataExtractionPipeline"

3. View recent executions in the "Executions" tab

4. Click on an execution ARN to see detailed progress:
   - Visual workflow diagram
   - Execution event history
   - Input/Output data
   - CloudWatch logs

### Method 4: Using the Test Script

```bash
# Run the test script (includes monitoring)
python test_api_gateway.py "Tesla Inc" "https://tesla.com" "TSLA"
```

---

## Error Handling

### Common Errors

#### 1. Invalid JSON Format (400 Bad Request)

**Cause:** Malformed JSON in request body

**Solution:** Validate JSON before sending
```python
import json

payload = {...}
try:
    json_str = json.dumps(payload)
except ValueError as e:
    print(f"Invalid JSON: {e}")
```

#### 2. Missing Required Fields (500 Internal Server Error)

**Cause:** `company_name` or `website_url` not provided

**Example Error:**
```json
{
  "error": "Step Function execution failed",
  "message": "Missing required field: company_name"
}
```

**Solution:** Always provide required fields
```python
# Validate before sending
required_fields = ['company_name', 'website_url']
for field in required_fields:
    if field not in payload or not payload[field]:
        raise ValueError(f"Missing required field: {field}")
```

#### 3. Step Function Execution Timeout

**Cause:** Execution takes longer than 15 minutes (Lambda max timeout)

**Response:** Execution will fail with status "TIMED_OUT"

**Solution:**
- Check if company website is accessible
- Verify SEC documents are available
- Re-run the extraction

#### 4. Incomplete Data (< 95% completeness)

**Cause:** Extraction yields insufficient data

**Step Function Behavior:** Execution fails at "CheckExtractionResults" state

**Solution:**
- Check DynamoDB for partial data
- Re-run extraction with updated parameters
- Review completeness thresholds in Step Function definition

### Retry Strategy

The API Gateway automatically handles transient AWS service errors. For application-level errors:

```python
import requests
import time

def extract_with_retry(payload, max_retries=3):
    """Extract company data with automatic retry"""
    url = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract"
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code >= 500:
                # Server error, retry
                print(f"Server error (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                # Client error, don't retry
                print(f"Client error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"Timeout (attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
    
    return None

# Usage
result = extract_with_retry({
    "company_name": "Tesla Inc",
    "website_url": "https://tesla.com",
    "stock_symbol": "TSLA"
})
```

---

## Architecture

### Request Flow

```
User/Application
      │
      │ POST /extract
      │ {company_name, website_url, stock_symbol}
      ▼
┌─────────────────────────────────┐
│      API Gateway (REST)          │
│  https://0x2t9tdx01.execute-api │
│  .us-east-1.amazonaws.com/prod   │
└─────────────┬───────────────────┘
              │
              │ StartExecution
              ▼
┌─────────────────────────────────┐
│     Step Functions              │
│  CompanyDataExtractionPipeline  │
└─────────────┬───────────────────┘
              │
              │ Orchestrates
              ▼
┌─────────────────────────────────┐
│   3 Lambda Functions:           │
│   1. NovaSECExtractor           │
│   2. CXOWebsiteExtractor        │
│   3. DynamoDBToS3Merger         │
└─────────────┬───────────────────┘
              │
              │ Stores data
              ▼
┌─────────────────────────────────┐
│   DynamoDB Tables:              │
│   • CompanySECData              │
│   • CompanyCXOData              │
└─────────────┬───────────────────┘
              │
              │ Merged & uploaded
              ▼
┌─────────────────────────────────┐
│   S3 Bucket:                    │
│   company-sec-cxo-data-diligent │
│   /company_data/*.json          │
└─────────────────────────────────┘
```

### Integration Details

**API Gateway → Step Functions:**
- Integration Type: `AWS`
- Action: `states:StartExecution`
- Credentials: IAM Role (APIGatewayStepFunctionsRole)
- Request Template: Transforms API input to Step Function input

**Request Transformation:**
```json
{
  "input": "$util.escapeJavaScript($input.json('$'))",
  "stateMachineArn": "arn:aws:states:us-east-1:891067072053:stateMachine:CompanyDataExtractionPipeline"
}
```

**Response Transformation:**
```json
{
  "executionArn": "$input.path('$.executionArn')",
  "startDate": "$input.path('$.startDate')",
  "message": "Step Function execution started successfully"
}
```

### IAM Permissions

**API Gateway Role:**
- `states:StartExecution` on CompanyDataExtractionPipeline

**Step Function Role:**
- `lambda:InvokeFunction` on all 3 Lambda functions
- `logs:*` for CloudWatch Logs

**Lambda Role:**
- `bedrock:InvokeModel`
- `dynamodb:PutItem`, `dynamodb:Query`
- `s3:PutObject`
- `logs:*` for CloudWatch Logs

---

## Advanced Usage

### Webhook Integration

Use API Gateway to trigger extraction from external webhooks:

```python
from flask import Flask, request
import requests

app = Flask(__name__)

API_URL = "https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract"

@app.route('/webhook/extract', methods=['POST'])
def handle_webhook():
    """Webhook endpoint to trigger company data extraction"""
    data = request.json
    
    # Extract company info from webhook payload
    company_name = data.get('company_name')
    website_url = data.get('website_url')
    stock_symbol = data.get('stock_symbol', '')
    
    # Trigger extraction via API Gateway
    response = requests.post(API_URL, json={
        'company_name': company_name,
        'website_url': website_url,
        'stock_symbol': stock_symbol
    })
    
    if response.status_code == 200:
        result = response.json()
        return {
            'status': 'success',
            'execution_arn': result['executionArn']
        }, 200
    else:
        return {
            'status': 'error',
            'message': response.text
        }, 500

if __name__ == '__main__':
    app.run(port=5000)
```

### Scheduled Extraction (CloudWatch Events)

Trigger extraction on a schedule:

```bash
# Create CloudWatch Events rule
aws events put-rule \
  --name "DailyCompanyExtraction" \
  --schedule-expression "cron(0 9 * * ? *)" \
  --state ENABLED \
  --profile diligent

# Add API Gateway as target
aws events put-targets \
  --rule "DailyCompanyExtraction" \
  --targets "Id=1,Arn=arn:aws:execute-api:us-east-1:891067072053:0x2t9tdx01/prod/POST/extract,RoleArn=arn:aws:iam::891067072053:role/CloudWatchEventsRole,Input={\"company_name\":\"Apple Inc\",\"website_url\":\"https://apple.com\",\"stock_symbol\":\"AAPL\"}" \
  --profile diligent
```

---

## Rate Limits & Quotas

### API Gateway Limits
- **Requests per second:** 10,000 (default account limit)
- **Burst:** 5,000
- **Payload size:** 10 MB max

### Step Functions Limits
- **Concurrent executions:** 1,000 (default)
- **Execution history retention:** 90 days
- **Maximum execution time:** 1 year (Standard workflow)

### External API Limits
- **Serper API:** 1,000 searches/month (free tier)
- **AWS Bedrock Nova Pro:** Account-specific limits

### Best Practices
1. Don't exceed 10 requests per second to API Gateway
2. Implement exponential backoff for retries
3. Monitor Serper API usage to avoid quota exhaustion
4. Use execution caching for repeated companies (Phase 2 improvement)

---

## Monitoring & Alerts

### CloudWatch Metrics

**API Gateway Metrics:**
- `Count` - Number of API requests
- `4XXError` - Client-side errors
- `5XXError` - Server-side errors
- `Latency` - Time to respond (should be < 1s)

**Step Functions Metrics:**
- `ExecutionsStarted`
- `ExecutionsSucceeded`
- `ExecutionsFailed`
- `ExecutionTime` (should average 71-92 seconds)

### Set Up Alerts

```bash
# Create SNS topic
aws sns create-topic \
  --name CompanyExtractionAlerts \
  --profile diligent

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:891067072053:CompanyExtractionAlerts \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --profile diligent

# Create CloudWatch alarm for failed executions
aws cloudwatch put-metric-alarm \
  --alarm-name "StepFunctionFailures" \
  --alarm-description "Alert when Step Function executions fail" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:891067072053:CompanyExtractionAlerts \
  --profile diligent
```

---

## Security Considerations

### Current State (Public API)
⚠️ **Warning:** The API is currently PUBLIC (no authentication)

**Risks:**
- Anyone with the URL can trigger extractions
- Potential for abuse and cost overruns
- No access control or audit trail

### Recommended Improvements

#### Option 1: API Key Authentication

```bash
# Create API key
aws apigateway create-api-key \
  --name CompanyExtractionAPIKey \
  --enabled \
  --profile diligent

# Create usage plan
aws apigateway create-usage-plan \
  --name CompanyExtractionPlan \
  --throttle burstLimit=10,rateLimit=5 \
  --quota limit=1000,period=MONTH \
  --profile diligent

# Associate API key with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --key-type API_KEY \
  --profile diligent
```

**Usage with API Key:**
```bash
curl -X POST https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"company_name": "Tesla Inc", "website_url": "https://tesla.com", "stock_symbol": "TSLA"}'
```

#### Option 2: AWS IAM Authentication

Configure API Gateway to require AWS IAM credentials (AWS_IAM authorizer).

#### Option 3: Lambda Authorizer

Create custom authorization logic with a Lambda function.

---

## Troubleshooting

### Problem: API returns 403 Forbidden

**Cause:** IAM role permissions issue

**Solution:**
```bash
# Verify API Gateway role has Step Functions permissions
aws iam get-role-policy \
  --role-name APIGatewayStepFunctionsRole \
  --policy-name InvokeStepFunctionsPolicy \
  --profile diligent
```

### Problem: Step Function execution fails immediately

**Cause:** Lambda function not found or not accessible

**Solution:**
```bash
# Verify Lambda functions exist
aws lambda list-functions \
  --query "Functions[?contains(FunctionName, 'Extractor')].FunctionName" \
  --profile diligent

# Check Step Function IAM role
aws iam get-role-policy \
  --role-name CompanyDataExtractionStepFunctionRole \
  --policy-name InvokeStepFunctionsPolicy \
  --profile diligent
```

### Problem: Execution completes but no S3 files

**Cause:** S3 bucket permissions or merge Lambda failure

**Solution:**
```bash
# Check S3 bucket
aws s3 ls s3://company-sec-cxo-data-diligent/company_data/ --profile diligent

# Check merge Lambda logs
aws logs tail /aws/lambda/DynamoDBToS3Merger --follow --profile diligent
```

---

## Cost Estimation

### Per Execution Cost

| Component | Cost | Notes |
|-----------|------|-------|
| API Gateway | $0.0000035 | Per request |
| Step Functions | $0.0002 | Per state transition (8 states) |
| Lambda (3 functions) | $0.0024 | Compute + requests |
| Serper API | $0.044 | 2 searches @ $0.022 each |
| Bedrock Nova Pro | $0.06 | 2 extractions @ $0.03 each |
| DynamoDB | $0.0001 | Writes/reads |
| S3 | $0.0000 | Negligible |
| **Total** | **~$0.11** | **Per company extraction** |

### Monthly Cost (1000 companies)

- **Total:** ~$110/month
- **AWS Services:** ~$7/month
- **External APIs:** ~$103/month

### Cost Optimization Tips

1. **Implement caching** (Phase 2) - Save 40-80% on repeat extractions
2. **Reduce Lambda memory** (Phase 0) - Save 25% on Lambda costs
3. **Use batch processing** (Phase 3) - Reduce Step Function costs by 90%
4. **Optimize Serper queries** - Reduce API calls

---

## Next Steps

1. **Secure the API** - Add API key or IAM authentication
2. **Set up monitoring** - Create CloudWatch alarms
3. **Implement caching** - Reduce costs for repeat extractions
4. **Add batch processing** - Process multiple companies efficiently
5. **Create dashboard** - Visualize extraction metrics
6. **Document API** - Generate OpenAPI/Swagger spec

---

## Support & Resources

### Documentation
- Main Architecture: `doc/SYSTEM_ARCHITECTURE.md`
- Improvement Plan: `doc/MASTER_IMPROVEMENT_PLAN.md`
- Production Readiness: `doc/PRODUCTION_READINESS.md`

### AWS Console Links
- **API Gateway:** https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis/0x2t9tdx01
- **Step Functions:** https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:891067072053:stateMachine:CompanyDataExtractionPipeline
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups

### Deployment Scripts
- Deploy API Gateway: `python deploy_api_gateway.py`
- Test API: `python test_api_gateway.py "Company" "URL" "Symbol"`
- Deploy Step Function: `python deploy_stepfunction.py`

---

**Document Version:** 1.0  
**Last Updated:** October 14, 2025  
**API Endpoint:** https://0x2t9tdx01.execute-api.us-east-1.amazonaws.com/prod/extract  
**Status:** Active & Functional

