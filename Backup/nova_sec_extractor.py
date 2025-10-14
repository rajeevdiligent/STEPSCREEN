#!/usr/bin/env python3
"""
Nova Pro SEC Document Data Extractor
Following apple_sec_search.py approach with real Nova Pro integration
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
class CompanyInfo:
    """Data structure for company information"""
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

class NovaProExtractor:
    """Real Nova Pro integration for SEC document analysis"""
    
    def __init__(self, profile: str = "diligent", region: str = "us-east-1"):
        self.profile = profile
        self.region = region
        
        try:
            # Try using AWS profile first, then fall back to environment variables
            try:
                session = boto3.Session(profile_name=profile)
                self.bedrock_client = session.client('bedrock-runtime', region_name=region)
                logger.info(f"AWS Bedrock client initialized successfully using profile: {profile}")
            except Exception as profile_error:
                logger.warning(f"Could not use AWS profile '{profile}': {profile_error}")
                logger.info("Falling back to environment variables")
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=region,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                logger.info("AWS Bedrock client initialized successfully using environment variables")
        except Exception as e:
            logger.error(f"Error initializing AWS Bedrock client: {e}")
            self.bedrock_client = None
    
    def extract_company_data(self, company_name: str, document_urls: List[str], search_snippets: str = "") -> CompanyInfo:
        """
        Extract company information using Nova Pro following apple_sec_search.py approach
        """
        if not self.bedrock_client:
            logger.warning("Nova Pro not available, using enhanced fallback extraction")
            return self._enhanced_fallback_extraction(company_name, document_urls, search_snippets)
        
        try:
            # Build comprehensive prompt for Nova Pro
            prompt = self._build_extraction_prompt(company_name, document_urls, search_snippets)
            
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
            
            logger.info("Calling Nova Pro for SEC document analysis...")
            
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
            
            logger.info("Successfully extracted data using Nova Pro")
            
            # Parse the extracted JSON
            return self._parse_nova_response(extracted_text, company_name, document_urls)
            
        except Exception as e:
            logger.error(f"Error with Nova Pro extraction: {e}")
            return self._enhanced_fallback_extraction(company_name, document_urls, search_snippets)
    
    def _build_extraction_prompt(self, company_name: str, document_urls: List[str], search_snippets: str) -> str:
        """Build comprehensive extraction prompt for Nova Pro"""
        
        # Extract CIK from URLs for context
        cik = None
        for url in document_urls:
            cik_match = re.search(r'/data/(\d+)/', url)
            if cik_match:
                cik = cik_match.group(1).zfill(10)
                break
        
        current_year = datetime.now().year
        prompt = f"""
You are a financial data extraction expert specializing in SEC 10-K document analysis. 

COMPANY: {company_name}
CIK: {cik or 'Unknown'}
CURRENT YEAR: {current_year}

TASK: Extract detailed company information from the SEC 10-K documents at these URLs (prioritized by recency):
{chr(10).join(f"- {url}" for url in document_urls[:5])}

SEARCH CONTEXT (from SEC document search - includes {current_year} documents):
{search_snippets[:2000]}

**🚨 CRITICAL INSTRUCTION: PRIORITIZE 2025 QUARTERLY DATA OVER 2024 ANNUAL DATA:**
- **MANDATORY**: If you see 2025 quarterly revenue (like $124.3 billion Q1 2025), USE IT instead of 2024 annual revenue
- **MANDATORY**: If you see 2025 quarterly earnings data, USE IT for financial figures
- **For FINANCIAL DATA**: 2025 quarterly data > 2025 annual data > 2024 annual data
- **For STATIC COMPANY INFO**: Use ANY available data from 2025 OR 2024 documents
- **EXTRACT FROM TOP PRIORITY DOCUMENTS**: The documents are ranked by priority - use data from the highest priority documents first
- **QUARTERLY TO ANNUAL**: If only quarterly data available, note it as "Q1 2025", "Q2 2025", etc.
- **EXTRACT ACTUAL SALES NUMBERS**: Look for "Net sales", "Total sales" - provide actual figures
- **EXAMPLE**: If you see "$124.3 billion quarterly revenue Q1 2025", use "$124.3 billion (Q1 2025)" not "$383 billion (fiscal 2024)"
- **FOR EMPLOYEE DATA**: Look across ALL documents for the most recent employee count - check 10-K, 10-Q, proxy statements, and annual reports
- **EMPLOYEE PRIORITY**: Use 2025 employee data if available in ANY document, otherwise use the most recent available (2024)

EXTRACTION REQUIREMENTS:

**Company Basic Information - Collect and return:**
* Registered legal name
* Country of incorporation  
* Incorporation date
* Registered business address
* Company identifiers (e.g., registration number, DUNS, LEI)

**Company Profile Enrichment:**
* Provide a concise description of the company's business activities, industries, and core products/services.
* Include:
    * Number of employees
    * Annual revenue (latest available)
    * Annual sales (if different from revenue)
    * Website URL

Extract and return ONLY a JSON object with the following fields:

{{
    "registered_legal_name": "exact legal name from SEC documents",
    "country_of_incorporation": "country where incorporated (usually United States)",
    "incorporation_date": "date of incorporation (format: Month DD, YYYY)",
    "registered_business_address": "complete business address from SEC filing",
    "company_identifiers": {{
        "registration_number": "SEC registration number or CIK: {cik or 'extract from documents'}",
        "DUNS": "DUNS number from ANY available document (2025 or 2024)",
        "LEI": "Legal Entity Identifier from ANY available document (2025 or 2024)",
        "CIK": "{cik or 'extract from documents'}",
        "CUSIP": "CUSIP number from ANY available document (2025 or 2024)"
    }},
    "business_description": "concise description of business activities, industries, and core products/services",
    "number_of_employees": "LATEST number of employees with date - search ALL documents for most recent count (prioritize 2025 data from any document type)",
    "annual_revenue": "LATEST revenue - USE 2025 quarterly data if available (format: '$X billion Q1 2025' or '$X billion fiscal 2025')",
    "annual_sales": "LATEST sales/net sales - USE 2025 quarterly data if available (format: '$X billion Q1 2025' or '$X billion fiscal 2025')",
    "website_url": "company website URL"
}}

EXTRACTION RULES:
1. Follow the exact structure specified in "Company Basic Information" and "Company Profile Enrichment" sections above
2. Extract ONLY factual information from SEC documents
3. **HYBRID DATA EXTRACTION APPROACH:**
   - **Financial Data (revenue, sales)**: Use 2025 quarterly data if available, otherwise 2024 data
   - **Employee Data**: Search ALL documents (10-K, 10-Q, proxy statements) for most recent employee count - use 2025 if available in ANY document
   - **Static Company Info (DUNS, LEI, CUSIP, incorporation details)**: Use data from ANY available document (2025 OR 2024)
   - **NEVER leave fields as "Not specified" if the data exists in either 2025 or 2024 documents**
4. For financial figures, include the fiscal year and specify if it's annual or quarterly
5. For "annual sales" - ALWAYS provide the actual sales/net sales number from SEC documents (look for "Net sales", "Total sales", "Sales revenue", "Product sales", etc.)
6. If information is truly not found in ANY document, use "Not specified in SEC documents"
7. Return valid JSON format only
8. Be precise and accurate
9. **PRIORITY ORDER**: 2025 financial data > 2024 financial data > Any available static data
10. Use the exact legal name as it appears in SEC filings
11. Provide concise business description covering activities, industries, and core products/services
12. **MANDATORY: Extract ALL available company identifiers from both 2025 and 2024 documents**

Based on the SEC document URLs and search context provided, extract the company information and return the JSON object.
"""
        return prompt
    
    def _parse_nova_response(self, response_text: str, company_name: str, document_urls: List[str]) -> CompanyInfo:
        """Parse Nova Pro response into CompanyInfo object"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                return CompanyInfo(
                    registered_legal_name=data.get('registered_legal_name', company_name),
                    country_of_incorporation=data.get('country_of_incorporation', 'United States'),
                    incorporation_date=data.get('incorporation_date', 'Not specified in SEC documents'),
                    registered_business_address=data.get('registered_business_address', 'Not specified in SEC documents'),
                    company_identifiers=data.get('company_identifiers', {}),
                    business_description=data.get('business_description', 'Not specified in SEC documents'),
                    number_of_employees=data.get('number_of_employees', 'Not specified in SEC documents'),
                    annual_revenue=data.get('annual_revenue', 'Not specified in SEC documents'),
                    annual_sales=data.get('annual_sales', 'Not specified in SEC documents'),
                    website_url=data.get('website_url', self._generate_website_url(company_name))
                )
            else:
                raise ValueError("No JSON found in Nova Pro response")
                
        except Exception as e:
            logger.error(f"Error parsing Nova Pro response: {e}")
            logger.info(f"Raw response: {response_text[:500]}...")
            return self._enhanced_fallback_extraction(company_name, document_urls, "")
    
    def _enhanced_fallback_extraction(self, company_name: str, document_urls: List[str], search_snippets: str) -> CompanyInfo:
        """Enhanced fallback extraction when Nova Pro is not available"""
        logger.info("Using enhanced fallback extraction with search analysis")
        
        # Extract CIK from URLs
        cik = None
        for url in document_urls:
            cik_match = re.search(r'/data/(\d+)/', url)
            if cik_match:
                cik = cik_match.group(1).zfill(10)
                break
        
        # Analyze search snippets for information
        revenue = self._extract_revenue_from_snippets(search_snippets)
        employees = self._extract_employees_from_snippets(search_snippets)
        address = self._extract_address_from_snippets(search_snippets)
        fiscal_year = self._extract_fiscal_year_from_snippets(search_snippets)
        
        # Generate comprehensive business description
        business_desc = self._generate_business_description(company_name, search_snippets)
        
        return CompanyInfo(
            registered_legal_name=company_name,
            country_of_incorporation="United States",
            incorporation_date=f"Company incorporated, fiscal year ends {fiscal_year}" if fiscal_year else "Not specified in SEC documents",
            registered_business_address=address or "Not specified in SEC documents",
            company_identifiers={
                "CIK": cik or "Not specified in SEC documents",
                "DUNS": "Not specified in SEC documents",
                "LEI": "Not specified in SEC documents",
                "CUSIP": "Not specified in SEC documents"
            },
            business_description=business_desc,
            number_of_employees=employees or "Not specified in SEC documents",
            annual_revenue=revenue or "Not specified in SEC documents",
            annual_sales=revenue or "Not specified in SEC documents",
            website_url=self._generate_website_url(company_name)
        )
    
    def _extract_revenue_from_snippets(self, text: str) -> Optional[str]:
        """Extract revenue from search snippets"""
        if not text:
            return None
            
        patterns = [
            r'revenue[s]?\s+(?:of\s+|were\s+)?\$?([\d,]+\.?\d*)\s*(billion|million)',
            r'net\s+revenue[s]?\s+(?:of\s+)?\$?([\d,]+\.?\d*)\s*(billion|million)',
            r'total\s+revenue[s]?\s+(?:of\s+)?\$?([\d,]+\.?\d*)\s*(billion|million)',
            r'\$?([\d,]+\.?\d*)\s*(billion|million)\s+in\s+revenue',
            r'fiscal\s+year\s+\d{4}[^\d]*revenue[s]?\s+[^\d]*\$?([\d,]+\.?\d*)\s*(billion|million)'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                amount = match[0].replace(',', '')
                unit = match[1]
                try:
                    amount_float = float(amount)
                    if unit == 'billion' and amount_float > 0.1:
                        return f"${amount} billion (from SEC search results)"
                    elif unit == 'million' and amount_float > 100:
                        return f"${amount} million (from SEC search results)"
                except ValueError:
                    continue
        return None
    
    def _extract_employees_from_snippets(self, text: str) -> Optional[str]:
        """Extract employee count from search snippets"""
        if not text:
            return None
            
        patterns = [
            r'employ[s]?\s+(?:approximately\s+)?([\d,]+)\s+(?:people|employees)',
            r'([\d,]+)\s+employees',
            r'workforce\s+of\s+([\d,]+)',
            r'headcount\s+(?:of\s+)?([\d,]+)'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                count = match.replace(',', '')
                try:
                    count_int = int(count)
                    if 1000 <= count_int <= 10000000:
                        return f"{match} employees (from SEC search results)"
                except ValueError:
                    continue
        return None
    
    def _extract_address_from_snippets(self, text: str) -> Optional[str]:
        """Extract address from search snippets"""
        if not text:
            return None
            
        patterns = [
            r'headquarter[s]?\s+(?:are\s+)?(?:located\s+)?(?:at\s+)?([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'located\s+(?:at\s+)?([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'address[:\s]+([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                address = re.sub(r'\s+', ' ', match.strip())
                if 20 < len(address) < 200:
                    return address
        return None
    
    def _extract_fiscal_year_from_snippets(self, text: str) -> Optional[str]:
        """Extract fiscal year information from search snippets"""
        if not text:
            return None
            
        patterns = [
            r'fiscal\s+year\s+ended\s+(\w+\s+\d{1,2},\s+\d{4})',
            r'fiscal\s+year\s+ending\s+(\w+\s+\d{1,2},\s+\d{4})',
            r'for\s+the\s+fiscal\s+year\s+ended\s+(\w+\s+\d{1,2},\s+\d{4})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        return None
    
    def _generate_business_description(self, company_name: str, search_snippets: str) -> str:
        """Generate business description from search snippets"""
        if not search_snippets:
            return f"{company_name} - Business information available in SEC 10-K filings."
        
        # Look for business-related content in snippets
        business_keywords = []
        keywords_to_check = [
            'technology', 'software', 'hardware', 'services', 'products',
            'manufacturing', 'retail', 'financial', 'healthcare', 'energy',
            'automotive', 'telecommunications', 'entertainment', 'media'
        ]
        
        text_lower = search_snippets.lower()
        for keyword in keywords_to_check:
            if keyword in text_lower:
                business_keywords.append(keyword)
        
        if business_keywords:
            keywords_str = ', '.join(business_keywords[:5])
            return f"{company_name} operates in the {keywords_str} sector(s). The company is publicly traded with detailed business operations described in SEC 10-K filings."
        
        return f"{company_name} - Business information extracted from SEC 10-K filings and search results."
    
    def _generate_website_url(self, company_name: str) -> str:
        """Generate website URL from company name"""
        clean_name = company_name.lower()
        clean_name = re.sub(r'\s+(inc|corp|corporation|company|co|ltd)\.?$', '', clean_name)
        clean_name = clean_name.replace(' ', '').replace('.', '').replace(',', '')
        
        special_cases = {
            'apple': 'https://www.apple.com',
            'microsoft': 'https://www.microsoft.com',
            'tesla': 'https://www.tesla.com',
            'netflix': 'https://www.netflix.com',
            'amazon': 'https://www.amazon.com',
            'google': 'https://www.google.com',
            'alphabet': 'https://abc.xyz',
            'meta': 'https://www.meta.com',
            'nvidia': 'https://www.nvidia.com',
            'intel': 'https://www.intel.com'
        }
        
        return special_cases.get(clean_name, f"https://www.{clean_name}.com")

class NovaSECExtractor:
    """Main class following apple_sec_search.py approach with Nova Pro integration"""
    
    def __init__(self):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        self.nova_extractor = NovaProExtractor(profile="diligent")
        
        # Create output directory
        self.output_dir = Path("nova_sec_extractions")
        self.output_dir.mkdir(exist_ok=True)
    
    def _get_search_years(self) -> tuple[str, str]:
        """Get current year and previous year for SEC document search"""
        current_year = datetime.now().year
        previous_year = current_year - 1
        return str(current_year), str(previous_year)
    
    def search_and_extract(self, company_name: str, stock_symbol: str = None, year: str = None) -> Dict[str, Any]:
        """
        Main method following apple_sec_search.py approach with Nova Pro
        """
        try:
            # Get dynamic years if not specified
            current_year, previous_year = self._get_search_years()
            if year is None:
                year = f"{current_year} OR {previous_year}"
                logger.info(f"Using dynamic years: {current_year} (current) and {previous_year} (previous)")
            
            logger.info(f"Starting Nova Pro SEC data extraction for: {company_name}")
            
            # Step 1: Search for SEC documents (following apple_sec_search.py)
            search_results = self._search_sec_documents(company_name, year, current_year, previous_year)
            
            if not search_results.get('organic'):
                return self._create_empty_result(company_name, "No search results found")
            
            # Step 2: Extract and prioritize SEC document URLs (apple_sec_search.py approach)
            document_urls, sec_results = self._prioritize_sec_documents(
                search_results, company_name, stock_symbol, year, current_year, previous_year
            )
            
            if not document_urls:
                return self._create_empty_result(company_name, "No relevant SEC documents found")
            
            # Step 3: Collect search snippets for Nova Pro context
            search_snippets = self._collect_search_snippets(sec_results)
            
            # Step 4: Extract data using Nova Pro (following apple_sec_search.py)
            company_data = self.nova_extractor.extract_company_data(
                company_name, document_urls, search_snippets
            )
            
            # Step 5: Compile results (apple_sec_search.py format)
            results = {
                'search_query': f"{company_name} site:sec.gov 10-K {year} filetype:htm OR filetype:html",
                'search_timestamp': datetime.now().isoformat(),
                'search_focus': f'Latest 10-K Documents ({year})',
                'total_results': len(search_results.get('organic', [])),
                'sec_documents_found': len(document_urls),
                f'documents_with_{current_year}': len([r for r in sec_results if r.get(f'is_{current_year}', False)]),
                f'documents_with_{previous_year}': len([r for r in sec_results if r.get(f'is_{previous_year}', False)]),
                'documents_with_sec_filings': len([r for r in sec_results if r.get('is_sec_filing', False)]),
                'filing_types_found': list(set([r.get('filing_type', 'Unknown') for r in sec_results])),
                'company_information': asdict(company_data),
                'sec_documents': sec_results[:10],
                'extraction_method': 'Nova Pro SEC Analysis'
            }
            
            # Step 6: Save results
            self._save_results(results, company_name)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Nova Pro extraction: {e}")
            return self._create_empty_result(company_name, f"Extraction error: {str(e)}")
    
    def _search_sec_documents(self, company_name: str, year: str, current_year: str, previous_year: str) -> Dict[str, Any]:
        """Search for SEC documents (apple_sec_search.py approach)"""
        try:
            # Enhanced query to include latest quarterly reports and earnings data
            query = f"{company_name} site:sec.gov (10-K OR 10-Q OR 8-K) ({year}) (earnings OR quarterly OR annual) filetype:htm OR filetype:html"
            
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'num': 20,
                'gl': 'us',
                'hl': 'en',
                'tbs': 'qdr:y'
            }
            
            logger.info(f"Searching for latest {year} 10-K documents: {query}")
            
            response = requests.post("https://google.serper.dev/search", headers=headers, json=payload)
            response.raise_for_status()
            
            results = response.json()
            logger.info(f"Found {len(results.get('organic', []))} organic results")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching SEC documents: {e}")
            return {}
    
    def _prioritize_sec_documents(self, search_results: Dict, company_name: str, stock_symbol: str, year: str, current_year: str, previous_year: str) -> tuple:
        """Prioritize SEC documents (exact apple_sec_search.py approach)"""
        document_urls = []
        sec_results = []
        
        if not stock_symbol:
            stock_symbol = self._guess_stock_symbol(company_name)
        
        logger.info(f"Filtering results for {company_name} ({stock_symbol}) - {year}")
        
        # Process each result with priority scoring (from apple_sec_search.py)
        for result in search_results.get('organic', []):
            url = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Enhanced filtering (apple_sec_search.py logic)
            is_sec_document = any(keyword in url.lower() for keyword in ['sec.gov', 'edgar'])
            is_sec_filing = any(keyword in title.lower() or keyword in snippet.lower() 
                                for keyword in ['10-k', '10k', '10-q', '10q', '8-k', '8k', 'annual report', 'quarterly report', 'earnings'])
            # Handle dynamic year matching
            year_keywords = []
            
            if current_year in year:
                year_keywords.extend([
                    current_year, 
                    f'{current_year}0930', f'{current_year}-09-30', 
                    f'{current_year}1231', f'{current_year}-12-31'
                ])
            if previous_year in year:
                year_keywords.extend([
                    previous_year, 
                    f'{previous_year}0930', f'{previous_year}-09-30', 
                    f'{previous_year}1231', f'{previous_year}-12-31'
                ])
            
            is_target_year = any(keyword in title.lower() or keyword in snippet.lower() or keyword in url.lower()
                               for keyword in year_keywords)
            # Enhanced company matching
            company_keywords = [company_name.lower()]
            if stock_symbol:
                company_keywords.append(stock_symbol.lower())
            
            # Add company name parts for better matching
            company_parts = company_name.lower().replace(' corporation', '').replace(' corp', '').replace(' inc', '').split()
            for part in company_parts:
                if len(part) > 3:  # Only meaningful parts
                    company_keywords.append(part)
            
            is_target_company = any(keyword in title.lower() or keyword in snippet.lower() or keyword in url.lower()
                                  for keyword in company_keywords)
            
            # Enhanced priority scoring with better company matching
            priority_score = 0
            if is_sec_document: priority_score += 10
            if is_sec_filing: priority_score += 10
            if is_target_year: priority_score += 20
            if is_target_company: priority_score += 25  # Increased weight for target company
            
            # Boost for year in URL (prefer current year over previous year)
            if current_year in url.lower(): priority_score += 25
            elif previous_year in url.lower(): priority_score += 15
            
            # Enhanced boost for filing types with financial data (prioritize comprehensive data)
            if 'form 10-k' in title.lower() or '10-k' in title.lower(): priority_score += 20  # Annual reports (most comprehensive)
            if '10-q' in title.lower() and current_year in title.lower(): priority_score += 18  # Latest quarterly with financials
            if 'earnings' in title.lower() or 'earnings' in snippet.lower(): priority_score += 15  # Earnings reports
            if '8-k' in title.lower() and ('earnings' in snippet.lower() or 'financial' in snippet.lower()): priority_score += 12  # Financial 8-Ks
            elif '8-k' in title.lower(): priority_score += 5   # Non-financial 8-Ks (lower priority)
            
            # Boost for financial content indicators
            financial_indicators = ['revenue', 'sales', 'income', 'earnings', 'financial results', 'quarterly results']
            if any(indicator in snippet.lower() for indicator in financial_indicators): priority_score += 10
            
            # Additional scoring for exact company matches
            company_name_parts = company_name.lower().split()
            for part in company_name_parts:
                if len(part) > 3 and part in url.lower():
                    priority_score += 15
                if len(part) > 3 and part in title.lower():
                    priority_score += 10
            
            # Boost for stock symbol in URL (strong indicator)
            if stock_symbol and stock_symbol.lower() in url.lower():
                priority_score += 20
            
            if priority_score >= 15:  # apple_sec_search.py threshold
                document_urls.append(url)
                sec_results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'priority_score': priority_score,
                    f'is_{current_year}': current_year in title.lower() or current_year in snippet.lower() or current_year in url.lower(),
                    f'is_{previous_year}': previous_year in title.lower() or previous_year in snippet.lower() or previous_year in url.lower(),
                    'is_sec_filing': is_sec_filing,
                    'is_target_company': is_target_company,
                    'filing_type': self._identify_filing_type(title, snippet)
                })
        
        # Sort by priority (apple_sec_search.py approach)
        sec_results.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        document_urls = [result['url'] for result in sec_results]
        
        logger.info(f"Found {len(document_urls)} prioritized SEC 10-K document URLs for {year}")
        
        return document_urls, sec_results
    
    def _identify_filing_type(self, title: str, snippet: str) -> str:
        """Identify the type of SEC filing"""
        text = f"{title} {snippet}".lower()
        if '10-k' in text or 'annual report' in text:
            return '10-K (Annual)'
        elif '10-q' in text or 'quarterly report' in text:
            return '10-Q (Quarterly)'
        elif '8-k' in text or 'current report' in text:
            return '8-K (Current)'
        elif 'earnings' in text:
            return 'Earnings Report'
        else:
            return 'SEC Filing'
    
    def _collect_search_snippets(self, sec_results: List[Dict]) -> str:
        """Collect search snippets for Nova Pro context"""
        snippets = []
        for result in sec_results[:10]:  # Top 10 results
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            if title:
                snippets.append(f"Title: {title}")
            if snippet:
                snippets.append(f"Snippet: {snippet}")
        
        return "\n".join(snippets)
    
    def _guess_stock_symbol(self, company_name: str) -> str:
        """Guess stock symbol from company name"""
        name_map = {
            'apple': 'AAPL', 'microsoft': 'MSFT', 'tesla': 'TSLA',
            'amazon': 'AMZN', 'google': 'GOOGL', 'alphabet': 'GOOGL',
            'meta': 'META', 'facebook': 'META', 'netflix': 'NFLX',
            'nvidia': 'NVDA', 'intel': 'INTC', 'cisco': 'CSCO'
        }
        
        for key, symbol in name_map.items():
            if key in company_name.lower():
                return symbol
        
        words = company_name.split()
        if len(words) >= 2:
            return ''.join(word[0].upper() for word in words[:4])
        
        return company_name[:4].upper()
    
    def _create_empty_result(self, company_name: str, error_message: str) -> Dict[str, Any]:
        """Create empty result for failed extractions"""
        return {
            'search_timestamp': datetime.now().isoformat(),
            'company_searched': company_name,
            'error': error_message,
            'extraction_method': 'Failed'
        }
    
    def _save_results(self, result: Dict[str, Any], company_name: str):
        """Save results to JSON file"""
        safe_name = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_name}_nova_extraction_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {filepath}")
    
    def display_results(self, result: Dict[str, Any]):
        """Display results (apple_sec_search.py format)"""
        if 'error' in result:
            print(f"\nERROR: {result['error']}")
            return
        
        current_year, previous_year = self._get_search_years()
        company_info = result.get('company_information', {})
        
        print("\n" + "="*70)
        print(f"{result.get('company_searched', 'COMPANY').upper()} SEC DOCUMENT SEARCH & EXTRACTION RESULTS")
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
        
        print(f"\nCOMPANY IDENTIFIERS:")
        for key, value in company_info.get('company_identifiers', {}).items():
            print(f"{key}: {value}")
        
        print(f"\nBUSINESS DESCRIPTION:")
        print(company_info.get('business_description', 'N/A'))
        
        print(f"\nSEARCH SUMMARY:")
        print(f"Search Focus: {result.get('search_focus', 'SEC Documents')}")
        print(f"Total Results: {result.get('total_results', 0)}")
        print(f"SEC Documents Found: {result.get('sec_documents_found', 0)}")
        # Display dynamic year counts
        current_year, previous_year = self._get_search_years()
        print(f"{current_year} Documents: {result.get(f'documents_with_{current_year}', 0)}")
        print(f"{previous_year} Documents: {result.get(f'documents_with_{previous_year}', 0)}")
        print(f"SEC Filings Found: {result.get('documents_with_sec_filings', 0)}")
        filing_types = result.get('filing_types_found', [])
        if filing_types:
            print(f"Filing Types: {', '.join(filing_types)}")
        print(f"Query: {result.get('search_query', 'N/A')}")
        
        sec_docs = result.get('sec_documents', [])
        if sec_docs:
            print(f"\nLATEST 10-K DOCUMENTS FOUND (by priority):")
            for i, doc in enumerate(sec_docs[:5], 1):
                priority_indicator = "⭐" * min(3, doc.get('priority_score', 0) // 20)
                year_indicator = ""
                if doc.get(f'is_{current_year}', False):
                    year_indicator = f"📅 {current_year}"
                elif doc.get(f'is_{previous_year}', False):
                    year_indicator = f"📅 {previous_year}"
                filing_type = doc.get('filing_type', 'SEC Filing')
                filing_icon = "📋" if any(x in filing_type for x in ['10-K', '10-Q', '8-K']) else "📄"
                print(f"{i}. {priority_indicator} {doc['title']}")
                print(f"   URL: {doc['url']}")
                print(f"   {year_indicator} {filing_icon} {filing_type} Priority: {doc.get('priority_score', 0)}")
                print()

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python nova_sec_extractor.py \"Company Name\"")
        print("\nExamples:")
        print("  python nova_sec_extractor.py \"Apple Inc\"")
        print("  python nova_sec_extractor.py \"Microsoft Corporation\"")
        print("  python nova_sec_extractor.py \"Tesla Inc\"")
        return
    
    company_name = sys.argv[1]
    
    try:
        # Initialize the Nova SEC extractor
        extractor = NovaSECExtractor()
        
        # Extract company data using Nova Pro
        result = extractor.search_and_extract(company_name)
        
        # Display results
        extractor.display_results(result)
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
