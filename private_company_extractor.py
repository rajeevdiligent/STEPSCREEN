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
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            logger.info("AWS Bedrock client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing AWS Bedrock client: {e}")
            self.bedrock_client = None
    
    def extract_private_company_data(self, company_name: str, search_results: Dict[str, List]) -> PrivateCompanyInfo:
        """Extract private company data using Nova Pro"""
        if not self.bedrock_client:
            logger.warning("Nova Pro not available, using fallback extraction")
            return self._fallback_extraction(company_name)
        
        try:
            # Build comprehensive context from all search results
            context = self._build_search_context(search_results)
            
            # Build extraction prompt
            prompt = self._build_private_company_prompt(company_name, context)
            
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
                    "max_new_tokens": 4000,
                    "temperature": 0.1
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
            
            logger.info("Successfully extracted private company data using Nova Pro")
            
            # Parse the extracted JSON
            return self._parse_nova_response(extracted_text, company_name)
            
        except Exception as e:
            logger.error(f"Error with Nova Pro extraction: {e}")
            return self._fallback_extraction(company_name)
    
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
{context[:15000]}  # Limit to avoid token limits

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

EXTRACTION RULES:
1. Extract ONLY factual information from the search results provided
2. **PRIORITIZE {current_year} DATA** - Use most recent information available
3. For financial figures, include the year and source (e.g., "per company press release", "per industry report")
4. If information is not found in ANY search result, use "Not specified in available sources"
5. Return valid JSON format only
6. Be precise and accurate
7. **COMBINE INFORMATION** from multiple search result categories for comprehensive data
8. **LOOK FOR RECENT NEWS** about employee count, revenue, funding, acquisitions
9. **CHECK COMPANY WEBSITE** for official announcements and reports
10. **USE FUNDING DATABASE INFO** for valuation and investor information

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
        
        # Create output directory
        self.output_dir = Path("private_company_extractions")
        self.output_dir.mkdir(exist_ok=True)
    
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
            
            # Step 2: Extract data using Nova Pro
            company_data = self.extractor.extract_private_company_data(company_name, search_results)
            
            # Step 3: Compile results
            results = {
                'extraction_metadata': {
                    'company_searched': company_name,
                    'search_timestamp': datetime.now().isoformat(),
                    'search_years': f"{current_year} OR {previous_year}",
                    'extraction_method': 'Nova Pro Private Company Analysis',
                    'sources_searched': list(search_results.keys()),
                    'total_results_found': sum(len(results) for results in search_results.values())
                },
                'company_information': asdict(company_data),
                'search_results_summary': {
                    source: len(results) for source, results in search_results.items()
                },
                'detailed_search_results': search_results
            }
            
            # Step 4: Save results
            self._save_results(results, company_name)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in private company extraction: {e}")
            return self._create_error_result(company_name, str(e))
    
    def _save_results(self, results: Dict[str, Any], company_name: str):
        """Save extraction results to JSON file"""
        safe_company_name = company_name.lower().replace(" ", "_").replace(".", "").replace(",", "")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_company_name}_private_extraction_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {filepath}")
    
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
