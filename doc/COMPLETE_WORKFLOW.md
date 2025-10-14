# Complete Company Data Extraction & Storage Workflow

## System Overview

A comprehensive AWS-based solution for extracting, storing, and managing company information from SEC filings and corporate websites using AI-powered extraction.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    DATA EXTRACTION LAYER                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │ nova_sec_extractor  │         │ cxo_website_extractor│        │
│  │    (SEC Filings)    │         │   (Corporate Sites)  │        │
│  └──────────┬──────────┘         └──────────┬──────────┘        │
│             │                               │                     │
│             │    Uses AWS Nova Pro LLM      │                     │
│             │    (amazon.nova-pro-v1:0)     │                     │
│             │                               │                     │
└─────────────┼───────────────────────────────┼─────────────────────┘
              │                               │
              ▼                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER (DynamoDB)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │  CompanySECData     │         │  CompanyCXOData     │        │
│  │  - Company Info     │         │  - Executive Profiles│        │
│  │  - Financials       │         │  - Leadership Data  │        │
│  │  - Identifiers      │         │  - Background Info  │        │
│  └─────────────────────┘         └─────────────────────┘        │
│                                                                    │
└─────────────┬────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  MERGE & EXPORT LAYER                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         merge_and_save_to_s3.py                          │    │
│  │  - Extracts from both DynamoDB tables                    │    │
│  │  - Merges by company_id                                  │    │
│  │  - Generates summary reports                             │    │
│  └───────────────────────────┬─────────────────────────────┘    │
│                               │                                   │
└───────────────────────────────┼───────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    S3 STORAGE LAYER                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  📦 S3 Bucket: company-data-bucket                               │
│  ├── company_data/                                               │
│  │   ├── merged_company_data_20251013_135000.json               │
│  │   ├── merged_company_data_20251013_140000.json               │
│  │   ├── merged_company_data_latest.json                        │
│  │   ├── summary_report_20251013_135000.json                    │
│  │   └── summary_report_20251013_140000.json                    │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Data Extractors

#### nova_sec_extractor.py
**Purpose:** Extract company data from SEC filings

**Features:**
- Searches SEC.gov for 10-K, 10-Q, 8-K filings
- Uses AWS Nova Pro for intelligent extraction
- Prioritizes latest 2025/2024 documents
- Extracts: Company info, financials, identifiers, business description

**Output:**
- JSON file: `nova_sec_extractions/{company}_nova_extraction_{timestamp}.json`
- DynamoDB: `CompanySECData` table

**Usage:**
```bash
python nova_sec_extractor.py "Apple Inc"
```

#### cxo_website_extractor.py
**Purpose:** Extract executive information from corporate websites

**Features:**
- Searches corporate HQ websites (excludes regional pages)
- Fetches full HTML content from top results
- Uses AWS Nova Pro for intelligent executive extraction
- Extracts: Names, titles, education, background, tenure

**Output:**
- JSON file: `cxo_nova_extractions/{company}_cxo_extraction_{timestamp}.json`
- DynamoDB: `CompanyCXOData` table

**Usage:**
```bash
python cxo_website_extractor.py "https://www.apple.com"
```

### 2. Storage Layer (DynamoDB)

#### CompanySECData Table
**Schema:**
- Partition Key: `company_id` (String)
- Sort Key: `extraction_timestamp` (String)
- Attributes: All SEC company data fields

**Purpose:** Store company SEC filings data with time-series capability

#### CompanyCXOData Table
**Schema:**
- Partition Key: `company_id` (String)
- Sort Key: `executive_id` (String)
- Attributes: All executive profile fields

**Purpose:** Store multiple executives per company

### 3. Merge & Export

#### merge_and_save_to_s3.py
**Purpose:** Consolidate all company data and export to S3

**Features:**
- Extracts latest data from both DynamoDB tables
- Intelligently merges by company_id
- Generates summary statistics
- Creates timestamped + latest versions
- Tracks data completeness

**Output:**
- Merged data: `s3://{bucket}/{prefix}/merged_company_data_{timestamp}.json`
- Latest version: `s3://{bucket}/{prefix}/merged_company_data_latest.json`
- Summary: `s3://{bucket}/{prefix}/summary_report_{timestamp}.json`

**Usage:**
```bash
python merge_and_save_to_s3.py company-data-bucket
```

## Setup Instructions

### Step 1: Create DynamoDB Tables

```bash
python setup_dynamodb_tables.py
```

This creates:
- `CompanySECData` table
- `CompanyCXOData` table

### Step 2: Create S3 Bucket

```bash
python setup_s3_bucket.py company-data-bucket
```

This creates and configures the S3 bucket with:
- Versioning enabled
- Lifecycle policy (archives after 90 days)

### Step 3: Extract Company Data

```bash
# Extract SEC data
python nova_sec_extractor.py "Apple Inc"
python nova_sec_extractor.py "Intel Corporation"
python nova_sec_extractor.py "Netflix Inc"

# Extract CXO data
python cxo_website_extractor.py "https://www.apple.com"
python cxo_website_extractor.py "https://www.intel.com"
python cxo_website_extractor.py "https://www.netflix.com"
```

### Step 4: Merge and Export to S3

```bash
python merge_and_save_to_s3.py company-data-bucket
```

## Data Flow

```
1. RUN EXTRACTORS
   ├── nova_sec_extractor.py "Company"
   └── cxo_website_extractor.py "https://company.com"
              ↓
2. DATA SAVED TO
   ├── JSON Files (backup)
   └── DynamoDB Tables
              ↓
3. MERGE DATA
   └── merge_and_save_to_s3.py bucket-name
              ↓
4. EXPORT TO S3
   ├── Timestamped file
   ├── Latest version
   └── Summary report
```

## Complete Workflow Example

```bash
# 1. Setup (one-time)
python setup_dynamodb_tables.py
python setup_s3_bucket.py my-company-data

# 2. Extract data for multiple companies
companies=("Apple Inc" "Intel Corporation" "Netflix Inc" "Cisco Systems")
websites=("https://www.apple.com" "https://www.intel.com" "https://www.netflix.com" "https://www.cisco.com")

for company in "${companies[@]}"; do
    python nova_sec_extractor.py "$company"
done

for website in "${websites[@]}"; do
    python cxo_website_extractor.py "$website"
done

# 3. Merge and export
python merge_and_save_to_s3.py my-company-data

# 4. Download and analyze
aws s3 cp s3://my-company-data/company_data/merged_company_data_latest.json . --profile diligent
```

## Output Structure

### Merged Data JSON

```json
[
  {
    "company_id": "apple_inc",
    "sec_data": {
      "company_name": "Apple Inc",
      "registered_legal_name": "Apple Inc.",
      "annual_revenue": "$124.3 billion (Q1 2025)",
      "number_of_employees": "164,000",
      "company_identifiers": {
        "CIK": "0000320193",
        "DUNS": "268000088",
        "LEI": "HWUPKR0MPOU8FGXBT394"
      }
    },
    "executives": [
      {
        "name": "Tim Cook",
        "title": "CEO",
        "education": "Auburn (BS), Duke (MBA)",
        "tenure": "Since August 2011"
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

## Cost Analysis

### Per Company Extraction:
- Serper API: $0.004 per search query (×15) = $0.060
- AWS Nova Pro: ~$0.020 per extraction
- DynamoDB Write: ~$0.001
- **Total per company: ~$0.08**

### Storage:
- DynamoDB: PAY_PER_REQUEST (minimal cost for small datasets)
- S3: $0.023 per GB-month (first 50 TB)
- **Total storage: < $1/month for 100 companies**

### Estimated Monthly Cost (100 Companies):
- Weekly extractions: 400 extractions/month × $0.08 = $32
- Storage: $1
- **Total: ~$33/month**

## Key Features

✅ **AI-Powered Extraction** - Uses AWS Nova Pro for intelligent data parsing  
✅ **Time-Series Data** - Tracks changes over time  
✅ **Clean JSON Output** - Production-ready format  
✅ **Comprehensive Coverage** - SEC filings + Corporate leadership  
✅ **Scalable Architecture** - DynamoDB + S3  
✅ **Cost-Effective** - Pay-per-request pricing  
✅ **Automated Backups** - JSON files + DynamoDB + S3  
✅ **Data Completeness Tracking** - Know what data is available  

## Files Reference

### Scripts
- `nova_sec_extractor.py` - SEC data extraction
- `cxo_website_extractor.py` - Executive data extraction
- `merge_and_save_to_s3.py` - Data merge & S3 export
- `setup_dynamodb_tables.py` - DynamoDB setup
- `setup_s3_bucket.py` - S3 bucket setup

### Documentation
- `DYNAMODB_SETUP_README.md` - DynamoDB integration guide
- `S3_MERGE_README.md` - S3 merge script guide
- `COMPLETE_WORKFLOW.md` - This document

### Configuration
- `.env` - API keys and credentials
- `requirements.txt` - Python dependencies

## Requirements

```
boto3>=1.28.0
requests>=2.31.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0
```

## AWS Resources Created

1. **DynamoDB Tables:**
   - CompanySECData
   - CompanyCXOData

2. **S3 Bucket:**
   - Your specified bucket name
   - With versioning enabled
   - With lifecycle policies

3. **AWS Services Used:**
   - Amazon Bedrock (Nova Pro)
   - DynamoDB
   - S3

## Next Steps

1. ✅ Setup infrastructure (DynamoDB + S3)
2. ✅ Extract data for companies
3. ✅ Merge and export to S3
4. 📊 Build analytics dashboard
5. 🤖 Automate with Lambda/EventBridge
6. 📧 Set up monitoring/alerts

## Support

For issues or questions:
1. Check the respective README files
2. Review error logs
3. Verify AWS permissions
4. Ensure API keys are valid

