# AWS Step Functions - Company Data Extraction Pipeline

## Overview

This Step Functions state machine orchestrates the complete company data extraction pipeline by coordinating three Lambda functions in a specific workflow.

## Workflow Diagram

```
                    START
                      |
                      v
          ┌───────────────────────┐
          │  ParallelExtraction   │
          └───────────┬───────────┘
                      |
          ┌───────────┴───────────┐
          |                       |
          v                       v
    ┌─────────┐           ┌──────────┐
    │ Nova    │           │   CXO    │
    │  SEC    │           │ Website  │
    │Extractor│           │Extractor │
    └────┬────┘           └────┬─────┘
         |                     |
         └──────────┬──────────┘
                    v
         ┌──────────────────┐
         │ Check Results    │
         │ (Both Success?)  │
         └─────────┬────────┘
                   |
        ┌──────────┴──────────┐
        |                     |
    SUCCESS                FAILED
        |                     |
        v                     v
┌───────────────┐      ┌──────────┐
│  DynamoDB     │      │  Exit    │
│  to S3        │      │  with    │
│  Merger       │      │  Error   │
└───────┬───────┘      └──────────┘
        |
        v
  ┌─────────┐
  │ Success │
  └─────────┘
```

## State Machine Details

### 1. ParallelExtraction State
- **Type**: Parallel
- **Purpose**: Execute SEC and CXO extractions simultaneously
- **Branches**:
  - Branch 1: NovaSECExtractor Lambda
  - Branch 2: CXOWebsiteExtractor Lambda
- **Benefits**: 
  - Reduces total execution time
  - Independent failures don't block the other extraction

### 2. SEC Extraction Task
- **Lambda**: NovaSECExtractor
- **Input**: `company_name`, `stock_symbol` (optional)
- **Output**: SEC company data saved to DynamoDB
- **Retry Policy**: 2 attempts with exponential backoff
- **Error Handling**: Catches all errors and marks as failed

### 3. CXO Extraction Task
- **Lambda**: CXOWebsiteExtractor
- **Input**: `company_name`, `website_url`
- **Output**: Executive data saved to DynamoDB
- **Retry Policy**: 2 attempts with exponential backoff
- **Error Handling**: Catches all errors and marks as failed

### 4. CheckExtractionResults State
- **Type**: Choice
- **Purpose**: Verify both extractions succeeded
- **Logic**: 
  - If both return statusCode 200 → Proceed to merge
  - If either failed → Exit with error

### 5. MergeAndSaveToS3 Task
- **Lambda**: DynamoDBToS3Merger
- **Input**: S3 bucket name
- **Output**: Merged JSON files in S3
- **Retry Policy**: 2 attempts with exponential backoff

## Input Format

```json
{
  "company_name": "Apple Inc",
  "website_url": "https://www.apple.com",
  "stock_symbol": "AAPL"
}
```

**Required Fields**:
- `company_name` - Full company name
- `website_url` - Company website URL

**Optional Fields**:
- `stock_symbol` - Stock ticker symbol (helps with SEC search)

## Output Format

### Success Output
```json
{
  "extraction_results": [
    {
      "sec_result": {
        "statusCode": 200,
        "body": "{...SEC data...}"
      }
    },
    {
      "cxo_result": {
        "statusCode": 200,
        "body": "{...CXO data...}"
      }
    }
  ],
  "statusCode": 200,
  "body": "{...merge results...}",
  "status": "success",
  "message": "Company data extraction and merge completed successfully"
}
```

### Error Output
```json
{
  "Error": "ExtractionError",
  "Cause": "SEC or CXO extraction failed. Check extraction_results for details."
}
```

## Execution Time

- **SEC Extraction**: ~60-120 seconds
- **CXO Extraction**: ~45-90 seconds
- **Parallel Execution**: ~60-120 seconds (max of both)
- **Merge**: ~5-15 seconds
- **Total**: ~65-135 seconds

## Error Handling

### Retry Strategy
- **Attempts**: 2 retries per task
- **Backoff**: Exponential (2x multiplier)
- **Initial Interval**: 2 seconds

### Error Types Handled
- `States.TaskFailed` - Task execution failure
- `Lambda.ServiceException` - AWS Lambda service errors
- `Lambda.AWSLambdaException` - Lambda runtime errors
- `Lambda.SdkClientException` - SDK client errors
- `States.ALL` - Catch-all for other errors

### Graceful Degradation
- If SEC extraction fails, CXO can still succeed
- If CXO extraction fails, SEC can still succeed
- Merge only runs if both succeed
- Failed tasks provide detailed error messages

## Monitoring and Logging

### CloudWatch Logs
- **Log Group**: `/aws/stepfunctions/CompanyDataExtractionPipeline`
- **Level**: ALL
- **Includes**: Full execution data and state transitions

### Execution History
- All state transitions logged
- Task inputs and outputs captured
- Timestamps for performance analysis
- Error details for debugging

## IAM Permissions

### Step Functions Role
```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:InvokeFunction"
  ],
  "Resource": [
    "arn:aws:lambda:*:*:function:NovaSECExtractor",
    "arn:aws:lambda:*:*:function:CXOWebsiteExtractor",
    "arn:aws:lambda:*:*:function:DynamoDBToS3Merger"
  ]
}
```

## Usage Examples

### Using Python Script
```bash
# Test with Apple Inc
python test_stepfunction.py "Apple Inc" "https://www.apple.com" "AAPL"

# Test with Netflix
python test_stepfunction.py "Netflix Inc" "https://www.netflix.com" "NFLX"

# Test with Intel
python test_stepfunction.py "Intel Corporation" "https://www.intel.com" "INTC"
```

### Using AWS CLI
```bash
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --name "execution-apple-20251013" \
  --input '{"company_name":"Apple Inc","website_url":"https://www.apple.com","stock_symbol":"AAPL"}' \
  --profile diligent \
  --region us-east-1
```

### Using Boto3
```python
import boto3
import json

sfn = boto3.client('stepfunctions', region_name='us-east-1')

response = sfn.start_execution(
    stateMachineArn='<STATE_MACHINE_ARN>',
    name='execution-apple-20251013',
    input=json.dumps({
        'company_name': 'Apple Inc',
        'website_url': 'https://www.apple.com',
        'stock_symbol': 'AAPL'
    })
)
```

## Deployment

### Deploy State Machine
```bash
python deploy_stepfunction.py
```

### Update State Machine
Simply run the deployment script again - it will update the existing state machine:
```bash
python deploy_stepfunction.py
```

### Delete State Machine
```bash
aws stepfunctions delete-state-machine \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --profile diligent \
  --region us-east-1
```

## Cost Optimization

### State Transitions
- Standard Workflow: $0.025 per 1,000 state transitions
- Average execution: ~10-15 state transitions
- Cost per execution: ~$0.0004

### Lambda Invocations
- 3 Lambda functions per execution
- Cost depends on Lambda pricing
- Execution time: ~65-135 seconds total

### DynamoDB & S3
- DynamoDB: Pay per read/write
- S3: Pay per storage and requests
- Minimal costs for small datasets

## Best Practices

1. **Parallel Execution**: Always run SEC and CXO in parallel for faster results
2. **Error Handling**: Review failed executions in CloudWatch Logs
3. **Monitoring**: Set up CloudWatch alarms for failed executions
4. **Batch Processing**: Use Step Functions Map state for multiple companies
5. **Testing**: Test with known companies before production use

## Troubleshooting

### Common Issues

**Issue**: State machine not found
- **Solution**: Run `python deploy_stepfunction.py` to deploy

**Issue**: Lambda invocation fails
- **Solution**: Check Lambda function permissions and IAM role

**Issue**: Both extractions succeed but merge fails
- **Solution**: Check DynamoDB for data presence and S3 bucket permissions

**Issue**: Execution times out
- **Solution**: Increase Lambda timeouts or state machine timeout

## Future Enhancements

1. **Batch Processing**: Add Map state for multiple companies
2. **Notifications**: Add SNS integration for completion alerts
3. **Data Validation**: Add validation steps before merge
4. **Resume Support**: Add checkpointing for long-running executions
5. **Cost Tracking**: Add tags for cost allocation

## Support

For issues or questions:
1. Check CloudWatch Logs for detailed error messages
2. Review Lambda execution logs
3. Verify DynamoDB table contents
4. Check S3 bucket for output files

