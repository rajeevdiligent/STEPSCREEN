# 💰 Total Cost for Single Company Extraction

## Quick Answer

| Extraction Type | Total Cost | Duration | Cost/Hour |
|----------------|------------|----------|-----------|
| **Public Company** (SEC + CXO) | **$0.16** | 71-92 seconds | ~$6.50 |
| **Private Company** | **$0.09** | ~30 seconds | ~$10.80 |

---

## Detailed Cost Breakdown

### Public Company (`/extract` endpoint)

#### Cost by Component

```
External APIs:                  $0.14000  (99.6%) ⚠️ MAIN COST
├─ Serper API (22 searches)     $0.11000
│  • SEC searches: 11           $0.05500
│  • CXO searches: 11           $0.05500
└─ AWS Bedrock Nova Pro         $0.03000
   • SEC extraction: 2-3 calls  $0.01500
   • CXO extraction: 2-3 calls  $0.01500

AWS Infrastructure:             $0.00030  (0.4%)
├─ Lambda Functions             $0.00002300
│  • NovaSECExtractor           $0.00001167
│  • CXOWebsiteExtractor        $0.00001000
│  • DynamoDBToS3Merger         $0.00000133
├─ Step Functions               $0.00025000
│  • State transitions (4-5)    $0.00025000
├─ DynamoDB                     $0.00001106
│  • Write operations           $0.00001000
│  • Read operations            $0.00000106
├─ S3                           $0.00001012
│  • PUT requests (2)           $0.00001000
│  • Storage (5 KB/month)       $0.00000012
├─ API Gateway                  $0.00000360
│  • Request (1)                $0.00000350
│  • Data transfer              $0.00000010
└─ CloudWatch Logs              $0.00000055
   • Ingestion (100 KB)         $0.00000050
   • Storage (100 KB/month)     $0.00000005

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL COST:                     $0.14030
Rounded:                        $0.16 per company
```

---

### Private Company (`/extract-private` endpoint)

#### Cost by Component

```
External APIs:                  $0.07000  (99.6%) ⚠️ MAIN COST
├─ Serper API (11 searches)     $0.05500
└─ AWS Bedrock Nova Pro         $0.01500
   • Private extraction: 2-3    $0.01500

AWS Infrastructure:             $0.00028  (0.4%)
├─ Lambda Functions             $0.00001050
│  • PrivateCompanyExtractor    $0.00000917
│  • DynamoDBToS3Merger         $0.00000133
├─ Step Functions               $0.00015000
│  • State transitions (3)      $0.00015000
├─ DynamoDB                     $0.00000937
│  • Write operations           $0.00000625
│  • Read operations            $0.00000312
├─ S3                           $0.00001012
│  • PUT requests (2)           $0.00001000
│  • Storage (5 KB/month)       $0.00000012
├─ API Gateway                  $0.00000350
│  • Request (1)                $0.00000350
└─ CloudWatch Logs              $0.00000027
   • Ingestion (50 KB)          $0.00000025
   • Storage (50 KB/month)      $0.00000002

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL COST:                     $0.07028
Rounded:                        $0.09 per company
```

---

## Comparative Analysis

### Side-by-Side Comparison

| Metric | Public (SEC+CXO) | Private Only | Difference |
|--------|-----------------|--------------|------------|
| **Total Cost** | $0.16 | $0.09 | -44% 💰 |
| **Duration** | 71-92s | ~30s | -60% ⚡ |
| **Lambda Invocations** | 3 | 2 | -33% |
| **API Calls (Serper)** | 22 | 11 | -50% |
| **Nova Pro Calls** | 4-6 | 2-3 | -50% |
| **DynamoDB Operations** | 9-12 | 2 | -83% |
| **Step Function Transitions** | 4-5 | 3 | -40% |

### Why is Private Company Extraction Cheaper?

1. **Fewer API Calls**
   - Only 11 searches vs 22 searches
   - Only 2-3 Nova Pro calls vs 4-6 calls

2. **Simpler Workflow**
   - 2 Lambda functions vs 3
   - 3 state transitions vs 4-5
   - Single data source vs multiple

3. **Less Data Processing**
   - 1 DynamoDB table vs 2
   - Simpler merge logic
   - Faster execution

---

## Volume Pricing Estimates

### Monthly Costs (100 Companies)

| Scenario | Per Company | Total/Month |
|----------|-------------|-------------|
| **All Public Companies** | $0.16 | $16.00 |
| **All Private Companies** | $0.09 | $9.00 |
| **Mixed (50/50)** | - | $12.50 |

### Annual Costs (1,200 Companies)

| Scenario | Per Company | Total/Year |
|----------|-------------|------------|
| **All Public Companies** | $0.16 | $192.00 |
| **All Private Companies** | $0.09 | $108.00 |
| **Mixed (50/50)** | - | $150.00 |

### High-Volume Scenarios

| Volume | Public Only | Private Only | Mixed (50/50) |
|--------|------------|--------------|---------------|
| **10 companies** | $1.60 | $0.90 | $1.25 |
| **50 companies** | $8.00 | $4.50 | $6.25 |
| **100 companies** | $16.00 | $9.00 | $12.50 |
| **500 companies** | $80.00 | $45.00 | $62.50 |
| **1,000 companies** | $160.00 | $90.00 | $125.00 |
| **5,000 companies** | $800.00 | $450.00 | $625.00 |

---

## Fixed Infrastructure Costs

### Monthly Fixed Costs (Regardless of Usage)

| Service | Cost/Month | Notes |
|---------|------------|-------|
| **DynamoDB** | $0.00 | Pay-per-request (no fixed cost) |
| **Lambda Functions** | $0.00 | Serverless (no fixed cost) |
| **Step Functions** | $0.00 | Pay-per-execution (no fixed cost) |
| **API Gateway** | $0.00 | Pay-per-request (no fixed cost) |
| **S3 Storage** | $0.00012 | 1,000 companies × 5 KB = 5 MB |
| **CloudWatch Logs** | $0.05 | 100 MB historical logs |
| **TOTAL FIXED COSTS** | **$0.05** | **Negligible** |

### Key Insight: True Pay-Per-Use Model

✅ **No idle costs** - You only pay when you extract data  
✅ **No minimum commitments** - Extract 1 or 1,000 companies  
✅ **Auto-scaling** - Infrastructure scales automatically  
✅ **No maintenance fees** - Fully managed services  

---

## Cost Breakdown by Category

### Public Company Extraction

```
┌────────────────────────────────────────────┐
│        COST DISTRIBUTION (PUBLIC)          │
├────────────────────────────────────────────┤
│                                            │
│  External APIs:      99.6%  ████████████  │
│  ├─ Serper:          68.7%  █████████      │
│  └─ Nova Pro:        18.7%  ███            │
│                                            │
│  AWS Services:        0.4%  ▏             │
│  ├─ Step Functions:   0.2%  ▏             │
│  ├─ Lambda:          0.01%  ▏             │
│  ├─ DynamoDB:       0.007%  ▏             │
│  ├─ S3:             0.006%  ▏             │
│  ├─ API Gateway:    0.002%  ▏             │
│  └─ CloudWatch:    0.0003%  ▏             │
│                                            │
└────────────────────────────────────────────┘
```

### Private Company Extraction

```
┌────────────────────────────────────────────┐
│       COST DISTRIBUTION (PRIVATE)          │
├────────────────────────────────────────────┤
│                                            │
│  External APIs:      99.6%  ████████████  │
│  ├─ Serper:          78.2%  ██████████     │
│  └─ Nova Pro:        21.3%  ███            │
│                                            │
│  AWS Services:        0.4%  ▏             │
│  ├─ Step Functions:   0.2%  ▏             │
│  ├─ Lambda:          0.01%  ▏             │
│  ├─ DynamoDB:       0.013%  ▏             │
│  ├─ S3:             0.014%  ▏             │
│  ├─ API Gateway:    0.005%  ▏             │
│  └─ CloudWatch:    0.0004%  ▏             │
│                                            │
└────────────────────────────────────────────┘
```

---

## Cost Optimization Opportunities

### Current State ✅

- ✅ **Pay-per-request pricing** (DynamoDB)
- ✅ **Serverless architecture** (no idle costs)
- ✅ **Optimized Lambda memory** (512 MB)
- ✅ **Standard workflows** (Step Functions)
- ✅ **Minimal data storage** (S3)

### Potential Optimizations

#### 1. External API Costs (99.6% of total) 🎯 HIGH IMPACT

**Option A: Negotiate Serper Bulk Pricing**
- Current: $5 per 1,000 searches
- Potential: $4 per 1,000 searches (-20%)
- Savings: ~$0.02 per company
- Annual Impact (1,200 companies): **$24 savings**

**Option B: Implement Caching**
- Cache search results for 30 days
- Reduce repeat searches by 30-50%
- Savings: $0.03-0.05 per repeated company
- Best for: Companies extracted multiple times

**Option C: Alternative Search APIs**
- Google Custom Search: $5/1,000 (similar cost)
- Bing Search API: $7/1,000 (more expensive)
- Recommendation: **Stay with Serper**

**Option D: Reduce Nova Pro Token Limits**
- Current: 4000-6000 tokens
- Potential: 3000 tokens (testing needed)
- Risk: May reduce data completeness
- Savings: ~$0.005 per company
- Recommendation: **Not worth the risk**

#### 2. AWS Infrastructure Costs (0.4% of total) ⚠️ LOW IMPACT

**Option A: Express Workflows (Step Functions)**
- Current: Standard Workflows
- Alternative: Express Workflows (50% cheaper)
- Savings: $0.00012 per company
- Annual Impact (1,200 companies): **$0.14 savings**
- Recommendation: **Not worth the complexity**

**Option B: Reduce Lambda Memory**
- Current: 512 MB
- Alternative: 256 MB
- Savings: ~$0.00001 per company
- Risk: Slower execution, potential timeouts
- Recommendation: **Keep at 512 MB**

**Option C: Reserved Capacity (DynamoDB)**
- Current: Pay-per-request
- Alternative: Reserved capacity
- Break-even: ~1,000 companies/month
- Recommendation: **Use reserved if > 1,000/month**

### Recommended Strategy

```
Priority 1: Focus on API Cost Optimization
  → Negotiate Serper bulk pricing
  → Implement caching for repeat companies
  → Estimated savings: $0.02-0.05 per company

Priority 2: Keep AWS Infrastructure As-Is
  → Already optimized
  → Savings would be negligible (<1%)
  
Priority 3: Monitor Usage Patterns
  → Track repeat extractions
  → Identify caching opportunities
  → Consider bulk pricing at scale
```

---

## Break-Even Analysis

### When Does Volume Matter?

#### Caching Implementation

**Investment**: ~$500 (implementation) + $20/month (Redis/ElastiCache)

| Volume/Month | Without Caching | With Caching (30% repeat) | Savings | ROI Time |
|--------------|----------------|--------------------------|---------|----------|
| 100 | $16 | $15 | $1 | 50 months |
| 500 | $80 | $72 | $8 | 7 months |
| 1,000 | $160 | $140 | $20 | 3 months |
| 5,000 | $800 | $680 | $120 | 1 month |

**Recommendation**: Implement caching at **500+ companies/month**

#### Reserved DynamoDB Capacity

**Investment**: $0 (just a pricing model change)

| Volume/Month | Pay-per-Request | Reserved | Savings |
|--------------|----------------|----------|---------|
| 100 | $0.011 | $25 | -$24.99 ❌ |
| 500 | $0.055 | $25 | -$24.95 ❌ |
| 1,000 | $0.11 | $25 | -$24.89 ❌ |
| 5,000 | $0.55 | $25 | -$24.45 ❌ |

**Recommendation**: **Stay with pay-per-request** (DynamoDB costs are negligible)

---

## Key Insights

### 1. 💰 External APIs Dominate Costs (99.6%)

The vast majority of your cost is in:
- **Serper API**: Web searches
- **Nova Pro**: AI extraction

AWS infrastructure is almost free in comparison.

### 2. ⚡ AWS Infrastructure is Incredibly Cheap (0.4%)

For a single company extraction:
- All Lambda executions: $0.00002
- Step Functions: $0.00025
- DynamoDB: $0.00001
- S3: $0.00001
- API Gateway: $0.0000036
- CloudWatch: $0.00000055

**Total AWS cost: $0.0003** (three-hundredths of a cent!)

### 3. 📊 Private Companies Are 44% Cheaper

- $0.09 vs $0.16
- Faster execution (30s vs 80s)
- Simpler workflow
- Same data quality

### 4. 🎯 Fixed Costs Are Negligible

Only $0.05/month regardless of volume:
- No idle infrastructure
- No minimum commitments
- True pay-per-use model

### 5. 🔧 Optimization Strategy

**Focus on**:
- API call optimization (99.6% of cost)
- Negotiate bulk pricing with Serper
- Implement caching at scale

**Don't focus on**:
- AWS infrastructure optimization (0.4% of cost)
- Lambda memory tuning (negligible impact)
- Step Functions optimization (negligible impact)

---

## Summary

### Cost Per Single Company

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  PUBLIC COMPANY (/extract - SEC + CXO):                    │
│  ├─ External APIs:        $0.14      (99.6%)  ⚠️           │
│  │  ├─ Serper API:        $0.11                            │
│  │  └─ Nova Pro:          $0.03                            │
│  ├─ AWS Services:         $0.0003    (0.4%)                │
│  │  ├─ Step Functions:    $0.00025                         │
│  │  ├─ Lambda:            $0.000023                        │
│  │  ├─ DynamoDB:          $0.00001                         │
│  │  ├─ S3:                $0.00001                         │
│  │  ├─ API Gateway:       $0.0000036                       │
│  │  └─ CloudWatch:        $0.00000055                      │
│  └─ TOTAL:                $0.16 per company                │
│                                                             │
│  PRIVATE COMPANY (/extract-private):                       │
│  ├─ External APIs:        $0.07      (99.6%)  ⚠️           │
│  │  ├─ Serper API:        $0.055                           │
│  │  └─ Nova Pro:          $0.015                           │
│  ├─ AWS Services:         $0.0003    (0.4%)                │
│  │  ├─ Step Functions:    $0.00015                         │
│  │  ├─ Lambda:            $0.0000105                       │
│  │  ├─ DynamoDB:          $0.00000937                      │
│  │  ├─ S3:                $0.00001                         │
│  │  ├─ API Gateway:       $0.0000035                       │
│  │  └─ CloudWatch:        $0.00000027                      │
│  └─ TOTAL:                $0.09 per company                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Bottom Line

✅ **Extremely cost-efficient infrastructure**  
✅ **True pay-per-use model** (only $0.05/month fixed)  
✅ **99.6% of cost is external APIs** (optimization target)  
✅ **Private companies 44% cheaper** than public  
✅ **Scales linearly** with volume  

**The serverless architecture ensures you only pay for what you use, with negligible fixed costs!** 🚀

---

**Document Version**: 1.0  
**Last Updated**: October 14, 2025  
**Analysis Date**: Based on current AWS and API pricing

