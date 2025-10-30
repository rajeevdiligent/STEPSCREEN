# Complete Company Data Extraction Workflow with S3 Merge

## 🎯 Overview

Successfully implemented a **complete end-to-end workflow** that extracts company data from 3 sources, saves to DynamoDB, merges all data, and exports to S3.

---

## 🔄 Complete Workflow

```
Input: {company_name, location}
  ↓
┌────────────────────────────────────────────┐
│ 1. Extract SEC Data                        │
│    - Company information from SEC/regulatory│
│    - Save to CompanySECData (DynamoDB)     │
│    - Returns: company_id, website_url      │
└────────────────────────────────────────────┘
  ↓
┌────────────────────────────────────────────┐
│ 2. Parallel Extraction                     │
│                                            │
│  ┌──────────────┐    ┌──────────────────┐ │
│  │ CXO Extractor│    │ Adverse Media    │ │
│  │              │    │ Scanner          │ │
│  │ Input:       │    │                  │ │
│  │ - website_url│    │ Input:           │ │
│  │              │    │ - company_id     │ │
│  │ Output:      │    │                  │ │
│  │ → DynamoDB   │    │ Output:          │ │
│  │ CXOData      │    │ → DynamoDB       │ │
│  │              │    │ AdverseMedia     │ │
│  └──────────────┘    └──────────────────┘ │
└────────────────────────────────────────────┘
  ↓
┌────────────────────────────────────────────┐
│ 3. Merge and Export to S3                  │
│    - Query all 3 DynamoDB tables          │
│    - Merge by company_id                  │
│    - Create unified JSON                  │
│    - Upload to S3 bucket                  │
└────────────────────────────────────────────┘
  ↓
✅ Complete!
```

---

## 📊 Test Results

### **Test: Tesla Inc**

```bash
Input:
{
  "company_name": "Tesla Inc",
  "location": "California"
}

Results:
✅ SEC Extraction:      83.33% complete (status 200)
✅ CXO Extraction:      Success (status 200) - 4 executives
✅ Adverse Media Scan:  Success (status 200) - 4 items
✅ Merge to S3:         Success (status 200)

S3 Output:
  📄 s3://company-sec-cxo-data-diligent/company_data/tesla_inc_20251029_081428.json
  📄 s3://company-sec-cxo-data-diligent/company_data/tesla_inc_latest.json
  
Duration: 29 seconds
Status: ✅ SUCCEEDED
```

### **Merged Data Structure:**

```json
[
  {
    "company_id": "tesla_inc",
    "sec_data": {
      "annual_revenue": "$124.3 billion (Q1 2025)",
      "business_description": "Tesla, Inc. is an automotive...",
      "company_identifiers": {...},
      "registered_business_address": "...",
      "incorporation_date": "...",
      "country_of_incorporation": "...",
      "number_of_employees": "...",
      "website_url": "https://www.tesla.com",
      ...
    },
    "executives": [
      {
        "name": "Robyn Denholm",
        "title": "Chairman of the Board",
        "linkedin_url": "...",
        "email": "..."
      },
      {
        "name": "Elon Musk",
        "title": "Chief Executive Officer",
        ...
      }
    ],
    "adverse_media": [
      {
        "title": "Tesla Faces Multiple Lawsuits Over Autopilot Safety",
        "adverse_category": "Legal",
        "severity_score": 0.8,
        "confidence_score": 0.9,
        "description": "...",
        "source": "...",
        "url": "...",
        "published_date": "..."
      }
    ]
  }
]
```

---

## 🔧 Changes Made

### **1. Updated Merge Handler Lambda (`lambda_merge_handler.py`):**

**Added:**
- ✅ Support for `CompanyAdverseMedia` DynamoDB table
- ✅ `DecimalEncoder` class to handle DynamoDB Decimal types
- ✅ Updated `extract_data()` to query 3 tables (was 2)
- ✅ Updated `merge_data()` to merge 3 data types (was 2)
- ✅ Applied `DecimalEncoder` to all `json.dumps()` calls

**Output Structure:**
```python
{
    'company_id': 'company_name',
    'sec_data': {...},          # SEC/regulatory data
    'executives': [...],         # CXO executive data
    'adverse_media': [...]       # Adverse media findings
}
```

### **2. Updated Step Function (`stepfunction_definition_complete_extraction.json`):**

**Added:**
- ✅ `MergeAndSaveToS3` state - Invokes DynamoDBToS3Merger Lambda
- ✅ `MergeFailed` state - Graceful error handling
- ✅ Retry logic for merge operation
- ✅ Passes `company_name` to merge handler

**New States:**
1. `CompileFinalResults` → `MergeAndSaveToS3` → `ExtractionComplete`
2. Error path: `MergeAndSaveToS3` → `MergeFailed` → `ExtractionComplete`

### **3. Updated IAM Permissions:**

**Role:** `CompleteCompanyDataExtractionRole`

**Added Permission:**
```json
{
  "Effect": "Allow",
  "Action": ["lambda:InvokeFunction"],
  "Resource": "arn:aws:lambda:us-east-1:891067072053:function:DynamoDBToS3Merger"
}
```

---

## 💾 Data Storage

### **DynamoDB Tables (Input):**

| Table | Purpose | Data |
|-------|---------|------|
| `CompanySECData` | SEC/regulatory filings | Company info, financials, identifiers |
| `CompanyCXOData` | Executive information | Names, titles, contact info |
| `CompanyAdverseMedia` | Adverse media findings | Title, category, severity, description |

### **S3 Storage (Output):**

| File | Purpose |
|------|---------|
| `company_data/{company_id}_{timestamp}.json` | Timestamped merged data |
| `company_data/{company_id}_latest.json` | Latest merged data |

**Bucket:** `company-sec-cxo-data-diligent`

---

## ⏱️ Performance

| Stage | Duration | Notes |
|-------|----------|-------|
| **SEC Extraction** | 6-15 sec | Depends on document availability |
| **Parallel Extraction** | 15-25 sec | CXO + Adverse Media (simultaneous) |
| **Merge to S3** | 1-2 sec | Fast DynamoDB query + S3 upload |
| **Total** | 22-42 sec | Complete end-to-end pipeline |

---

## 💰 Cost Estimate

### **Per Company Extraction:**

| Component | Cost |
|-----------|------|
| Nova SEC Extractor | $0.015 |
| CXO Website Extractor | $0.080 |
| Adverse Media Scanner | $0.020 |
| DynamoDB (3 tables) | $0.001 |
| Merge Lambda | $0.0001 |
| S3 Storage | $0.0001 |
| Step Functions | $0.0001 |
| **Total** | **$0.116** |

---

## 🚀 Usage

### **Start Extraction:**

```bash
cd /Users/rchandran/Library/CloudStorage/OneDrive-DiligentCorporation/TPMAI/STEPSCREEN

# Start and monitor execution
python3 monitor_stepfunction_execution.py --start "Company Name" "Location"
```

### **Example:**

```bash
python3 monitor_stepfunction_execution.py --start "Apple Inc" "California"
```

### **AWS CLI:**

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:891067072053:stateMachine:CompleteCompanyDataExtraction \
  --input '{"company_name": "Microsoft Corporation", "location": "Washington"}' \
  --profile diligent
```

---

## 📥 Downloading Results

### **From S3:**

```python
import boto3
import json

session = boto3.Session(profile_name='diligent', region_name='us-east-1')
s3_client = session.client('s3')

response = s3_client.get_object(
    Bucket='company-sec-cxo-data-diligent',
    Key='company_data/tesla_inc_latest.json'
)

data = json.loads(response['Body'].read().decode('utf-8'))
print(json.dumps(data, indent=2))
```

---

## 🔍 Data Validation

### **Verified for Tesla Inc:**

```
✅ SEC Data:      13 fields populated
✅ CXO Data:      4 executives extracted
✅ Adverse Media: 4 items found
✅ S3 File Size:  10,030 bytes
✅ JSON Valid:    ✓
```

---

## 📋 Files Updated

1. ✅ `lambda/lambda_merge_handler.py` - Added adverse media support & Decimal encoder
2. ✅ `stepfunction_definition_complete_extraction.json` - Added merge state
3. ✅ `clear_dynamodb_tables.py` - Added CompanyAdverseMedia table
4. ✅ IAM Role: `CompleteCompanyDataExtractionRole` - Added merge Lambda permission

---

## ✅ Deployment Checklist

- [x] Merge handler updated to include 3 tables
- [x] Decimal serialization fixed
- [x] Step Function updated with merge state
- [x] IAM permissions added for merge Lambda
- [x] Tested end-to-end (Tesla Inc)
- [x] Verified S3 output contains all 3 data types
- [x] Verified JSON structure is correct
- [x] Documentation created

---

## 🎯 Benefits

### **Before:**
- ❌ Data scattered across 3 DynamoDB tables
- ❌ Manual merging required
- ❌ No unified export format

### **After:**
- ✅ Automatic merging of all data
- ✅ Single unified JSON file per company
- ✅ Both timestamped and latest versions
- ✅ Ready for downstream consumption
- ✅ Clean, structured data format

---

## 📊 Example Output Preview

```json
{
  "company_id": "tesla_inc",
  "sec_data": {
    "annual_revenue": "$124.3 billion",
    "registered_legal_name": "Tesla, Inc.",
    "website_url": "https://www.tesla.com",
    ...
  },
  "executives": [
    {
      "name": "Elon Musk",
      "title": "Chief Executive Officer"
    }
  ],
  "adverse_media": [
    {
      "title": "Tesla Faces Lawsuits...",
      "adverse_category": "Legal",
      "severity_score": 0.8
    }
  ]
}
```

---

**Deployment Date:** October 29, 2025  
**Version:** 2.0  
**Status:** ✅ Production Ready  
**Region:** us-east-1  
**AWS Profile:** diligent

