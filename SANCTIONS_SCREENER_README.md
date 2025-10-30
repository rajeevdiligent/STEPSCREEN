# 🛡️ Sanctions & Watchlist Screening Module

## Overview

The Sanctions Screener module performs comprehensive screening of companies and their executives against global sanctions lists, watchlists, and Politically Exposed Persons (PEP) databases.

---

## 📊 Data Sources

### Company Name Sources (Priority Order)

The screener retrieves company names from DynamoDB in the following priority:

1. **CompanySECData** - Public companies with SEC/regulatory filings
2. **CompanyPrivateData** - Private companies (alternative source)

### Executive Data Source

- **CompanyCXOData** - Executive profiles for all companies (both public and private)

### Sanctions Sources Checked

The module searches 7 comprehensive sanctions and watchlist sources in parallel:

| Source | Description | Priority |
|--------|-------------|----------|
| **OFAC SDN** | US Treasury - Specially Designated Nationals | 1 |
| **UN Sanctions** | United Nations Security Council Sanctions | 2 |
| **EU Sanctions** | European Union Restrictive Measures | 3 |
| **UK HMT** | UK Her Majesty's Treasury Sanctions | 4 |
| **FinCEN** | Financial Crimes Enforcement Network Watchlist | 5 |
| **Interpol** | Interpol Wanted/Red Notices | 6 |
| **PEP** | Politically Exposed Persons | 7 |

---

## 🔄 Workflow

```
Input: Company Name
    ↓
1. Query DynamoDB for Company Data
    ├─ Try CompanySECData (public companies)
    └─ Fallback to CompanyPrivateData (private companies)
    ↓
2. Query CompanyCXOData for Executives
    ↓
3. Screen Company
    ├─ Parallel searches across 7 sanctions sources
    └─ AI analysis via AWS Nova Pro
    ↓
4. Screen Each Executive
    ├─ Parallel searches across 7 sanctions sources
    └─ AI analysis via AWS Nova Pro
    ↓
5. Save Results to CompanySanctionsScreening
    ├─ Company matches
    ├─ Executive matches
    ├─ Confidence levels
    ├─ Source URLs
    └─ Data source tracking
```

---

## 📋 Output Format

### Match Criteria

For each potential match, the system provides:

| Field | Description | Example |
|-------|-------------|---------|
| **Match Type** | Which list/source | "OFAC SDN", "PEP", "Interpol" |
| **Confidence Level** | High / Medium / Low | "High" |
| **Confidence Justification** | 50-100 word explanation with evidence | "Exact name match with John Doe appearing on the OFAC SDN list with matching date of birth..." |
| **Match Reason** | Specific reason for match | "Exact name and DOB match on OFAC SDN List" |
| **Source** | Official source name | "OFAC SDN List" |
| **Source URL** | Direct URL (MANDATORY) | "https://sanctionssearch.ofac.treas.gov/..." |
| **Match Details** | Additional info | {"aliases": ["J. Doe"], "dob": "1975-03-15"} |

### Confidence Levels

- **High**: Exact name match + additional identifying information (DOB, address, passport, etc.)
- **Medium**: Strong name match with some context but missing key identifiers
- **Low**: Name similarity but significant uncertainty

---

## 💾 DynamoDB Schema

### Table: CompanySanctionsScreening

**Keys:**
- **company_id** (Partition Key) - Normalized company identifier
- **screening_id** (Sort Key) - Unique screening identifier (sanctions_YYYYMMDD_HHMMSS)

**Attributes:**
```json
{
  "company_id": "tesco_plc",
  "screening_id": "sanctions_20251030_071613",
  "company_name": "Tesco PLC",
  "screening_timestamp": "2025-10-30T07:16:13.399607",
  "data_source": "CompanySECData",
  "total_entities_screened": 4,
  "total_matches_found": 2,
  "company_matches": [],
  "executive_matches": [
    {
      "entity_name": "Alan Stewart",
      "entity_type": "individual",
      "match_type": "PEP",
      "confidence_level": "Medium",
      "confidence_justification": "Alan Stewart appears...",
      "match_reason": "Name match with government official records",
      "source": "Politically Exposed Persons Database",
      "source_url": "https://www.pep.org/...",
      "match_details": {...},
      "screened_date": "2025-10-30T07:16:13"
    }
  ]
}
```

---

## 🚀 Usage

### Command Line

```bash
python3 sanctions_screener.py "Company Name"
```

### Programmatic

```python
from sanctions_screener import SerperSanctionsSearcher

# Initialize screener
screener = SerperSanctionsSearcher(
    api_key="your_serper_api_key",
    aws_profile="diligent"
)

# Screen company and executives
result = screener.screen_company_and_executives("Tesco PLC")

# Access results
print(f"Total Matches: {result.total_matches_found}")
print(f"Company Matches: {len(result.company_matches)}")
print(f"Executive Matches: {len(result.executive_matches)}")
```

### AWS Lambda

```python
import json
from lambda_function import lambda_handler

# Invoke Lambda
event = {
    "company_name": "Tesco PLC"
}

response = lambda_handler(event, None)
body = json.loads(response['body'])

print(f"Matches Found: {body['total_matches_found']}")
```

---

## ⚡ Performance

### Typical Execution Times

| Company Type | Duration | Notes |
|--------------|----------|-------|
| Company only (no executives) | 10-15s | 7 parallel searches + Nova Pro analysis |
| Company + 3 executives | 40-50s | Sequential executive screening |
| Company + 10 executives | 120-150s | Sequential executive screening |

### Optimization Features

- ✅ **Parallel API Calls** - 7 sanctions sources searched simultaneously
- ✅ **AI-Powered Filtering** - AWS Nova Pro reduces false positives
- ✅ **Cached Results** - DynamoDB stores screening history
- ✅ **Efficient Queries** - Direct DynamoDB queries by company_id

---

## 📊 Current Database Status

As of 2025-10-30:

| Table | Companies | Executives | Status |
|-------|-----------|------------|--------|
| CompanySECData | 7 | N/A | ✅ Active |
| CompanyPrivateData | 0 | N/A | 📝 Empty (future use) |
| CompanyCXOData | 7 | 34 | ✅ Active |
| CompanySanctionsScreening | 7 | N/A | ✅ Active |

**Companies Ready for Screening:**
- ✅ apple_inc (5 executives)
- ✅ infosys_limited (6 executives)
- ✅ intel_corporation (9 executives)
- ✅ microsoft_corporation (4 executives)
- ✅ starbucks_corporation (3 executives)
- ✅ tesco_plc (3 executives)
- ✅ tesla_inc (4 executives)

---

## 🔧 Configuration

### Environment Variables

```bash
SERPER_API_KEY=your_serper_api_key_here
AWS_PROFILE=diligent
AWS_REGION=us-east-1
```

### Required AWS Permissions

- **DynamoDB**: Read access to CompanySECData, CompanyPrivateData, CompanyCXOData
- **DynamoDB**: Write access to CompanySanctionsScreening
- **Bedrock**: InvokeModel permission for Nova Pro (us.amazon.nova-pro-v1:0)

---

## 📝 Example Results

### Test Case: Tesco PLC

```
Company: Tesco PLC
Data Source: CompanySECData
Entities Screened: 4 (1 company + 3 executives)
Duration: 44.9 seconds

✅ Company: No matches

👥 Executives:
  1. Ken Murphy (CEO) - ✅ No matches
  2. Alan Stewart (CFO) - ⚠️  PEP Match (Medium Confidence)
  3. Melissa Bethell (Director) - ⚠️  PEP Match (Medium Confidence)

Total Matches Found: 2
```

---

## 🔮 Future Enhancements

1. **Batch Screening** - Screen multiple companies in one request
2. **Real-time Alerts** - Monitor for new sanctions matches
3. **Historical Tracking** - Track changes in sanctions status over time
4. **Custom Watchlists** - Add organization-specific screening lists
5. **Risk Scoring** - Aggregate risk scores based on all matches
6. **Automated Re-screening** - Periodic re-screening of all entities

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: "No data found for [company]"
- **Solution**: Verify company exists in CompanySECData or CompanyPrivateData
- **Check**: Run `python3 -c "import boto3; ...query DynamoDB..."`

**Issue**: "No executives found"
- **Solution**: Verify executives exist in CompanyCXOData for that company_id
- **Check**: Ensure company_id normalization matches

**Issue**: "SERPER_API_KEY not found"
- **Solution**: Set environment variable or create .env file
- **Command**: `export SERPER_API_KEY=your_key_here`

---

## 📞 Support

For questions or issues:
1. Check the troubleshooting section above
2. Review DynamoDB table contents
3. Check CloudWatch logs for Lambda executions
4. Verify Serper API quota and AWS Bedrock limits

---

## 🎯 Key Features

✅ **Comprehensive Coverage** - 7 global sanctions sources  
✅ **AI-Powered Analysis** - AWS Nova Pro reduces false positives  
✅ **Flexible Data Sources** - Supports both public and private companies  
✅ **Detailed Justifications** - Clear explanations for each match  
✅ **Source URLs** - Direct links to official sanctions listings  
✅ **High Performance** - Parallel API calls for speed  
✅ **Full Tracking** - Data source and timestamp tracking  
✅ **DynamoDB Storage** - Persistent screening history  

---

**Module Status**: ✅ Production Ready  
**Last Updated**: 2025-10-30  
**Version**: 1.0.0

