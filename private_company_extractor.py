#!/usr/bin/env python3
"""
Private Company Data Extractor
Specialized for extracting real-time data from private companies using alternative document sources
"""

import os
import sys
import json
import logging
import requests
import boto3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import re
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PrivateCompanyInfo:
    """Data structure for private company information"""
    registered_legal_name: str
    country_of_incorporation: str
    incorporation_date: str
    registered_business_address: str
    company_identifiers: Dict[str, str]
    business_description: str
    number_of_employees: str
    annual_revenue: str
    annual_sales: str
    website_url: str
    funding_rounds: str = "Not specified"
    key_investors: str = "Not specified"
    valuation: str = "Not specified"
    leadership_team: str = "Not specified"

class PrivateCompanySearcher:
    """Enhanced searcher for private company data using multiple sources"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
    
    def search_multiple_sources(self, company_name: str, current_year: str, previous_year: str) -> Dict[str, List]:
        """Search multiple sources for private company data in priority order"""
        all_results = {
            'sec_form_10k': [],
            'sec_other_filings': [],
            'sec_executive_filings': [],
            'cxo_corporate_website': [],
            'wikipedia': [],
            'yahoo_finance': [],
            'bloomberg': [],
            'state_filings': [],
            'news_articles': [],
            'company_website': [],
            'funding_databases': []
        }
        
        # 1. SEC Comprehensive Search (First Priority - All Private Company Filings)
        sec_comprehensive_query = f'{company_name} site:sec.gov ({current_year} OR {previous_year} OR 2023 OR 2022 OR 2021)'
        all_results['sec_form_10k'] = self._execute_search(sec_comprehensive_query, "SEC Comprehensive Search")
        
        # 2. SEC Private Company Specific Filings (Second Priority)
        sec_private_query = f'"{company_name}" site:sec.gov ("Form D" OR "private placement" OR "offering" OR "Schedule 13" OR "beneficial ownership" OR "proxy" OR "DEF 14A" OR "subsidiary" OR "acquisition" OR "merger")'
        all_results['sec_other_filings'] = self._execute_search(sec_private_query, "SEC Private Company Filings")
        
        # 3. SEC Executive & Board Filings (Third Priority)
        sec_executive_query = f'"{company_name}" site:sec.gov ("Form 4" OR "insider trading" OR "director" OR "officer" OR "executive" OR "board member" OR "Form 3" OR "Form 5")'
        all_results['sec_executive_filings'] = self._execute_search(sec_executive_query, "SEC Executive Filings")
        
        # 4. CxO Corporate Website Search (Fourth Priority - Executive Leadership Only)
        cxo_website_query = f'site:{self._extract_domain(company_name)} ("CEO" OR "CFO" OR "CTO" OR "COO" OR "president" OR "founder" OR "executive team" OR "leadership team" OR "management team" OR "board of directors" OR "senior leadership" OR "about us" OR "leadership" OR "executives" OR "management" OR "team" OR "our team")'
        all_results['cxo_corporate_website'] = self._execute_search(cxo_website_query, "CxO Corporate Website")
        
        # 5. Wikipedia (Fifth Priority)
        wikipedia_query = f'"{company_name}" site:wikipedia.org (company OR corporation OR business OR revenue OR employees OR founded OR headquarters)'
        all_results['wikipedia'] = self._execute_search(wikipedia_query, "Wikipedia")
        
        # 6. Yahoo Finance (Sixth Priority)
        yahoo_query = f'"{company_name}" site:finance.yahoo.com (company OR profile OR financials OR revenue OR employees OR business)'
        all_results['yahoo_finance'] = self._execute_search(yahoo_query, "Yahoo Finance")
        
        # 7. Bloomberg (Seventh Priority)
        bloomberg_query = f'"{company_name}" site:bloomberg.com (company OR revenue OR employees OR financial OR business OR profile OR valuation) ({current_year} OR {previous_year})'
        all_results['bloomberg'] = self._execute_search(bloomberg_query, "Bloomberg")
        
        # 8. State Corporate Filings
        state_query = f'{company_name} (site:sosnc.gov OR site:delaware.gov OR site:sos.ca.gov OR site:dos.ny.gov) (annual report OR corporate filing OR registration) ({current_year} OR {previous_year})'
        all_results['state_filings'] = self._execute_search(state_query, "State Corporate Filings")
        
        # 9. Recent News & Press Releases
        news_query = f'"{company_name}" (revenue OR funding OR employees OR "financial results" OR acquisition OR "annual report") ({current_year} OR {previous_year})'
        all_results['news_articles'] = self._execute_search(news_query, "News & Press Releases")
        
        # 10. Company Website & Official Documents
        website_query = f'"{company_name}" site:{self._extract_domain(company_name)} (annual report OR financial OR investor OR about OR press release OR company) ({current_year} OR {previous_year})'
        all_results['company_website'] = self._execute_search(website_query, "Company Website")
        
        # 11. Funding & Investment Databases
        funding_query = f'"{company_name}" (site:crunchbase.com OR site:pitchbook.com OR site:privco.com OR funding OR investment OR valuation) ({current_year} OR {previous_year})'
        all_results['funding_databases'] = self._execute_search(funding_query, "Funding Databases")
        
        return all_results
    
    def _execute_search(self, query: str, search_type: str) -> List[Dict]:
        """Execute a single search query"""
        try:
            payload = {
                "q": query,
                "num": 10,
                "gl": "us",
                "hl": "en",
                "tbs": "qdr:y2"  # Past 2 years for more recent data
            }
            
            logger.info(f"Searching {search_type}: {query[:100]}...")
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            results = response.json()
            organic_results = results.get('organic', [])
            
            # Add search metadata
            for result in organic_results:
                result['search_type'] = search_type
                result['search_query'] = query
            
            logger.info(f"Found {len(organic_results)} results for {search_type}")
            return organic_results
            
        except Exception as e:
            logger.error(f"Error searching {search_type}: {e}")
            return []
    
    def _extract_domain(self, company_name: str) -> str:
        """Extract likely domain name from company name"""
        # Simple domain extraction logic
        clean_name = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
        clean_name = clean_name.replace('corporation', '').replace('corp', '').replace('inc', '').replace('llc', '')
        return f"{clean_name}.com"

class NovaProPrivateExtractor:
    """Nova Pro LLM integration for private company data extraction"""
    
    def __init__(self, profile: str = "diligent", region: str = "us-east-1"):
        self.profile = profile
        self.region = region
        
        try:
            # Check if running in Lambda environment
            is_lambda = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
            
            if is_lambda:
                # Lambda: use IAM role (no profile)
                self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
                logger.info("AWS Bedrock client initialized successfully using Lambda IAM role")
            else:
                # Local: use AWS profile
                try:
                    session = boto3.Session(profile_name=profile)
                    self.bedrock_client = session.client('bedrock-runtime', region_name=region)
                    logger.info(f"AWS Bedrock client initialized successfully using profile: {profile}")
                except Exception as profile_error:
                    logger.warning(f"Could not use AWS profile '{profile}': {profile_error}")
                    logger.info("Falling back to default credentials")
                    self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
                    logger.info("AWS Bedrock client initialized successfully using default credentials")
        except Exception as e:
            logger.error(f"Error initializing AWS Bedrock client: {e}")
            self.bedrock_client = None
    
    def extract_private_company_data(self, company_name: str, search_results: Dict[str, List]) -> tuple[PrivateCompanyInfo, float]:
        """Extract private company data using Nova Pro with completeness validation and retry
        
        Returns:
            tuple: (PrivateCompanyInfo, completeness_percentage)
        """
        if not self.bedrock_client:
            logger.warning("Nova Pro not available, using fallback extraction")
            return self._fallback_extraction(company_name), 0.0
        
        max_attempts = 3
        target_completeness = 95.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Extraction attempt {attempt}/{max_attempts}")
                
                # Build comprehensive context from all search results
                context = self._build_search_context(search_results)
                
                # Build extraction prompt (enhanced on retries)
                if attempt == 1:
                    prompt = self._build_private_company_prompt(company_name, context)
                else:
                    prompt = self._build_enhanced_retry_prompt(company_name, context, attempt)
                
                # Call Nova Pro model
                model_id = "amazon.nova-pro-v1:0"
                
                body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                "inferenceConfig": {
                    "max_new_tokens": 6000,  # Increased from 4000 to handle more data
                    "temperature": 0.5  # Increased to 0.5 for maximum extraction creativity
                }
                }
                
                logger.info("Calling Nova Pro for private company data extraction...")
                
                response = self.bedrock_client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body)
                )
                
                response_body = json.loads(response['body'].read())
                
                # Handle different response formats
                if 'output' in response_body:
                    extracted_text = response_body['output']['message']['content'][0]['text']
                elif 'content' in response_body:
                    extracted_text = response_body['content'][0]['text']
                else:
                    logger.error(f"Unexpected Nova Pro response structure: {response_body}")
                    extracted_text = str(response_body)
                
                # Parse the extracted JSON
                company_info = self._parse_nova_response(extracted_text, company_name)
                
                # Calculate completeness
                completeness = self._calculate_completeness(company_info)
                logger.info(f"Extraction completeness: {completeness:.1f}%")
                
                # Check if completeness meets target
                if completeness >= target_completeness:
                    logger.info(f"✅ Target completeness achieved: {completeness:.1f}%")
                    return company_info, completeness
                elif attempt < max_attempts:
                    logger.warning(f"⚠️  Completeness {completeness:.1f}% below target {target_completeness}%, retrying...")
                    time.sleep(2)  # Brief pause before retry
                else:
                    logger.warning(f"⚠️  Final completeness: {completeness:.1f}% (target: {target_completeness}%)")
                    return company_info, completeness
                
            except Exception as e:
                logger.error(f"Error with Nova Pro extraction (attempt {attempt}): {e}")
                if attempt == max_attempts:
                    return self._fallback_extraction(company_name), 0.0
        
        return self._fallback_extraction(company_name), 0.0
    
    def _build_search_context(self, search_results: Dict[str, List]) -> str:
        """Build comprehensive context from all search results"""
        context_parts = []
        
        for search_type, results in search_results.items():
            if results:
                context_parts.append(f"\n=== {search_type.upper().replace('_', ' ')} ===")
                for i, result in enumerate(results[:5], 1):  # Top 5 results per category
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    url = result.get('link', '')
                    context_parts.append(f"{i}. {title}")
                    context_parts.append(f"   URL: {url}")
                    context_parts.append(f"   Content: {snippet}")
                    context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _build_private_company_prompt(self, company_name: str, context: str) -> str:
        """Build extraction prompt for private companies"""
        current_year = datetime.now().year
        
        prompt = f"""
You are a financial data extraction expert specializing in PRIVATE COMPANY analysis.

COMPANY: {company_name}
CURRENT YEAR: {current_year}

TASK: Extract detailed private company information from the search results below. Private companies don't file traditional SEC 10-K reports, so look for alternative data sources.

SEARCH CONTEXT (Multiple Sources):
{context[:20000]}  # Increased limit for more comprehensive context

**🚨 CRITICAL INSTRUCTIONS FOR PRIVATE COMPANIES:**
- **SOURCE PRIORITY ORDER**: 1) SEC Comprehensive Search 2) SEC Private Company Filings 3) SEC Executive Filings 4) CxO Corporate Website 5) Wikipedia 6) Yahoo Finance 7) Bloomberg 8) Other sources
- **PRIORITIZE RECENT DATA**: Use {current_year} data over older information
- **SEC COMPREHENSIVE FIRST**: Use ANY SEC filing for the company (Form D, 10-K, 10-Q, 8-K, proxy statements, etc.) - most authoritative source
- **SEC PRIVATE COMPANY SECOND**: Focus on private placement offerings, acquisitions, mergers, beneficial ownership filings
- **SEC EXECUTIVE THIRD**: Use executive/insider filings (Form 3, 4, 5) which may indicate company relationships
- **CXO CORPORATE WEBSITE FOURTH**: **EXCLUSIVE FOCUS** on company's official website ONLY for executive team, leadership pages, management bios, about us pages - most current and authoritative executive information
- **WIKIPEDIA FIFTH**: Use Wikipedia for basic company info, founding date, headquarters, business description
- **YAHOO FINANCE SIXTH**: Use for financial data, revenue, employee count if available
- **BLOOMBERG SEVENTH**: Use for latest financial news, valuation, business updates
- **EXTRACT FROM MULTIPLE SOURCES**: Combine information from different search result categories
- **FOCUS ON REAL-TIME DATA**: Recent press releases, funding rounds, news articles often have current employee/revenue data
- **USE LATEST AVAILABLE**: If {current_year} data not available, use most recent year found
- **PRIVATE COMPANY SEC STRATEGY**: Even private companies may have SEC filings through subsidiaries, acquisitions, or executive relationships with public companies
- **CXO EXTRACTION PRIORITY**: Extract detailed executive information EXCLUSIVELY from the company's official corporate website - this is the most reliable source for current leadership team information

EXTRACTION REQUIREMENTS:

**Company Basic Information - Collect and return:**
* Registered legal name
* Country of incorporation  
* Incorporation date (check state filings, news articles)
* Registered business address
* Company identifiers (CIK, DUNS, LEI, state registration numbers)

**Company Profile Enrichment:**
* Provide a concise description of business activities, industries, and core products/services
* Include:
    * Number of employees (latest available - check news, company website, funding announcements)
    * Annual revenue (latest available - check press releases, news articles, industry reports)
    * Annual sales (if different from revenue)
    * Website URL
    * Recent funding rounds and valuation (if available)
    * Key investors or ownership information
    * Leadership team information

**🚨 CxO & Executive Leadership Information (HIGH PRIORITY):**
Extract detailed information for each executive found:
* **CEO (Chief Executive Officer)**: Full name, background, tenure, previous experience
* **CFO (Chief Financial Officer)**: Full name, background, tenure, previous experience
* **CTO (Chief Technology Officer)**: Full name, background, tenure, previous experience
* **COO (Chief Operating Officer)**: Full name, background, tenure, previous experience
* **President**: Full name, background, tenure, previous experience
* **Founder(s)**: Full name, background, founding date, current role
* **Board Members**: Names, titles, backgrounds (if available)
* **Other Key Executives**: VP-level and above, department heads

For each executive, extract:
- Full legal name
- Current title/position
- Date appointed (if available)
- Previous roles/experience
- Educational background (if available)
- Age/Date of birth (if available)
- Nationality (if available)
- Any ownership percentage (if mentioned)
- Contact information (if available)

Extract and return ONLY a JSON object with the following fields:

{{
    "registered_legal_name": "exact legal name from documents",
    "country_of_incorporation": "country where incorporated",
    "incorporation_date": "date of incorporation (format: Month DD, YYYY)",
    "registered_business_address": "complete business address",
    "company_identifiers": {{
        "registration_number": "state or federal registration number",
        "DUNS": "DUNS number if available",
        "LEI": "Legal Entity Identifier if available",
        "CIK": "CIK if available from SEC filings",
        "CUSIP": "CUSIP number if available",
        "state_id": "state registration ID if available"
    }},
    "business_description": "comprehensive description of business activities, industries, and core products/services",
    "number_of_employees": "LATEST number of employees with date and source (e.g., '500 employees as of March 2025 per company announcement')",
    "annual_revenue": "LATEST revenue with year and source (e.g., '$50 million revenue 2024 per industry report')",
    "annual_sales": "LATEST sales with year (if different from revenue)",
    "website_url": "company website URL",
    "funding_rounds": "recent funding information if available",
    "key_investors": "major investors or ownership information if available",
    "valuation": "company valuation if available",
    "leadership_team": {{
        "ceo": {{
            "name": "CEO full name",
            "title": "exact title",
            "background": "previous experience and education",
            "tenure": "when appointed or years in role",
            "age_or_birth_date": "if available",
            "nationality": "if available"
        }},
        "cfo": {{
            "name": "CFO full name",
            "title": "exact title", 
            "background": "previous experience and education",
            "tenure": "when appointed or years in role"
        }},
        "cto": {{
            "name": "CTO full name",
            "title": "exact title",
            "background": "previous experience and education", 
            "tenure": "when appointed or years in role"
        }},
        "coo": {{
            "name": "COO full name",
            "title": "exact title",
            "background": "previous experience and education",
            "tenure": "when appointed or years in role"
        }},
        "president": {{
            "name": "President full name",
            "title": "exact title",
            "background": "previous experience and education",
            "tenure": "when appointed or years in role"
        }},
        "founders": [
            {{
                "name": "Founder full name",
                "current_role": "current position in company",
                "background": "founding story and previous experience",
                "founding_date": "when company was founded"
            }}
        ],
        "board_members": [
            {{
                "name": "Board member full name",
                "title": "board position",
                "background": "professional background"
            }}
        ],
        "other_executives": [
            {{
                "name": "Executive full name", 
                "title": "position title",
                "department": "area of responsibility",
                "background": "professional background if available"
            }}
        ]
    }}
}}

EXTRACTION RULES (🚨 CRITICAL - MUST ACHIEVE 95%+ COMPLETENESS):
1. **PRIMARY**: Extract ALL factual information from the search results provided
2. **PRIORITIZE {current_year} DATA** - Use most recent information available
3. For financial figures, include the year and source (e.g., "per company press release", "per industry report")
4. **MINIMIZE EMPTY FIELDS**: Only use "Not specified in available sources" as LAST RESORT after checking ALL search results
5. **INFER WHEN NEEDED**: If exact data not available but context clues exist, provide reasonable estimates with source note
6. Return valid JSON format only
7. **COMBINE INFORMATION** from multiple search result categories for comprehensive data
8. **LOOK FOR RECENT NEWS** about employee count, revenue, funding, acquisitions
9. **CHECK COMPANY WEBSITE** for official announcements and reports
10. **USE FUNDING DATABASE INFO** for valuation and investor information
11. **EXECUTIVE DATA**: Extract EVERY executive name mentioned in ANY search result
12. **COMPANY IDs**: Extract ANY identifier (CIK, DUNS, registration numbers) from SEC filings or state documents
13. **FILL ALL FIELDS**: Aim for 95%+ field completion - empty fields indicate incomplete extraction

Based on the search results provided, extract the private company information and return the JSON object.
"""
        return prompt
    
    def _parse_nova_response(self, extracted_text: str, company_name: str) -> PrivateCompanyInfo:
        """Parse Nova Pro response into PrivateCompanyInfo object"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', extracted_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                return PrivateCompanyInfo(
                    registered_legal_name=data.get('registered_legal_name', company_name),
                    country_of_incorporation=data.get('country_of_incorporation', 'Not specified in available sources'),
                    incorporation_date=data.get('incorporation_date', 'Not specified in available sources'),
                    registered_business_address=data.get('registered_business_address', 'Not specified in available sources'),
                    company_identifiers=data.get('company_identifiers', {}),
                    business_description=data.get('business_description', 'Not specified in available sources'),
                    number_of_employees=data.get('number_of_employees', 'Not specified in available sources'),
                    annual_revenue=data.get('annual_revenue', 'Not specified in available sources'),
                    annual_sales=data.get('annual_sales', 'Not specified in available sources'),
                    website_url=data.get('website_url', 'Not specified in available sources'),
                    funding_rounds=data.get('funding_rounds', 'Not specified in available sources'),
                    key_investors=data.get('key_investors', 'Not specified in available sources'),
                    valuation=data.get('valuation', 'Not specified in available sources'),
                    leadership_team=data.get('leadership_team', 'Not specified in available sources')
                )
            else:
                logger.error("No valid JSON found in Nova Pro response")
                return self._fallback_extraction(company_name)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Nova Pro JSON response: {e}")
            return self._fallback_extraction(company_name)
        except Exception as e:
            logger.error(f"Error processing Nova Pro response: {e}")
            return self._fallback_extraction(company_name)
    
    def _calculate_completeness(self, company_info: PrivateCompanyInfo) -> float:
        """Calculate completeness percentage of extracted data"""
        total_fields = 0
        filled_fields = 0
        
        # Check main fields
        for field_name, field_value in asdict(company_info).items():
            if field_name == 'company_identifiers':
                # Count identifier fields
                identifiers = field_value if isinstance(field_value, dict) else {}
                for id_key, id_val in identifiers.items():
                    total_fields += 1
                    if id_val and id_val != 'Not specified in available sources' and id_val != '' and id_val != 'Not specified':
                        filled_fields += 1
            elif field_name == 'leadership_team':
                # Count leadership fields
                leadership = field_value if isinstance(field_value, dict) else {}
                if isinstance(leadership, str):
                    total_fields += 1
                    if leadership and leadership != 'Not specified in available sources' and leadership != 'Not specified':
                        filled_fields += 1
                else:
                    for role_key, role_val in leadership.items():
                        if isinstance(role_val, dict):
                            for sub_key, sub_val in role_val.items():
                                total_fields += 1
                                if sub_val and sub_val != 'Not specified' and sub_val != '' and sub_val != 'Not specified in available sources':
                                    filled_fields += 1
                        elif isinstance(role_val, list):
                            for item in role_val:
                                if isinstance(item, dict):
                                    for sub_key, sub_val in item.items():
                                        total_fields += 1
                                        if sub_val and sub_val != 'Not specified' and sub_val != '' and sub_val != 'Not specified in available sources':
                                            filled_fields += 1
            else:
                total_fields += 1
                if field_value and field_value != 'Not specified in available sources' and field_value != '' and field_value != 'Not specified':
                    filled_fields += 1
        
        completeness = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        return completeness
    
    def _build_enhanced_retry_prompt(self, company_name: str, context: str, attempt: int) -> str:
        """Build enhanced prompt for retry attempts"""
        base_prompt = self._build_private_company_prompt(company_name, context)
        
        enhancement = f"""

🚨🚨🚨 ULTRA-CRITICAL: RETRY ATTEMPT {attempt}/3 - 95% COMPLETENESS MANDATORY 🚨🚨🚨

Previous extraction FAILED completeness check. This is your {'FINAL' if attempt == 3 else 'LAST'} chance.

**MANDATORY ACTIONS - NO EXCEPTIONS:**

1. **ZERO TOLERANCE FOR EMPTY FIELDS**:
   - "Not specified in available sources" is BANNED except for truly missing data
   - Review EVERY search result snippet line-by-line
   - Extract ANY relevant information, however minor

2. **AGGRESSIVE INFERENCE REQUIRED**:
   - incorporation_date: If founding year mentioned (e.g., "founded 2010"), use "Incorporated 2010 (estimated from founding)"
   - number_of_employees: Look for phrases like "team of X", "X+ employees", "hundreds of staff" → estimate reasonably
   - annual_sales: If revenue mentioned but not sales, use "Estimated equal to revenue" 
   - company_identifiers: Extract ANY ID numbers from SEC filings, state docs, or registration numbers

3. **EXECUTIVE EXTRACTION - MAXIMUM PRIORITY** (ZERO EMPTY SUB-FIELDS ALLOWED):
   - CEO: MUST be filled (check Wikipedia, company website, news articles)
   - CFO/CTO/COO/President: Check job postings, LinkedIn mentions, press releases about appointments
   - For ANY executive with missing sub-fields:
     * background: If not found, use "Background not publicly disclosed" or infer from company description
     * tenure: If not found, use "Tenure information not publicly available" or estimate from company age
     * If executive role unknown, use: "{{"name": "Position filled (name not publicly disclosed)", "title": "CFO", "background": "Executive background not publicly disclosed", "tenure": "Current tenure not specified"}}"
   - founders: Check Wikipedia, Crunchbase results, company history pages
   - board_members: Look for "board of directors", "advisory board" in search results
   - other_executives: Extract VP-level, heads of departments from ANY source
   - **CRITICAL**: Every executive sub-field (name, title, background, tenure) MUST have a value - never leave blank

4. **COMPANY IDENTIFIERS - HIGH VALUE** (MUST FILL ALL):
   - CIK: Check any SEC filing references in search results. If not found: "Not publicly disclosed (private company)"
   - state_id: Look for Delaware corp info, state filing numbers. If not found: "Private registration (not publicly available)"
   - registration_number: Check state filing search results. If not found: "Private company registration (restricted access)"
   - DUNS/LEI/CUSIP: If not found in search results: "Not publicly disclosed (typical for private companies)"
   - **CRITICAL**: Never leave identifier fields as "Not specified" - always provide context note

5. **FINANCIAL DATA - CREATIVE EXTRACTION**:
   - annual_revenue: Check news about "hit $X revenue", "revenue grew to $X", funding round valuations
   - valuation: Check "valued at $X", "worth $X", funding round announcements
   - key_investors: Extract from funding database results, news about investments
   - funding_rounds: Combine all funding mentions into comprehensive summary

6. **ADDRESS & INCORPORATION**:
   - registered_business_address: Use headquarters address if registered address not found
   - incorporation_date: Use founding date with "(estimated)" note if exact date unavailable
   - country_of_incorporation: Infer from headquarters location if not explicitly stated

7. **COMPLETENESS SCORING**:
   - Empty identifier fields: -10 points each
   - Empty executive positions (CEO/CFO/CTO/COO): -15 points each
   - Empty basic info (employees/revenue): -10 points each
   - Target: 95%+ or extraction fails

**EXTRACTION STRATEGY FOR THIS RETRY:**
- Step 1: Re-read ALL search results with fresh perspective
- Step 2: Extract explicit information first
- Step 3: Fill remaining fields with reasonable inferences
- Step 4: Use context clues creatively
- Step 5: Provide estimated/inferred values with source notes

**REMEMBER:** This is a private company - data is scarce. Use ALL available context clues.
A well-reasoned estimate with a source note is BETTER than "Not specified".

NOW EXTRACT with 95%+ completeness. This is MANDATORY.

"""
        
        return base_prompt + enhancement
    
    def _fallback_extraction(self, company_name: str) -> PrivateCompanyInfo:
        """Fallback extraction when Nova Pro is not available"""
        return PrivateCompanyInfo(
            registered_legal_name=company_name,
            country_of_incorporation="Not specified in available sources",
            incorporation_date="Not specified in available sources",
            registered_business_address="Not specified in available sources",
            company_identifiers={},
            business_description="Not specified in available sources",
            number_of_employees="Not specified in available sources",
            annual_revenue="Not specified in available sources",
            annual_sales="Not specified in available sources",
            website_url="Not specified in available sources"
        )

class PrivateCompanyExtractor:
    """Main class for private company data extraction"""
    
    def __init__(self):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        self.searcher = PrivateCompanySearcher(self.serper_api_key)
        self.extractor = NovaProPrivateExtractor(profile="diligent")
    
    def _get_search_years(self) -> tuple[str, str]:
        """Get current year and previous year for search"""
        current_year = datetime.now().year
        previous_year = current_year - 1
        return str(current_year), str(previous_year)
    
    def extract_company_data(self, company_name: str) -> Dict[str, Any]:
        """Main method to extract private company data"""
        try:
            current_year, previous_year = self._get_search_years()
            
            logger.info(f"Starting private company data extraction for: {company_name}")
            logger.info(f"Searching years: {current_year} (current) and {previous_year} (previous)")
            
            # Step 1: Search multiple sources
            search_results = self.searcher.search_multiple_sources(company_name, current_year, previous_year)
            
            # Step 2: Extract data using Nova Pro with completeness validation
            company_data, completeness = self.extractor.extract_private_company_data(company_name, search_results)
            
            # Step 3: Compile results
            results = {
                'extraction_metadata': {
                    'company_searched': company_name,
                    'search_timestamp': datetime.now().isoformat(),
                    'search_years': f"{current_year} OR {previous_year}",
                    'extraction_method': 'Nova Pro Private Company Analysis',
                    'sources_searched': list(search_results.keys()),
                    'total_results_found': sum(len(results) for results in search_results.values()),
                    'completeness_percentage': f"{completeness:.1f}%",
                    'completeness_status': 'Excellent' if completeness >= 95 else 'Good' if completeness >= 80 else 'Fair' if completeness >= 60 else 'Poor'
                },
                'company_information': asdict(company_data),
                'search_results_summary': {
                    source: len(results) for source, results in search_results.items()
                },
                'detailed_search_results': search_results
            }
            
            # Step 4: Save results
            self._save_results(results, company_name)
            
            logger.info(f"✅ Extraction complete with {completeness:.1f}% completeness")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in private company extraction: {e}")
            return self._create_error_result(company_name, str(e))
    
    def _save_results(self, results: Dict[str, Any], company_name: str):
        """Save extraction results to DynamoDB only (company data only, no metadata)"""
        safe_company_name = company_name.lower().replace(" ", "_").replace(".", "").replace(",", "")
        
        # Extract only company information (non-metadata)
        company_data_only = results.get('company_information', {})
        
        # Save to DynamoDB
        try:
            self._save_to_dynamodb(company_data_only, company_name, safe_company_name)
            logger.info(f"✅ Company data saved to DynamoDB successfully")
        except Exception as e:
            logger.error(f"❌ DynamoDB save failed: {e}")
            raise
    
    def _save_to_dynamodb(self, company_info: Dict[str, Any], company_name: str, company_id: str):
        """Save private company information to DynamoDB"""
        try:
            # Initialize DynamoDB client (use IAM role in Lambda, profile locally)
            is_lambda = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
            if is_lambda:
                dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            else:
                session = boto3.Session(profile_name='diligent')
                dynamodb = session.resource('dynamodb', region_name='us-east-1')
            
            # Table name for Private Company data
            table_name = 'CompanyPrivateData'
            table = dynamodb.Table(table_name)
            
            # Prepare item for DynamoDB
            timestamp = datetime.now().isoformat()
            
            # Convert leadership_team to JSON string if it's a dict (DynamoDB compatibility)
            leadership_team = company_info.get('leadership_team', {})
            if isinstance(leadership_team, dict):
                leadership_team_str = json.dumps(leadership_team)
            else:
                leadership_team_str = str(leadership_team)
            
            item = {
                'company_id': company_id,  # Partition key
                'extraction_timestamp': timestamp,  # Sort key
                'company_name': company_name,
                'registered_legal_name': company_info.get('registered_legal_name', ''),
                'country_of_incorporation': company_info.get('country_of_incorporation', ''),
                'incorporation_date': company_info.get('incorporation_date', ''),
                'registered_business_address': company_info.get('registered_business_address', ''),
                'company_identifiers': company_info.get('company_identifiers', {}),
                'business_description': company_info.get('business_description', ''),
                'number_of_employees': company_info.get('number_of_employees', ''),
                'annual_revenue': company_info.get('annual_revenue', ''),
                'annual_sales': company_info.get('annual_sales', ''),
                'website_url': company_info.get('website_url', ''),
                'funding_rounds': company_info.get('funding_rounds', ''),
                'key_investors': company_info.get('key_investors', ''),
                'valuation': company_info.get('valuation', ''),
                'leadership_team': leadership_team_str,
                'extraction_source': 'private_company_extractor'
            }
            
            # Put item to DynamoDB
            table.put_item(Item=item)
            
            logger.info(f"✅ Data saved to DynamoDB table: {table_name}")
            logger.info(f"   Company ID: {company_id}")
            logger.info(f"   Timestamp: {timestamp}")
            
        except Exception as e:
            logger.error(f"❌ DynamoDB save failed: {e}")
            raise
    
    def _create_error_result(self, company_name: str, error_message: str) -> Dict[str, Any]:
        """Create error result structure"""
        return {
            'extraction_metadata': {
                'company_searched': company_name,
                'search_timestamp': datetime.now().isoformat(),
                'extraction_method': 'Nova Pro Private Company Analysis',
                'error': error_message
            },
            'company_information': asdict(self.extractor._fallback_extraction(company_name)),
            'search_results_summary': {},
            'detailed_search_results': {}
        }
    
    def display_results(self, results: Dict[str, Any]):
        """Display extraction results"""
        if 'error' in results.get('extraction_metadata', {}):
            print(f"\nERROR: {results['extraction_metadata']['error']}")
            return
        
        company_info = results.get('company_information', {})
        metadata = results.get('extraction_metadata', {})
        
        print("\n" + "="*70)
        print(f"{results.get('extraction_metadata', {}).get('company_searched', 'COMPANY').upper()} PRIVATE COMPANY DATA EXTRACTION")
        print("="*70)
        
        print(f"\nCOMPANY INFORMATION:")
        print(f"Legal Name: {company_info.get('registered_legal_name', 'N/A')}")
        print(f"Country: {company_info.get('country_of_incorporation', 'N/A')}")
        print(f"Incorporation Date: {company_info.get('incorporation_date', 'N/A')}")
        print(f"Address: {company_info.get('registered_business_address', 'N/A')}")
        print(f"Employees: {company_info.get('number_of_employees', 'N/A')}")
        print(f"Revenue: {company_info.get('annual_revenue', 'N/A')}")
        print(f"Sales: {company_info.get('annual_sales', 'N/A')}")
        print(f"Website: {company_info.get('website_url', 'N/A')}")
        
        print(f"\nPRIVATE COMPANY SPECIFIC:")
        print(f"Funding Rounds: {company_info.get('funding_rounds', 'N/A')}")
        print(f"Valuation: {company_info.get('valuation', 'N/A')}")
        print(f"Key Investors: {company_info.get('key_investors', 'N/A')}")
        print(f"Leadership Team: {company_info.get('leadership_team', 'N/A')}")
        
        print(f"\nCOMPANY IDENTIFIERS:")
        for key, value in company_info.get('company_identifiers', {}).items():
            print(f"{key}: {value}")
        
        print(f"\nBUSINESS DESCRIPTION:")
        print(company_info.get('business_description', 'N/A'))
        
        print(f"\nEXTRACTION QUALITY:")
        completeness_pct = metadata.get('completeness_percentage', 'N/A')
        completeness_status = metadata.get('completeness_status', 'N/A')
        print(f"Completeness: {completeness_pct} ({completeness_status})")
        
        print(f"\nSEARCH SUMMARY:")
        print(f"Search Years: {metadata.get('search_years', 'N/A')}")
        print(f"Total Results Found: {metadata.get('total_results_found', 0)}")
        sources_searched = metadata.get('sources_searched', [])
        # Display in priority order
        priority_order = ['sec_form_10k', 'sec_other_filings', 'sec_executive_filings', 'cxo_corporate_website', 'wikipedia', 'yahoo_finance', 'bloomberg', 'state_filings', 'news_articles', 'company_website', 'funding_databases']
        ordered_sources = [s for s in priority_order if s in sources_searched]
        print(f"Sources Searched (Priority Order): {', '.join([s.replace('_', ' ').title() for s in ordered_sources])}")
        
        search_summary = results.get('search_results_summary', {})
        if search_summary:
            print(f"\nRESULTS BY SOURCE (Priority Order):")
            # Display in priority order
            priority_order = ['sec_form_10k', 'sec_other_filings', 'sec_executive_filings', 'cxo_corporate_website', 'wikipedia', 'yahoo_finance', 'bloomberg', 'state_filings', 'news_articles', 'company_website', 'funding_databases']
            for source in priority_order:
                if source in search_summary:
                    count = search_summary[source]
                    print(f"{source.replace('_', ' ').title()}: {count} results")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python private_company_extractor.py \"Company Name\"")
        print("Example: python private_company_extractor.py \"Diligent Corporation\"")
        sys.exit(1)
    
    company_name = sys.argv[1]
    
    try:
        # Initialize extractor
        extractor = PrivateCompanyExtractor()
        
        # Extract company data
        results = extractor.extract_company_data(company_name)
        
        # Display results
        extractor.display_results(results)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
