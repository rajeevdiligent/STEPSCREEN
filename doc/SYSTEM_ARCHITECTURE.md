# STEPSCREEN - System Architecture

**Project:** Company Data Extraction Pipeline  
**Version:** 1.0  
**Date:** October 14, 2025

---

## Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Detailed Component Architecture](#detailed-component-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [AWS Infrastructure](#aws-infrastructure)
5. [Execution Flow](#execution-flow)
6. [Error Handling Flow](#error-handling-flow)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEPSCREEN ARCHITECTURE                              │
│                   Company Data Extraction Pipeline                           │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │   User/API   │
                            │   Request    │
                            └──────┬───────┘
                                   │
                                   │ Input: {company_name, website_url, stock_symbol}
                                   ▼
                    ┌──────────────────────────────┐
                    │    AWS Step Functions       │
                    │  State Machine Orchestrator  │
                    └──────────────┬───────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                │ Parallel Execution                  │
                │                  │                  │
        ┌───────▼───────┐  ┌──────▼────────┐  ┌─────▼──────┐
        │ Lambda:       │  │ Lambda:       │  │  External  │
        │ Nova SEC      │  │ CXO Website   │  │    APIs    │
        │ Extractor     │  │ Extractor     │  │            │
        └───────┬───────┘  └───────┬───────┘  └─────┬──────┘
                │                  │                  │
                │ ┌────────────────┼──────────────────┤
                │ │                │                  │
                │ │                │                  │
        ┌───────▼─▼────────────────▼──────────┐     │
        │         DynamoDB Tables              │     │
        │  ┌──────────────┬─────────────────┐ │     │
        │  │CompanySECData│CompanyCXOData   │ │     │
        │  └──────────────┴─────────────────┘ │     │
        └────────────────┬────────────────────┘     │
                         │                           │
                         │ Both complete             │
                         │                           │
                ┌────────▼──────────┐                │
                │    Lambda:        │                │
                │ DynamoDB to S3    │                │
                │    Merger         │                │
                └────────┬──────────┘                │
                         │                           │
                         │ Merged JSON               │
                         ▼                           │
                ┌────────────────────┐               │
                │   S3 Bucket:       │               │
                │ company-sec-cxo-   │               │
                │   data-diligent    │               │
                └────────────────────┘               │
                                                     │
                    External Services: ───────────────┘
                    • AWS Bedrock (Nova Pro)
                    • Serper API
                    • SEC EDGAR
```

---

## Detailed Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPONENT ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         1. AWS STEP FUNCTIONS LAYER                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  State Machine: CompanyDataExtractionPipeline                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                          │ │
│  │  START                                                                   │ │
│  │    │                                                                     │ │
│  │    ├─► ValidateInput (Pass State)                                       │ │
│  │    │   • Validates input schema                                         │ │
│  │    │   • Normalizes company_id                                          │ │
│  │    │                                                                     │ │
│  │    ├─► ParallelExtraction (Parallel State)                              │ │
│  │    │   ┌─────────────────────┬────────────────────┐                    │ │
│  │    │   │ Branch 1:           │ Branch 2:          │                    │ │
│  │    │   │ ExtractSECData      │ ExtractCXOData     │                    │ │
│  │    │   │   (Task State)      │   (Task State)     │                    │ │
│  │    │   │                     │                    │                    │ │
│  │    │   │ • Timeout: 360s     │ • Timeout: 360s    │                    │ │
│  │    │   │ • Retry: 2x         │ • Retry: 2x        │                    │ │
│  │    │   │ • Catch errors      │ • Catch errors     │                    │ │
│  │    │   └─────────────────────┴────────────────────┘                    │ │
│  │    │                                                                     │ │
│  │    ├─► CheckExtractionResults (Choice State)                            │ │
│  │    │   • Both statusCode=200? → Continue                                │ │
│  │    │   • Completeness >= 95%? → Continue                                │ │
│  │    │   • Otherwise → Fail                                               │ │
│  │    │                                                                     │ │
│  │    ├─► MergeAndSaveToS3 (Task State)                                    │ │
│  │    │   • Timeout: 180s                                                  │ │
│  │    │   • Retry: 2x                                                      │ │
│  │    │   • Catch errors                                                   │ │
│  │    │                                                                     │ │
│  │    └─► PipelineSuccess / ExtractionFailed (End States)                  │ │
│  │                                                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Features:                                                                   │
│  • CloudWatch Logs: /aws/vendedlogs/states/CompanyDataExtractionPipeline    │
│  • IAM Role: CompanyDataExtractionStepFunctionRole                           │
│  • Tags: Project=STEPSCREEN, Purpose=DataExtraction                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         2. LAMBDA FUNCTIONS LAYER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Lambda 1: NovaSECExtractor                                             │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Runtime: Python 3.11                                                   │ │
│  │ Memory: 768 MB                                                         │ │
│  │ Timeout: 300 seconds (5 minutes)                                       │ │
│  │ Handler: lambda_nova_sec_handler.lambda_handler                        │ │
│  │                                                                        │ │
│  │ Core Logic:                                                            │ │
│  │   1. Receive company_name, stock_symbol                                │ │
│  │   2. Search SEC documents via Serper API                               │ │
│  │      • Site-specific: site:sec.gov {company}                           │ │
│  │      • Global fallback: {company} SEC filing                           │ │
│  │   3. Extract data with AWS Bedrock Nova Pro                            │ │
│  │      • Model: amazon.nova-pro-v1:0                                     │ │
│  │      • Temperature: 0.3                                                │ │
│  │      • Max tokens: 4000                                                │ │
│  │   4. Validate completeness (>= 95%)                                    │ │
│  │   5. Retry if incomplete (max 3 attempts)                              │ │
│  │   6. Save to DynamoDB (CompanySECData)                                 │ │
│  │   7. Save local JSON copy (if not Lambda)                              │ │
│  │                                                                        │ │
│  │ Dependencies:                                                          │ │
│  │   • boto3, requests, beautifulsoup4, python-dotenv                     │ │
│  │                                                                        │ │
│  │ Environment Variables:                                                 │ │
│  │   • SERPER_API_KEY                                                     │ │
│  │   • AWS_LAMBDA_FUNCTION_NAME (auto)                                    │ │
│  │                                                                        │ │
│  │ IAM Role: LambdaCompanyExtractionRole                                  │ │
│  │   • bedrock:InvokeModel                                                │ │
│  │   • dynamodb:PutItem                                                   │ │
│  │   • logs:CreateLogGroup, PutLogEvents                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Lambda 2: CXOWebsiteExtractor                                          │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Runtime: Python 3.11                                                   │ │
│  │ Memory: 768 MB                                                         │ │
│  │ Timeout: 360 seconds (6 minutes)                                       │ │
│  │ Handler: lambda_cxo_handler.lambda_handler                             │ │
│  │                                                                        │ │
│  │ Core Logic:                                                            │ │
│  │   1. Receive company_name, website_url                                 │ │
│  │   2. Search for executive pages via Serper API                         │ │
│  │      • "leadership" OR "management" OR "executives" site:{website}     │ │
│  │   3. Fetch and parse page content (limit: 5000 chars)                  │ │
│  │   4. Extract executives with Nova Pro                                  │ │
│  │      • Model: amazon.nova-pro-v1:0                                     │ │
│  │      • Temperature: 0.3                                                │ │
│  │      • Max tokens: 6000                                                │ │
│  │   5. Validate completeness (>= 95%)                                    │ │
│  │   6. Retry if incomplete (max 3 attempts)                              │ │
│  │   7. Save to DynamoDB (CompanyCXOData)                                 │ │
│  │   8. Save local JSON copy (if not Lambda)                              │ │
│  │                                                                        │ │
│  │ Dependencies:                                                          │ │
│  │   • boto3, requests, beautifulsoup4, python-dotenv                     │ │
│  │                                                                        │ │
│  │ Environment Variables:                                                 │ │
│  │   • SERPER_API_KEY                                                     │ │
│  │   • AWS_LAMBDA_FUNCTION_NAME (auto)                                    │ │
│  │                                                                        │ │
│  │ IAM Role: LambdaCompanyExtractionRole                                  │ │
│  │   • bedrock:InvokeModel                                                │ │
│  │   • dynamodb:PutItem                                                   │ │
│  │   • logs:CreateLogGroup, PutLogEvents                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Lambda 3: DynamoDBToS3Merger                                           │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Runtime: Python 3.11                                                   │ │
│  │ Memory: 512 MB                                                         │ │
│  │ Timeout: 120 seconds (2 minutes)                                       │ │
│  │ Handler: lambda_merge_handler.lambda_handler                           │ │
│  │                                                                        │ │
│  │ Core Logic:                                                            │ │
│  │   1. Receive s3_bucket_name, company_name                              │ │
│  │   2. Query DynamoDB for specific company                               │ │
│  │      • CompanySECData: Get latest by company_id                        │ │
│  │      • CompanyCXOData: Get all executives for company_id               │ │
│  │   3. Merge SEC + CXO data                                              │ │
│  │      • Add executives array to company info                            │ │
│  │      • Add extraction metadata                                         │ │
│  │   4. Save to S3                                                        │ │
│  │      • Timestamped: company_data/{company}_{timestamp}.json            │ │
│  │      • Latest: company_data/{company}_latest.json                      │ │
│  │   5. Return merge statistics                                           │ │
│  │                                                                        │ │
│  │ IAM Role: LambdaCompanyExtractionRole                                  │ │
│  │   • dynamodb:Query, Scan                                               │ │
│  │   • s3:PutObject                                                       │ │
│  │   • logs:CreateLogGroup, PutLogEvents                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          3. DATA STORAGE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ DynamoDB Table: CompanySECData                                         │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Partition Key: company_id (String)                                     │ │
│  │ Sort Key: extraction_timestamp (String)                                │ │
│  │                                                                        │ │
│  │ Schema:                                                                │ │
│  │   {                                                                    │ │
│  │     "company_id": "apple_inc",                                         │ │
│  │     "extraction_timestamp": "2025-10-14T10:30:00",                     │ │
│  │     "company_name": "Apple Inc",                                       │ │
│  │     "stock_symbol": "AAPL",                                            │ │
│  │     "official_name": "Apple Inc.",                                     │ │
│  │     "cik": "0000320193",                                               │ │
│  │     "duns": "...",                                                     │ │
│  │     "lei": "...",                                                      │ │
│  │     "address": {...},                                                  │ │
│  │     "website": "https://apple.com",                                    │ │
│  │     "fiscal_year_end": "09-30",                                        │ │
│  │     "industry": "Technology",                                          │ │
│  │     "business_description": "...",                                     │ │
│  │     "financial_data": {...},                                           │ │
│  │     "regulatory_filings": [...],                                       │ │
│  │     "extraction_source": "nova_sec_extractor",                         │ │
│  │     "completeness": 95.2                                               │ │
│  │   }                                                                    │ │
│  │                                                                        │ │
│  │ Billing Mode: On-Demand                                                │ │
│  │ Read/Write Capacity: Auto-scaling                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ DynamoDB Table: CompanyCXOData                                         │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Partition Key: company_id (String)                                     │ │
│  │ Sort Key: executive_id (String)                                        │ │
│  │                                                                        │ │
│  │ Schema:                                                                │ │
│  │   {                                                                    │ │
│  │     "company_id": "apple_inc",                                         │ │
│  │     "executive_id": "apple_inc_1_2025-10-14T10:35:00",                │ │
│  │     "extraction_timestamp": "2025-10-14T10:35:00",                     │ │
│  │     "name": "Tim Cook",                                                │ │
│  │     "title": "Chief Executive Officer",                                │ │
│  │     "role_category": "C-Suite",                                        │ │
│  │     "description": "...",                                              │ │
│  │     "tenure": "Since 2011",                                            │ │
│  │     "background": "...",                                               │ │
│  │     "education": [...],                                                │ │
│  │     "previous_roles": [...],                                           │ │
│  │     "contact_info": {...},                                             │ │
│  │     "extraction_source": "cxo_website_extractor",                      │ │
│  │     "website_source": "https://apple.com/leadership"                   │ │
│  │   }                                                                    │ │
│  │                                                                        │ │
│  │ Billing Mode: On-Demand                                                │ │
│  │ Read/Write Capacity: Auto-scaling                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ S3 Bucket: company-sec-cxo-data-diligent                               │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Region: us-east-1                                                      │ │
│  │ Versioning: Enabled                                                    │ │
│  │ Encryption: AES-256                                                    │ │
│  │                                                                        │ │
│  │ Structure:                                                             │ │
│  │   company-sec-cxo-data-diligent/                                       │ │
│  │   ├── company_data/                                                    │ │
│  │   │   ├── apple_inc_20251014_103500.json      (timestamped)           │ │
│  │   │   ├── apple_inc_latest.json                (latest version)       │ │
│  │   │   ├── microsoft_corporation_20251014.json                         │ │
│  │   │   ├── microsoft_corporation_latest.json                           │ │
│  │   │   └── ...                                                          │ │
│  │                                                                        │ │
│  │ Lifecycle Policy:                                                      │ │
│  │   • Transition to IA after 30 days                                     │ │
│  │   • Archive to Glacier after 90 days                                   │ │
│  │   • Delete timestamped files after 1 year                              │ │
│  │   • Keep *_latest.json indefinitely                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       4. EXTERNAL SERVICES LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ AWS Bedrock - Amazon Nova Pro                                          │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Model: amazon.nova-pro-v1:0                                            │ │
│  │ Region: us-east-1                                                      │ │
│  │                                                                        │ │
│  │ Use Cases:                                                             │ │
│  │   1. SEC Document Data Extraction                                      │ │
│  │      • Parse financial data from SEC filings                           │ │
│  │      • Extract company identifiers (CIK, DUNS, LEI)                    │ │
│  │      • Identify business descriptions                                  │ │
│  │                                                                        │ │
│  │   2. Executive Information Extraction                                  │ │
│  │      • Parse executive bios from leadership pages                      │ │
│  │      • Extract structured data (name, title, tenure)                   │ │
│  │      • Categorize roles (C-Suite, VP, Director)                        │ │
│  │                                                                        │ │
│  │ Configuration:                                                         │ │
│  │   • Temperature: 0.3 (balanced creativity/precision)                   │ │
│  │   • Max tokens: 4000-6000                                              │ │
│  │   • System prompt: Structured JSON extraction                          │ │
│  │                                                                        │ │
│  │ Cost: ~$0.03 per extraction                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Serper API - Web Search                                                │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Endpoint: https://google.serper.dev/search                             │ │
│  │ Authentication: API Key                                                │ │
│  │                                                                        │ │
│  │ Use Cases:                                                             │ │
│  │   1. SEC Document Search                                               │ │
│  │      Query: "site:sec.gov {company_name} 10-K"                         │ │
│  │      Returns: SEC filing URLs + snippets                               │ │
│  │                                                                        │ │
│  │   2. Executive Page Search                                             │ │
│  │      Query: "leadership OR management site:{website}"                  │ │
│  │      Returns: Leadership page URLs + snippets                          │ │
│  │                                                                        │ │
│  │ Rate Limits:                                                           │ │
│  │   • 1000 searches/month (free tier)                                    │ │
│  │   • Paid: $50/month for 5000 searches                                  │ │
│  │                                                                        │ │
│  │ Cost: ~$0.022 per search                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ SEC EDGAR (Future Enhancement)                                         │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ Base URL: https://data.sec.gov                                         │ │
│  │                                                                        │ │
│  │ Planned APIs:                                                          │ │
│  │   1. Company Facts API                                                 │ │
│  │      /api/xbrl/companyfacts/CIK{cik}.json                              │ │
│  │      Returns: Comprehensive company financials                         │ │
│  │                                                                        │ │
│  │   2. Submissions API                                                   │ │
│  │      /submissions/CIK{cik}.json                                        │ │
│  │      Returns: All company filings metadata                             │ │
│  │                                                                        │ │
│  │   3. Full Text Search API                                              │ │
│  │      /cgi-bin/browse-edgar?company={name}                              │ │
│  │      Returns: Filing search results                                    │ │
│  │                                                                        │ │
│  │ Status: Planned for Phase 1 improvements                               │ │
│  │ Cost: Free (rate limited to 10 req/sec)                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Complete Execution Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       COMPLETE EXECUTION FLOW                               │
└────────────────────────────────────────────────────────────────────────────┘

Time: 0s
├─► User initiates extraction
│   Input: {
│     "company_name": "Apple Inc",
│     "website_url": "https://apple.com",
│     "stock_symbol": "AAPL"
│   }
│
│   Step Function starts
│   Execution ARN: arn:aws:states:...:execution:...
│
Time: 0-2s
├─► ValidateInput (Pass State)
│   • Normalize company_id: "apple_inc"
│   • Validate required fields
│   • Add execution metadata
│
Time: 2-62s
├─► ParallelExtraction (Parallel State)
│   ├─────────────────────────────────┬─────────────────────────────────┐
│   │                                 │                                 │
│   │ Branch 1: SEC Extraction        │ Branch 2: CXO Extraction        │
│   │                                 │                                 │
│   │ Time: 2-47s (45s execution)     │ Time: 2-64s (62s execution)     │
│   │                                 │                                 │
│   │ 2-4s: Cold start (if first run) │ 2-4s: Cold start                │
│   │ 4-10s: Serper API search        │ 4-15s: Serper API search        │
│   │   ├─ site:sec.gov apple 10-K    │   ├─ leadership site:apple.com  │
│   │   └─ Returns 10 results         │   └─ Returns 10 results         │
│   │                                 │                                 │
│   │ 10-12s: Filter/rank results     │ 15-25s: Fetch page content      │
│   │   ├─ Prioritize 10-K, 8-K       │   ├─ requests.get(url)          │
│   │   └─ Select top 5 documents     │   └─ BeautifulSoup parse        │
│   │                                 │                                 │
│   │ 12-42s: Nova Pro extraction     │ 25-60s: Nova Pro extraction     │
│   │   ├─ Build prompt with snippets │   ├─ Build prompt with HTML     │
│   │   ├─ bedrock.invoke_model()     │   ├─ bedrock.invoke_model()     │
│   │   ├─ Parse JSON response        │   ├─ Parse JSON response        │
│   │   └─ Validate completeness      │   └─ Validate completeness      │
│   │                                 │                                 │
│   │ 42-44s: Check completeness      │ 60-62s: Check completeness      │
│   │   ├─ Calculate fill rate        │   ├─ Calculate fill rate        │
│   │   ├─ If < 95%, retry            │   ├─ If < 95%, retry            │
│   │   └─ Max 3 attempts             │   └─ Max 3 attempts             │
│   │                                 │                                 │
│   │ 44-47s: Save to DynamoDB        │ 62-64s: Save to DynamoDB        │
│   │   ├─ Table: CompanySECData      │   ├─ Table: CompanyCXOData      │
│   │   ├─ PK: company_id             │   ├─ PK: company_id             │
│   │   ├─ SK: timestamp              │   ├─ SK: executive_id           │
│   │   └─ Return: statusCode 200     │   └─ Return: statusCode 200     │
│   │                                 │                                 │
│   └─────────────────────────────────┴─────────────────────────────────┘
│   Both complete at 64s
│
Time: 64-65s
├─► CheckExtractionResults (Choice State)
│   Conditions:
│   ✓ SEC statusCode == 200
│   ✓ CXO statusCode == 200
│   ✓ SEC completeness >= 95%
│   ✓ CXO completeness >= 95%
│   Result: Proceed to merge
│
Time: 65-71s
├─► MergeAndSaveToS3 (Task State - Lambda)
│   65-66s: Cold start
│   66-67s: Query DynamoDB
│     ├─ CompanySECData.query(company_id="apple_inc")
│     └─ CompanyCXOData.query(company_id="apple_inc")
│   67-68s: Merge data
│     ├─ Combine SEC + CXO JSON
│     └─ Add executives[] array
│   68-70s: Save to S3
│     ├─ s3.put_object(Key="apple_inc_20251014.json")
│     └─ s3.put_object(Key="apple_inc_latest.json")
│   70-71s: Return success
│
Time: 71s
└─► PipelineSuccess (End State)
    Output: {
      "status": "success",
      "company_name": "Apple Inc",
      "company_id": "apple_inc",
      "sec_completeness": 95.2,
      "cxo_completeness": 96.8,
      "executives_count": 14,
      "execution_time": 71,
      "s3_files": [
        "company_data/apple_inc_20251014_103500.json",
        "company_data/apple_inc_latest.json"
      ]
    }

Total Execution Time: 71 seconds
Cost Breakdown:
  • Step Functions: $0.0002
  • Lambda (3 invocations): $0.0024
  • Serper API (2 searches): $0.0440
  • Nova Pro (2 extractions): $0.0600
  • DynamoDB (reads/writes): $0.0001
  • S3 (puts): $0.0000
  Total: $0.1067
```

### 2. SEC Extractor Internal Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   NOVA SEC EXTRACTOR INTERNAL FLOW                          │
└────────────────────────────────────────────────────────────────────────────┘

START Lambda Handler
│
├─► 1. Input Validation
│   Input: {"company_name": "Apple Inc", "stock_symbol": "AAPL"}
│   ✓ Check required fields
│   ✓ Normalize company_id: "apple_inc"
│
├─► 2. Search for SEC Documents (Serper API)
│   ┌────────────────────────────────────────────────┐
│   │ Strategy: Hybrid Search                        │
│   ├────────────────────────────────────────────────┤
│   │                                                │
│   │ Search 1: Site-Specific                        │
│   │   Query: "site:sec.gov Apple Inc 10-K"         │
│   │   Results: 10 URLs                             │
│   │   Priority: HIGH                               │
│   │                                                │
│   │ IF Search 1 returns < 5 results:               │
│   │   Search 2: Global Fallback                    │
│   │   Query: "Apple Inc SEC filing 10-K"           │
│   │   Results: 10 URLs                             │
│   │   Priority: MEDIUM                             │
│   │                                                │
│   │ Ranking:                                       │
│   │   1. 10-K filings (annual reports)             │
│   │   2. 8-K filings (current reports)             │
│   │   3. DEF 14A (proxy statements)                │
│   │   4. Other filings                             │
│   │                                                │
│   │ Select: Top 5 results                          │
│   └────────────────────────────────────────────────┘
│   Output: [
│     {"title": "Apple Inc 10-K 2024", "link": "...", "snippet": "..."},
│     ...
│   ]
│
├─► 3. Build Extraction Context
│   ┌────────────────────────────────────────────────┐
│   │ Current Implementation:                        │
│   │   • Concatenate snippets (max 2000 chars)      │
│   │   • Limited: Only metadata, no full content    │
│   │                                                │
│   │ ⚠️ BOTTLENECK: No document content fetching    │
│   │    Impact: 70% of missing data                 │
│   │                                                │
│   │ Future Enhancement (Phase 1):                  │
│   │   • Fetch full document content                │
│   │   • Extract specific sections                  │
│   │   • Use SEC EDGAR API                          │
│   └────────────────────────────────────────────────┘
│   Output: search_context = "Apple Inc... [2000 chars]"
│
├─► 4. Nova Pro Extraction
│   ┌────────────────────────────────────────────────┐
│   │ Model: amazon.nova-pro-v1:0                    │
│   │ Temperature: 0.3                               │
│   │ Max tokens: 4000                               │
│   │                                                │
│   │ Prompt Structure:                              │
│   │   System: "You are an expert at extracting..." │
│   │   User: {                                      │
│   │     "task": "Extract company information",     │
│   │     "context": "[Search results snippets]",    │
│   │     "company": "Apple Inc",                    │
│   │     "required_fields": {...}                   │
│   │   }                                            │
│   │                                                │
│   │ Response Format: JSON                          │
│   │   {                                            │
│   │     "official_name": "Apple Inc.",             │
│   │     "cik": "0000320193",                       │
│   │     "address": {...},                          │
│   │     "industry": "Technology",                  │
│   │     "financial_data": {...},                   │
│   │     ...                                        │
│   │   }                                            │
│   └────────────────────────────────────────────────┘
│   API Call: bedrock_runtime.invoke_model(...)
│   Response Time: ~30 seconds
│
├─► 5. Completeness Validation
│   ┌────────────────────────────────────────────────┐
│   │ Calculate Completeness Score:                  │
│   │                                                │
│   │ Required Fields (23 total):                    │
│   │   Core: name, cik, address, industry, website  │
│   │   Financial: revenue, net_income, assets       │
│   │   Regulatory: fiscal_year_end, sic_code        │
│   │                                                │
│   │ Score = (filled_fields / total_fields) × 100   │
│   │                                                │
│   │ Example:                                       │
│   │   Filled: 22 fields                            │
│   │   Total: 23 fields                             │
│   │   Score: 95.7%                                 │
│   │                                                │
│   │ Threshold: >= 95%                              │
│   │ Current Average: 65%                           │
│   │ Target (Phase 1): 95%+                         │
│   └────────────────────────────────────────────────┘
│
├─► 6. Retry Logic (If completeness < 95%)
│   ┌────────────────────────────────────────────────┐
│   │ Retry Strategy:                                │
│   │   Attempt 1: Standard prompt                   │
│   │   Attempt 2: Enhanced prompt with emphasis     │
│   │   Attempt 3: Relaxed threshold (90%)           │
│   │                                                │
│   │ Max Attempts: 3                                │
│   │ Backoff: None (immediate retry)                │
│   │                                                │
│   │ Success Rate:                                  │
│   │   Attempt 1: 65%                               │
│   │   Attempt 2: 75%                               │
│   │   Attempt 3: 80%                               │
│   └────────────────────────────────────────────────┘
│   If all attempts fail: Return best result with warning
│
├─► 7. Save to DynamoDB
│   Table: CompanySECData
│   Item: {
│     "company_id": "apple_inc",
│     "extraction_timestamp": "2025-10-14T10:30:00",
│     [... extracted data ...],
│     "extraction_source": "nova_sec_extractor",
│     "completeness": 95.2
│   }
│   Result: Success
│
├─► 8. Save Local Copy (If not in Lambda)
│   File: sec_extraction_outputs/apple_nova_extraction_20251014.json
│   Skipped in Lambda (read-only filesystem)
│
└─► 9. Return Result
    Output: {
      "statusCode": 200,
      "body": {
        "status": "success",
        "company_name": "Apple Inc",
        "company_id": "apple_inc",
        "completeness": 95.2,
        "attempts": 1,
        "execution_time": 45
      }
    }

END Lambda Handler
```

### 3. CXO Extractor Internal Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   CXO WEBSITE EXTRACTOR INTERNAL FLOW                       │
└────────────────────────────────────────────────────────────────────────────┘

START Lambda Handler
│
├─► 1. Input Validation
│   Input: {"company_name": "Apple Inc", "website_url": "https://apple.com"}
│   ✓ Check required fields
│   ✓ Normalize company_id: "apple_inc"
│   ✓ Validate URL format
│
├─► 2. Search for Leadership Pages (Serper API)
│   ┌────────────────────────────────────────────────┐
│   │ Search Strategy: Comprehensive                 │
│   ├────────────────────────────────────────────────┤
│   │                                                │
│   │ Query: (leadership OR management OR            │
│   │         executives OR "about us" OR            │
│   │         "our team" OR board) site:apple.com    │
│   │                                                │
│   │ Filters:                                       │
│   │   • Must be from target domain                 │
│   │   • Exclude: jobs, careers, press releases     │
│   │   • Prioritize: /leadership, /team, /about     │
│   │                                                │
│   │ Results: 10 URLs                               │
│   │   1. https://apple.com/leadership/             │
│   │   2. https://apple.com/leadership/tim-cook/    │
│   │   3. https://apple.com/about/management/       │
│   │   ...                                          │
│   │                                                │
│   │ Ranking by Relevance:                          │
│   │   Score = keyword_match + url_pattern +        │
│   │           snippet_quality                      │
│   │                                                │
│   │ Select: Top 5 pages                            │
│   └────────────────────────────────────────────────┘
│   Output: [
│     {"title": "Leadership - Apple", "link": "...", "snippet": "..."},
│     ...
│   ]
│
├─► 3. Fetch Page Content
│   ┌────────────────────────────────────────────────┐
│   │ For each selected URL:                         │
│   │                                                │
│   │ 1. HTTP GET request                            │
│   │    headers = {                                 │
│   │      'User-Agent': 'Mozilla/5.0...',           │
│   │      'Accept': 'text/html'                     │
│   │    }                                           │
│   │    timeout = 10 seconds                        │
│   │                                                │
│   │ 2. Parse HTML (BeautifulSoup)                  │
│   │    • Remove script, style tags                 │
│   │    • Extract visible text                      │
│   │    • Preserve structure (headers, lists)       │
│   │                                                │
│   │ 3. Truncate to 5000 chars                      │
│   │    ⚠️ BOTTLENECK: Page limit too low           │
│   │       Typical page: 10k-20k chars              │
│   │       Current limit: 5k chars                  │
│   │       Data loss: 40-60%                        │
│   │                                                │
│   │ 4. Combine all pages                           │
│   │    Total content: ~25,000 chars                │
│   │    Truncated to: ~5,000 chars                  │
│   │    Executives visible: 4-6 of 14               │
│   │                                                │
│   │ Future Enhancement (Phase 1):                  │
│   │   • Increase limit to 15k per page             │
│   │   • Smart section detection                    │
│   │   • Extract only executive info                │
│   └────────────────────────────────────────────────┘
│   Output: combined_content = "Apple Leadership... [5000 chars]"
│
├─► 4. Nova Pro Extraction
│   ┌────────────────────────────────────────────────┐
│   │ Model: amazon.nova-pro-v1:0                    │
│   │ Temperature: 0.3                               │
│   │ Max tokens: 6000                               │
│   │                                                │
│   │ ⚠️ BOTTLENECK: Token limit                     │
│   │    Previous: 4000 tokens (truncates at 9 execs)│
│   │    Current: 6000 tokens (supports 14 execs)    │
│   │                                                │
│   │ Prompt Structure:                              │
│   │   System: "Extract executive information..."   │
│   │   User: {                                      │
│   │     "company": "Apple Inc",                    │
│   │     "page_content": "[HTML text]",             │
│   │     "required_fields": {                       │
│   │       "name": "Full name",                     │
│   │       "title": "Job title",                    │
│   │       "role_category": "C-Suite/VP/Director",  │
│   │       "description": "Bio/background",         │
│   │       ...                                      │
│   │     }                                          │
│   │   }                                            │
│   │                                                │
│   │ Response Format: JSON Array                    │
│   │   {                                            │
│   │     "executives": [                            │
│   │       {                                        │
│   │         "name": "Tim Cook",                    │
│   │         "title": "CEO",                        │
│   │         "role_category": "C-Suite",            │
│   │         ...                                    │
│   │       },                                       │
│   │       ...                                      │
│   │     ]                                          │
│   │   }                                            │
│   └────────────────────────────────────────────────┘
│   API Call: bedrock_runtime.invoke_model(...)
│   Response Time: ~35 seconds
│
├─► 5. Completeness Validation
│   ┌────────────────────────────────────────────────┐
│   │ Calculate Completeness Score (Per Executive):  │
│   │                                                │
│   │ Required Fields (10 total):                    │
│   │   Core: name, title, role_category             │
│   │   Optional: description, tenure, background    │
│   │            education, previous_roles,          │
│   │            contact_info                        │
│   │                                                │
│   │ Per-Executive Score:                           │
│   │   Score = (filled / total) × 100               │
│   │                                                │
│   │ Overall Score:                                 │
│   │   Average of all executives                    │
│   │                                                │
│   │ Quality Checks:                                │
│   │   ✓ At least 5 executives found                │
│   │   ✓ At least 1 C-Suite member                  │
│   │   ✓ No duplicate names                         │
│   │   ✓ Role diversity (CEO, CFO, CTO, etc.)       │
│   │                                                │
│   │ Threshold: >= 95%                              │
│   │ Current Average: 60%                           │
│   │ Target (Phase 1): 95%+                         │
│   └────────────────────────────────────────────────┘
│
├─► 6. Retry Logic (If completeness < 95%)
│   ┌────────────────────────────────────────────────┐
│   │ Retry Strategy:                                │
│   │   Attempt 1: Standard extraction               │
│   │   Attempt 2: Enhanced prompt + different pages │
│   │   Attempt 3: Relaxed threshold (90%)           │
│   │                                                │
│   │ Max Attempts: 3                                │
│   │ Backoff: None (immediate retry)                │
│   │                                                │
│   │ Success Rate:                                  │
│   │   Attempt 1: 60%                               │
│   │   Attempt 2: 70%                               │
│   │   Attempt 3: 75%                               │
│   └────────────────────────────────────────────────┘
│   If all attempts fail: Return best result with warning
│
├─► 7. Save to DynamoDB (One Item Per Executive)
│   Table: CompanyCXOData
│   For each executive:
│     Item: {
│       "company_id": "apple_inc",
│       "executive_id": "apple_inc_1_2025-10-14T10:35:00",
│       "extraction_timestamp": "2025-10-14T10:35:00",
│       "name": "Tim Cook",
│       "title": "Chief Executive Officer",
│       [... other fields ...],
│       "extraction_source": "cxo_website_extractor",
│       "website_source": "https://apple.com/leadership"
│     }
│   Total Items: 14 (one per executive)
│   Result: Success
│
├─► 8. Save Local Copy (If not in Lambda)
│   File: cxo_nova_extractions/apple_cxo_extraction_20251014.json
│   Skipped in Lambda (read-only filesystem)
│
└─► 9. Return Result
    Output: {
      "statusCode": 200,
      "body": {
        "status": "success",
        "company_name": "Apple Inc",
        "company_id": "apple_inc",
        "executives_count": 14,
        "completeness": 96.8,
        "role_categories": {
          "C-Suite": 5,
          "VP": 7,
          "Director": 2
        },
        "attempts": 1,
        "execution_time": 62
      }
    }

END Lambda Handler
```

---

## AWS Infrastructure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS INFRASTRUCTURE MAP                               │
└─────────────────────────────────────────────────────────────────────────────┘

Region: us-east-1

┌─────────────────────────────────────────────────────────────────────────────┐
│ VPC: Default VPC                                                             │
│ CIDR: 172.31.0.0/16                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Subnet: us-east-1a                                                    │  │
│  │ CIDR: 172.31.0.0/20                                                   │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │ Lambda Function: NovaSECExtractor                            │   │  │
│  │  │ • ENI: eni-xxx (172.31.x.x)                                  │   │  │
│  │  │ • Security Group: default                                    │   │  │
│  │  │ • Internet Access: Yes (NAT Gateway)                         │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │ Lambda Function: CXOWebsiteExtractor                         │   │  │
│  │  │ • ENI: eni-yyy (172.31.x.x)                                  │   │  │
│  │  │ • Security Group: default                                    │   │  │
│  │  │ • Internet Access: Yes (NAT Gateway)                         │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │ Lambda Function: DynamoDBToS3Merger                          │   │  │
│  │  │ • ENI: eni-zzz (172.31.x.x)                                  │   │  │
│  │  │ • Security Group: default                                    │   │  │
│  │  │ • Internet Access: Not required (VPC endpoints available)    │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ IAM Roles & Policies                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Role 1: LambdaCompanyExtractionRole                                         │
│  ├─ Trust: lambda.amazonaws.com                                              │
│  └─ Policies:                                                                │
│     ├─ AWS Managed: AWSLambdaBasicExecutionRole                              │
│     └─ Custom Inline:                                                        │
│        {                                                                     │
│          "Statement": [                                                      │
│            {                                                                 │
│              "Effect": "Allow",                                              │
│              "Action": [                                                     │
│                "bedrock:InvokeModel",                                        │
│                "bedrock:InvokeModelWithResponseStream"                       │
│              ],                                                              │
│              "Resource": "arn:aws:bedrock:*::foundation-model/*"             │
│            },                                                                │
│            {                                                                 │
│              "Effect": "Allow",                                              │
│              "Action": [                                                     │
│                "dynamodb:PutItem",                                           │
│                "dynamodb:Query",                                             │
│                "dynamodb:Scan"                                               │
│              ],                                                              │
│              "Resource": [                                                   │
│                "arn:aws:dynamodb:*:*:table/CompanySECData",                  │
│                "arn:aws:dynamodb:*:*:table/CompanyCXOData"                   │
│              ]                                                               │
│            },                                                                │
│            {                                                                 │
│              "Effect": "Allow",                                              │
│              "Action": ["s3:PutObject"],                                     │
│              "Resource": "arn:aws:s3:::company-sec-cxo-data-diligent/*"      │
│            },                                                                │
│            {                                                                 │
│              "Effect": "Allow",                                              │
│              "Action": [                                                     │
│                "logs:CreateLogGroup",                                        │
│                "logs:CreateLogStream",                                       │
│                "logs:PutLogEvents"                                           │
│              ],                                                              │
│              "Resource": "arn:aws:logs:*:*:*"                                │
│            }                                                                 │
│          ]                                                                   │
│        }                                                                     │
│                                                                              │
│  Role 2: CompanyDataExtractionStepFunctionRole                               │
│  ├─ Trust: states.amazonaws.com                                              │
│  └─ Policies:                                                                │
│     └─ Custom Inline:                                                        │
│        {                                                                     │
│          "Statement": [                                                      │
│            {                                                                 │
│              "Effect": "Allow",                                              │
│              "Action": ["lambda:InvokeFunction"],                            │
│              "Resource": [                                                   │
│                "arn:aws:lambda:*:*:function:NovaSECExtractor",               │
│                "arn:aws:lambda:*:*:function:CXOWebsiteExtractor",            │
│                "arn:aws:lambda:*:*:function:DynamoDBToS3Merger"              │
│              ]                                                               │
│            },                                                                │
│            {                                                                 │
│              "Effect": "Allow",                                              │
│              "Action": [                                                     │
│                "logs:CreateLogDelivery",                                     │
│                "logs:GetLogDelivery",                                        │
│                "logs:UpdateLogDelivery",                                     │
│                "logs:DeleteLogDelivery",                                     │
│                "logs:ListLogDeliveries",                                     │
│                "logs:PutResourcePolicy",                                     │
│                "logs:DescribeResourcePolicies",                              │
│                "logs:DescribeLogGroups"                                      │
│              ],                                                              │
│              "Resource": "*"                                                 │
│            }                                                                 │
│          ]                                                                   │
│        }                                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ CloudWatch Logs                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  /aws/lambda/NovaSECExtractor                                                │
│  ├─ Retention: 7 days                                                        │
│  ├─ Size: ~50 MB                                                             │
│  └─ Contains: Lambda execution logs, errors, timing                          │
│                                                                              │
│  /aws/lambda/CXOWebsiteExtractor                                             │
│  ├─ Retention: 7 days                                                        │
│  ├─ Size: ~60 MB                                                             │
│  └─ Contains: Lambda execution logs, errors, timing                          │
│                                                                              │
│  /aws/lambda/DynamoDBToS3Merger                                              │
│  ├─ Retention: 7 days                                                        │
│  ├─ Size: ~20 MB                                                             │
│  └─ Contains: Lambda execution logs, errors, timing                          │
│                                                                              │
│  /aws/vendedlogs/states/CompanyDataExtractionPipeline                        │
│  ├─ Retention: 30 days                                                       │
│  ├─ Size: ~100 MB                                                            │
│  └─ Contains: Step Function execution logs, state transitions                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Cost Breakdown (Monthly, assuming 1000 executions)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Lambda                                                                      │
│  ├─ Compute: 1000 × 3 × $0.0000008 × 60s = $2.40                            │
│  └─ Requests: 1000 × 3 × $0.0000002 = $0.60                                 │
│     Total Lambda: $3.00/month                                                │
│                                                                              │
│  Step Functions                                                              │
│  └─ State Transitions: 1000 × 8 × $0.000025 = $0.20                         │
│     Total Step Functions: $0.20/month                                        │
│                                                                              │
│  DynamoDB (On-Demand)                                                        │
│  ├─ Writes: 1000 × 15 × $0.00000125 = $0.02                                 │
│  └─ Reads: 1000 × 15 × $0.00000025 = $0.004                                 │
│     Total DynamoDB: $0.02/month                                              │
│                                                                              │
│  S3                                                                          │
│  ├─ Storage: 10 GB × $0.023 = $0.23                                         │
│  └─ Requests: 2000 × $0.000005 = $0.01                                      │
│     Total S3: $0.24/month                                                    │
│                                                                              │
│  CloudWatch Logs                                                             │
│  └─ Ingestion: 0.5 GB × $0.50 = $0.25                                       │
│     Total CloudWatch: $0.25/month                                            │
│                                                                              │
│  External APIs (per execution)                                               │
│  ├─ Serper: 2 × $0.022 = $0.044                                             │
│  └─ Bedrock Nova Pro: 2 × $0.03 = $0.06                                     │
│     Total External: $0.104 × 1000 = $104/month                              │
│                                                                              │
│  TOTAL: $107.91/month (1000 executions)                                     │
│  Per Execution: ~$0.108                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERROR HANDLING ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ SEC Extraction Error Handling                                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step Function Level:                                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ ExtractSECData (Task State)                                           │ │
│  │                                                                       │ │
│  │ Retry Configuration:                                                  │ │
│  │   {                                                                   │ │
│  │     "ErrorEquals": ["Lambda.ServiceException",                        │ │
│  │                     "Lambda.TooManyRequestsException"],               │ │
│  │     "IntervalSeconds": 2,                                             │ │
│  │     "MaxAttempts": 2,                                                 │ │
│  │     "BackoffRate": 2.0                                                │ │
│  │   }                                                                   │ │
│  │                                                                       │ │
│  │   Retry Timeline:                                                     │ │
│  │   Attempt 1: Immediate                                                │ │
│  │   Attempt 2: +2s (after 2s wait)                                      │ │
│  │   Attempt 3: +4s (after 4s wait, 2×2)                                 │ │
│  │                                                                       │ │
│  │ Catch Configuration:                                                  │ │
│  │   {                                                                   │ │
│  │     "ErrorEquals": ["States.Timeout"],                                │ │
│  │     "ResultPath": "$.sec_timeout",                                    │ │
│  │     "Next": "SECExtractionFailed"                                     │ │
│  │   },                                                                  │ │
│  │   {                                                                   │ │
│  │     "ErrorEquals": ["States.ALL"],                                    │ │
│  │     "ResultPath": "$.sec_error",                                      │ │
│  │     "Next": "SECExtractionFailed"                                     │ │
│  │   }                                                                   │ │
│  │                                                                       │ │
│  │ Possible Errors:                                                      │ │
│  │   • Lambda.ServiceException → Retry (AWS issue)                       │ │
│  │   • Lambda.TooManyRequestsException → Retry (throttling)              │ │
│  │   • States.Timeout → Fail (execution > 360s)                          │ │
│  │   • States.ALL → Fail (other errors)                                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Lambda Level:                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ nova_sec_extractor.py                                                 │ │
│  │                                                                       │ │
│  │ Try-Catch Blocks:                                                     │ │
│  │   1. Serper API Errors                                                │ │
│  │      • Connection timeout → Retry with fallback query                 │ │
│  │      • Rate limit → Wait 60s, retry                                   │ │
│  │      • Invalid response → Log, continue with available data           │ │
│  │                                                                       │ │
│  │   2. Bedrock API Errors                                               │ │
│  │      • ModelNotFound → Return error 500                               │ │
│  │      • Throttling → Retry with exponential backoff                    │ │
│  │      • Invalid JSON → Parse partial, flag incomplete                  │ │
│  │                                                                       │ │
│  │   3. DynamoDB Errors                                                  │ │
│  │      • ProvisionedThroughputExceeded → Retry 3x                       │ │
│  │      • ResourceNotFound → Create table (if local)                     │ │
│  │      • ValidationException → Log schema error, fail                   │ │
│  │                                                                       │ │
│  │   4. Completeness Validation                                          │ │
│  │      • < 95% → Retry extraction (max 3 attempts)                      │ │
│  │      • Still < 95% → Return with warning                              │ │
│  │                                                                       │ │
│  │ Error Response Format:                                                │ │
│  │   {                                                                   │ │
│  │     "statusCode": 500,                                                │ │
│  │     "body": {                                                         │ │
│  │       "status": "error",                                              │ │
│  │       "error_type": "SerperAPIError",                                 │ │
│  │       "message": "Failed to search SEC documents",                    │ │
│  │       "company_name": "Apple Inc",                                    │ │
│  │       "retry_recommended": true                                       │ │
│  │     }                                                                 │ │
│  │   }                                                                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ Merge Error Handling (Future Enhancement - Phase 0)                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Current State: ❌ NO ERROR HANDLING                                        │
│  Issue: If merge fails, entire pipeline fails with unhandled error         │
│                                                                             │
│  Planned Enhancement:                                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ MergeAndSaveToS3 (Task State)                                         │ │
│  │                                                                       │ │
│  │ Retry Configuration:                                                  │ │
│  │   {                                                                   │ │
│  │     "ErrorEquals": ["States.TaskFailed"],                             │ │
│  │     "IntervalSeconds": 2,                                             │ │
│  │     "MaxAttempts": 2,                                                 │ │
│  │     "BackoffRate": 2.0                                                │ │
│  │   }                                                                   │ │
│  │                                                                       │ │
│  │ Catch Configuration: (TO BE ADDED)                                    │ │
│  │   {                                                                   │ │
│  │     "ErrorEquals": ["States.Timeout"],                                │ │
│  │     "ResultPath": "$.merge_timeout",                                  │ │
│  │     "Next": "MergeFailed"                                             │ │
│  │   },                                                                  │ │
│  │   {                                                                   │ │
│  │     "ErrorEquals": ["States.ALL"],                                    │ │
│  │     "ResultPath": "$.merge_error",                                    │ │
│  │     "Next": "MergeFailed"                                             │ │
│  │   }                                                                   │ │
│  │                                                                       │ │
│  │ MergeFailed (Fail State): (TO BE ADDED)                               │ │
│  │   {                                                                   │ │
│  │     "Type": "Fail",                                                   │ │
│  │     "Error": "MergeError",                                            │ │
│  │     "Cause": "Failed to merge SEC and CXO data"                       │ │
│  │   }                                                                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Impact: Prevents unhandled failures, better debugging                      │
│  Effort: 5 minutes                                                          │
│  Priority: CRITICAL                                                         │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ Logging & Monitoring                                                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Current State: ⚠️ MINIMAL LOGGING                                          │
│  ├─ Lambda logs: Yes (stdout/stderr)                                        │
│  ├─ Step Function logs: No (not configured)                                 │
│  ├─ Custom metrics: No                                                      │
│  └─ Alerts: No                                                              │
│                                                                             │
│  Planned Enhancement (Phase 0):                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ CloudWatch Logs Configuration                                         │ │
│  │                                                                       │ │
│  │ Step Function:                                                        │ │
│  │   loggingConfiguration:                                               │ │
│  │     level: "ALL"                                                      │ │
│  │     includeExecutionData: true                                        │ │
│  │     destinations:                                                     │ │
│  │       - logGroupArn: "/aws/vendedlogs/states/..."                    │ │
│  │                                                                       │ │
│  │ Log Structure:                                                        │ │
│  │   {                                                                   │ │
│  │     "execution_started": {...},                                       │ │
│  │     "state_entered": "ExtractSECData",                                │ │
│  │     "state_exited": "ExtractSECData",                                 │ │
│  │     "output": {...},                                                  │ │
│  │     "execution_succeeded": {...}                                      │ │
│  │   }                                                                   │ │
│  │                                                                       │ │
│  │ Benefits:                                                             │ │
│  │   • Full visibility into execution                                    │ │
│  │   • Debugging failed executions                                       │ │
│  │   • Audit trail for compliance                                        │ │
│  │   • Performance analysis                                              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Effort: 15 minutes                                                         │
│  Priority: CRITICAL                                                         │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DEPLOYMENT ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Development Environment
┌────────────────────────────────────────────────────────────────────────────┐
│ Local Machine                                                               │
│ ├─ Python 3.11                                                              │
│ ├─ AWS CLI                                                                  │
│ ├─ boto3                                                                    │
│ └─ .env file (SERPER_API_KEY, AWS credentials)                              │
│                                                                             │
│ Project Structure:                                                          │
│ STEPSCREEN/                                                                 │
│ ├── nova_sec_extractor.py         (Core SEC extractor)                     │
│ ├── cxo_website_extractor.py      (Core CXO extractor)                     │
│ ├── merge_and_save_to_s3.py       (Merge logic)                            │
│ ├── stepfunction_definition.json  (State machine definition)               │
│ ├── deploy_stepfunction.py        (Deploy state machine)                   │
│ ├── test_stepfunction.py          (Test executions)                        │
│ ├── requirements.txt               (Python dependencies)                   │
│ ├── .env                           (Environment variables - IGNORED)       │
│ ├── .gitignore                     (Git ignore rules)                      │
│ │                                                                           │
│ ├── lambda/                        (Lambda deployment artifacts)           │
│ │   ├── lambda_nova_sec_handler.py                                         │
│ │   ├── lambda_cxo_handler.py                                              │
│ │   ├── lambda_merge_handler.py                                            │
│ │   ├── deploy_lambda_nova_sec.py                                          │
│ │   ├── deploy_lambda_cxo.py                                               │
│ │   ├── deploy_lambda_merge.py                                             │
│ │   ├── lambda_requirements.txt                                            │
│ │   ├── lambda_nova_sec_deployment.zip (17 MB)                             │
│ │   ├── lambda_cxo_deployment.zip (17 MB)                                  │
│ │   └── lambda_merge_deployment.zip (15 MB)                                │
│ │                                                                           │
│ └── doc/                           (Documentation)                         │
│     ├── MASTER_IMPROVEMENT_PLAN.md                                         │
│     ├── SYSTEM_ARCHITECTURE.md     ← THIS FILE                             │
│     ├── NOVA_SEC_ACCURACY_ANALYSIS.md                                      │
│     ├── CXO_WEBSITE_ACCURACY_ANALYSIS.md                                   │
│     ├── STEPFUNCTION_ARCHITECTURE_ANALYSIS.md                              │
│     ├── STEPFUNCTION_EFFICIENCY_OPTIMIZATIONS.md                           │
│     └── PRODUCTION_READINESS.md                                            │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

Deployment Flow
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│ Step 1: Deploy Lambda Functions                                            │
│ ─────────────────────────────────                                          │
│   $ cd lambda                                                               │
│   $ python deploy_lambda_nova_sec.py                                       │
│   $ python deploy_lambda_cxo.py                                            │
│   $ python deploy_lambda_merge.py                                          │
│                                                                             │
│   Each script:                                                              │
│   1. Creates deployment package (ZIP)                                       │
│      • Copies handler + core extractor                                      │
│      • Installs dependencies                                                │
│      • Creates ZIP (~17 MB)                                                 │
│   2. Creates/updates IAM role                                               │
│      • Attaches policies                                                    │
│      • Waits for role propagation                                           │
│   3. Creates/updates Lambda function                                        │
│      • Uploads ZIP                                                          │
│      • Sets environment variables                                           │
│      • Configures memory/timeout                                            │
│   4. Tests invocation                                                       │
│      • Warmup call                                                          │
│      • Verifies success                                                     │
│                                                                             │
│ Step 2: Deploy DynamoDB Tables (If not exists)                             │
│ ───────────────────────────────────────────                                │
│   $ python setup_dynamodb.py                                                │
│                                                                             │
│   Creates:                                                                  │
│   • CompanySECData (PK: company_id, SK: extraction_timestamp)               │
│   • CompanyCXOData (PK: company_id, SK: executive_id)                       │
│                                                                             │
│ Step 3: Deploy S3 Bucket (If not exists)                                   │
│ ──────────────────────────────────────                                     │
│   $ python setup_s3.py                                                      │
│                                                                             │
│   Creates:                                                                  │
│   • company-sec-cxo-data-diligent                                           │
│   • Enables versioning                                                      │
│   • Sets lifecycle policy                                                   │
│                                                                             │
│ Step 4: Deploy Step Function                                               │
│ ──────────────────────────────                                             │
│   $ python deploy_stepfunction.py                                          │
│                                                                             │
│   1. Creates IAM role for Step Function                                     │
│   2. Loads stepfunction_definition.json                                     │
│   3. Creates/updates state machine                                          │
│   4. Configures CloudWatch logging                                          │
│   5. Returns execution ARN                                                  │
│                                                                             │
│ Step 5: Test Execution                                                     │
│ ───────────────────                                                        │
│   $ python test_stepfunction.py "Apple Inc" "https://apple.com" "AAPL"     │
│                                                                             │
│   1. Starts Step Function execution                                         │
│   2. Polls for completion                                                   │
│   3. Displays results                                                       │
│   4. Shows execution logs                                                   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

AWS Production Environment
┌────────────────────────────────────────────────────────────────────────────┐
│ Account: 891067072053                                                       │
│ Region: us-east-1                                                           │
│ Profile: diligent                                                           │
│                                                                             │
│ Deployed Resources:                                                         │
│ ├─ Lambda Functions: 3                                                      │
│ │  ├─ NovaSECExtractor                                                      │
│ │  ├─ CXOWebsiteExtractor                                                   │
│ │  └─ DynamoDBToS3Merger                                                    │
│ │                                                                           │
│ ├─ DynamoDB Tables: 2                                                       │
│ │  ├─ CompanySECData                                                        │
│ │  └─ CompanyCXOData                                                        │
│ │                                                                           │
│ ├─ S3 Buckets: 1                                                            │
│ │  └─ company-sec-cxo-data-diligent                                         │
│ │                                                                           │
│ ├─ Step Functions: 1                                                        │
│ │  └─ CompanyDataExtractionPipeline                                         │
│ │                                                                           │
│ ├─ IAM Roles: 2                                                             │
│ │  ├─ LambdaCompanyExtractionRole                                           │
│ │  └─ CompanyDataExtractionStepFunctionRole                                 │
│ │                                                                           │
│ └─ CloudWatch Log Groups: 4                                                 │
│    ├─ /aws/lambda/NovaSECExtractor                                          │
│    ├─ /aws/lambda/CXOWebsiteExtractor                                       │
│    ├─ /aws/lambda/DynamoDBToS3Merger                                        │
│    └─ /aws/vendedlogs/states/CompanyDataExtractionPipeline                  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Summary

### Typical Execution Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Total Duration** | 71-92 seconds | Depends on company size |
| **SEC Extraction** | 45-47 seconds | Includes search + extraction |
| **CXO Extraction** | 60-62 seconds | Includes page fetch + extraction |
| **Merge** | 7-9 seconds | Query DynamoDB + S3 upload |
| **Cold Start Overhead** | 6 seconds total | 2s per Lambda × 3 |
| **Cost per Execution** | $0.055 | Mostly external APIs |
| **Success Rate** | ~75% | Current (target: 95%+) |
| **Completeness** | 60-65% | Current (target: 95%+) |

### Performance Bottlenecks

1. **Nova Pro Inference**: 30-35s per extraction (60% of total time)
2. **Serper API**: 5-10s per search (10% of total time)
3. **Lambda Cold Starts**: 2s per Lambda (7% overhead)
4. **Idle Wait Time**: 15s (16% wasted - unbalanced loads)
5. **Page Fetching**: 10-15s (CXO only)

---

**Document Version:** 1.0  
**Last Updated:** October 14, 2025  
**Status:** Current Architecture  
**Author:** System Architecture Documentation

