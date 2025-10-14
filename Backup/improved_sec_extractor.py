#!/usr/bin/env python3
"""
Improved SEC Document Data Extractor
Based on apple_sec_search.py approach with real document processing
"""

import os
import sys
import json
import logging
import requests
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

class ImprovedSECExtractor:
    """Improved SEC data extraction following apple_sec_search.py approach"""
    
    def __init__(self):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        # Create output directory
        self.output_dir = Path("improved_sec_extractions")
        self.output_dir.mkdir(exist_ok=True)
    
    def search_and_extract(self, company_name: str, stock_symbol: str = None, year: str = "2024") -> Dict[str, Any]:
        """
        Main method following apple_sec_search.py approach
        """
        try:
            logger.info(f"Starting improved SEC data extraction for: {company_name}")
            
            # Step 1: Search for SEC documents with enhanced query
            search_results = self._search_sec_documents(company_name, year)
            
            if not search_results.get('organic'):
                logger.warning(f"No search results found for {company_name}")
                return self._create_empty_result(company_name, "No search results found")
            
            # Step 2: Extract and prioritize SEC document URLs (following apple_sec_search.py)
            document_urls, sec_results = self._prioritize_sec_documents(
                search_results, company_name, stock_symbol, year
            )
            
            if not document_urls:
                logger.warning(f"No relevant SEC documents found for {company_name}")
                return self._create_empty_result(company_name, "No relevant SEC documents found")
            
            # Step 3: Extract data from the best documents
            company_data = self._extract_from_documents(company_name, document_urls[:3])  # Top 3 documents
            
            # Step 4: Compile results
            results = {
                'search_query': f"{company_name} site:sec.gov 10-K {year} filetype:htm OR filetype:html",
                'search_timestamp': datetime.now().isoformat(),
                'search_focus': f'Latest {year} 10-K Documents',
                'total_results': len(search_results.get('organic', [])),
                'sec_documents_found': len(document_urls),
                'documents_with_year': len([r for r in sec_results if r.get(f'is_{year}', False)]),
                'documents_with_10k': len([r for r in sec_results if r.get('is_10k', False)]),
                'company_information': asdict(company_data),
                'sec_documents': sec_results[:10],  # Top 10 for reference
                'extraction_method': 'Improved SEC Document Analysis'
            }
            
            # Step 5: Save results
            self._save_results(results, company_name)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in company data extraction: {e}")
            return self._create_empty_result(company_name, f"Extraction error: {str(e)}")
    
    def _search_sec_documents(self, company_name: str, year: str) -> Dict[str, Any]:
        """Search for SEC documents using enhanced query"""
        try:
            # Enhanced query following apple_sec_search.py approach
            query = f"{company_name} site:sec.gov 10-K {year} filetype:htm OR filetype:html"
            
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'num': 20,  # Get more results for better filtering
                'gl': 'us',
                'hl': 'en',
                'tbs': 'qdr:y'  # Results from past year
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
    
    def _prioritize_sec_documents(self, search_results: Dict, company_name: str, stock_symbol: str, year: str) -> tuple:
        """
        Extract and prioritize SEC document URLs following apple_sec_search.py approach
        """
        document_urls = []
        sec_results = []
        
        # Generate stock symbol if not provided
        if not stock_symbol:
            stock_symbol = self._guess_stock_symbol(company_name)
        
        logger.info(f"Filtering results for {company_name} ({stock_symbol}) - {year}")
        
        # Process each search result with priority scoring (from apple_sec_search.py)
        for result in search_results.get('organic', []):
            url = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Enhanced filtering for target year 10-K documents
            is_sec_document = any(keyword in url.lower() for keyword in ['sec.gov', 'edgar'])
            is_10k_document = any(keyword in title.lower() or keyword in snippet.lower() 
                                for keyword in ['10-k', '10k', 'annual report'])
            is_target_year = any(keyword in title.lower() or keyword in snippet.lower() or keyword in url.lower()
                               for keyword in [year, f'{year}0930', f'{year}-09-30', f'{year}1231', f'{year}-12-31'])
            is_target_company = any(keyword in title.lower() or keyword in snippet.lower() 
                                  for keyword in [company_name.lower(), stock_symbol.lower() if stock_symbol else ''])
            
            # Priority scoring system (from apple_sec_search.py)
            priority_score = 0
            if is_sec_document: priority_score += 10
            if is_10k_document: priority_score += 10
            if is_target_year: priority_score += 20
            if is_target_company: priority_score += 5
            if year in url.lower(): priority_score += 15
            if 'form 10-k' in title.lower(): priority_score += 10
            
            # Additional scoring for document quality
            if 'htm' in url.lower(): priority_score += 5
            if company_name.lower().replace(' ', '') in url.lower(): priority_score += 10
            
            if priority_score >= 15:  # Minimum threshold for relevance
                document_urls.append(url)
                sec_results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'priority_score': priority_score,
                    f'is_{year}': is_target_year,
                    'is_10k': is_10k_document,
                    'is_target_company': is_target_company
                })
        
        # Sort by priority score (highest first)
        sec_results.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        document_urls = [result['url'] for result in sec_results]
        
        logger.info(f"Found {len(document_urls)} prioritized SEC 10-K document URLs for {year}")
        
        return document_urls, sec_results
    
    def _extract_from_documents(self, company_name: str, document_urls: List[str]) -> CompanyInfo:
        """
        Extract company information from actual SEC documents
        """
        logger.info(f"Extracting data from {len(document_urls)} SEC documents")
        
        # Collect content from documents
        all_content = ""
        successful_fetches = 0
        
        for i, url in enumerate(document_urls):
            try:
                logger.info(f"Fetching document {i+1}/{len(document_urls)}: {url}")
                content = self._fetch_document_content(url)
                if content:
                    all_content += " " + content
                    successful_fetches += 1
                    if successful_fetches >= 2:  # Limit to avoid too much content
                        break
                time.sleep(1)  # Be respectful to SEC.gov
            except Exception as e:
                logger.warning(f"Error fetching document {url}: {e}")
                continue
        
        if not all_content:
            logger.warning("Could not fetch any document content, using URL analysis")
            return self._extract_from_urls(company_name, document_urls)
        
        logger.info(f"Analyzing {len(all_content)} characters of document content")
        
        # Extract information from document content
        return self._extract_from_content(company_name, all_content, document_urls)
    
    def _fetch_document_content(self, url: str, max_chars: int = 50000) -> Optional[str]:
        """Fetch content from SEC document URL"""
        try:
            headers = {
                'User-Agent': 'Sample Company Name AdminContact@<sample company domain>.com',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                # Remove HTML tags and clean up
                clean_content = re.sub(r'<[^>]+>', ' ', content)
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                return clean_content[:max_chars]
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
                
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            return None
    
    def _extract_from_content(self, company_name: str, content: str, document_urls: List[str]) -> CompanyInfo:
        """Extract company information from document content"""
        
        # Extract CIK from URLs
        cik = self._extract_cik_from_urls(document_urls)
        
        # Extract detailed information using comprehensive patterns
        revenue = self._extract_revenue_from_content(content)
        employees = self._extract_employees_from_content(content)
        address = self._extract_address_from_content(content)
        legal_name = self._extract_legal_name_from_content(content, company_name)
        incorporation_date = self._extract_incorporation_date_from_content(content)
        business_desc = self._extract_business_description_from_content(content, company_name)
        
        return CompanyInfo(
            registered_legal_name=legal_name or company_name,
            country_of_incorporation="United States",
            incorporation_date=incorporation_date or "Available in SEC documents",
            registered_business_address=address or "Available in SEC documents",
            company_identifiers={
                "CIK": cik or "Available in SEC documents",
                "DUNS": "Available in SEC documents",
                "LEI": "Available in SEC documents",
                "CUSIP": "Available in SEC documents"
            },
            business_description=business_desc,
            number_of_employees=employees or "Available in SEC documents",
            annual_revenue=revenue or "Available in SEC documents",
            annual_sales=revenue or "Available in SEC documents",
            website_url=self._generate_website_url(company_name)
        )
    
    def _extract_revenue_from_content(self, content: str) -> Optional[str]:
        """Extract revenue from document content with comprehensive patterns"""
        patterns = [
            # Direct revenue statements
            r'total\s+(?:net\s+)?revenues?\s+(?:were\s+|of\s+)?\$?([\d,]+\.?\d*)\s*(million|billion)',
            r'net\s+revenues?\s+(?:were\s+|of\s+)?\$?([\d,]+\.?\d*)\s*(million|billion)',
            r'revenues?\s+(?:were\s+|of\s+)?\$?([\d,]+\.?\d*)\s*(million|billion)',
            r'total\s+revenues?\s+\$?([\d,]+\.?\d*)\s*(million|billion)',
            
            # Financial statement patterns
            r'revenues?\s+\$?([\d,]+\.?\d*)\s*(million|billion)',
            r'net\s+sales\s+\$?([\d,]+\.?\d*)\s*(million|billion)',
            r'total\s+net\s+sales\s+\$?([\d,]+\.?\d*)\s*(million|billion)',
            
            # Fiscal year patterns
            r'fiscal\s+year\s+\d{4}[^\d]*revenues?\s+[^\d]*\$?([\d,]+\.?\d*)\s*(million|billion)',
            r'for\s+the\s+year\s+ended[^\d]*revenues?\s+[^\d]*\$?([\d,]+\.?\d*)\s*(million|billion)',
            
            # Table patterns (common in 10-K)
            r'revenues?\s*[\s\$]+([\d,]+)\s*(million|billion)',
            r'total\s+revenues?\s*[\s\$]+([\d,]+)\s*(million|billion)'
        ]
        
        content_lower = content.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                amount = match[0].replace(',', '')
                unit = match[1]
                try:
                    # Validate it's a reasonable revenue number
                    amount_float = float(amount)
                    if unit == 'billion' and amount_float > 0.1:  # At least 100M
                        return f"${amount} billion (from SEC 10-K)"
                    elif unit == 'million' and amount_float > 100:  # At least 100M
                        return f"${amount} million (from SEC 10-K)"
                except ValueError:
                    continue
        
        return None
    
    def _extract_employees_from_content(self, content: str) -> Optional[str]:
        """Extract employee count from document content"""
        patterns = [
            r'employed\s+approximately\s+([\d,]+)\s+(?:full-time\s+)?(?:people|employees|persons)',
            r'approximately\s+([\d,]+)\s+(?:full-time\s+)?employees',
            r'total\s+employees\s+(?:of\s+)?([\d,]+)',
            r'workforce\s+of\s+(?:approximately\s+)?([\d,]+)',
            r'employs\s+(?:approximately\s+)?([\d,]+)\s+(?:people|employees)',
            r'([\d,]+)\s+employees\s+worldwide',
            r'headcount\s+of\s+([\d,]+)',
            r'as\s+of\s+\w+\s+\d+,\s+\d{4}[^\d]+([\d,]+)\s+employees'
        ]
        
        content_lower = content.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                count = match.replace(',', '') if isinstance(match, str) else match
                try:
                    count_int = int(count)
                    if 1000 <= count_int <= 10000000:  # Reasonable range
                        return f"{match} employees (from SEC 10-K)"
                except ValueError:
                    continue
        
        return None
    
    def _extract_address_from_content(self, content: str) -> Optional[str]:
        """Extract business address from document content"""
        patterns = [
            r'principal\s+executive\s+offices?\s+are\s+located\s+at\s+([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'corporate\s+headquarters\s+(?:are\s+)?(?:located\s+)?(?:at\s+)?([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'headquarters\s+(?:are\s+)?(?:located\s+)?(?:at\s+)?([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'business\s+address[:\s]+([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'located\s+at\s+([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)',
            r'offices\s+at\s+([^.]+(?:street|avenue|road|drive|way|blvd|boulevard|parkway)[^.]*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean up the address
                address = re.sub(r'\s+', ' ', match.strip())
                if len(address) > 20 and len(address) < 200:  # Reasonable address length
                    return address
        
        return None
    
    def _extract_legal_name_from_content(self, content: str, company_name: str) -> Optional[str]:
        """Extract legal company name from document content"""
        escaped_name = re.escape(company_name)
        spaced_name = company_name.replace(" ", r"\s+")
        
        patterns = [
            rf'({escaped_name}[,\s]+(?:Inc\.?|Corporation|Corp\.?|LLC|Ltd\.?))',
            rf'({spaced_name}[,\s]+(?:Inc\.?|Corporation|Corp\.?|LLC|Ltd\.?))',
            r'([\w\s]+(?:Inc\.?|Corporation|Corp\.?|LLC|Ltd\.?))\s+(?:\(the\s+)?(?:"Company"|Company)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) > 5 and len(match) < 100:
                    return match.strip()
        
        return None
    
    def _extract_incorporation_date_from_content(self, content: str) -> Optional[str]:
        """Extract incorporation date from document content"""
        patterns = [
            r'incorporated\s+(?:in\s+)?(?:the\s+state\s+of\s+)?[\w\s]+(?:on\s+|in\s+)?(\w+\s+\d{1,2},\s+\d{4})',
            r'incorporation\s+(?:date\s+)?(?:was\s+)?(\w+\s+\d{1,2},\s+\d{4})',
            r'founded\s+(?:in\s+|on\s+)?(\w+\s+\d{1,2},\s+\d{4})',
            r'established\s+(?:in\s+|on\s+)?(\w+\s+\d{1,2},\s+\d{4})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                return match
        
        return None
    
    def _extract_business_description_from_content(self, content: str, company_name: str) -> str:
        """Extract business description from document content"""
        # Look for business overview sections
        business_patterns = [
            r'business\s+overview[^\n]*\n([^\n]{100,500})',
            r'our\s+business[^\n]*\n([^\n]{100,500})',
            r'company\s+overview[^\n]*\n([^\n]{100,500})',
            r'we\s+(?:are\s+|operate\s+|provide\s+|design\s+|manufacture\s+)([^\n]{100,500})',
            rf'{re.escape(company_name)}[^\n]*(?:is\s+|operates\s+|provides\s+|designs\s+|manufactures\s+)([^\n]{{100,500}})'
        ]
        
        for pattern in business_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                clean_desc = re.sub(r'\s+', ' ', match.strip())
                if len(clean_desc) > 50:
                    return f"{company_name} - {clean_desc} (from SEC 10-K filing)"
        
        return f"{company_name} - Detailed business information available in SEC 10-K filings."
    
    def _extract_from_urls(self, company_name: str, document_urls: List[str]) -> CompanyInfo:
        """Fallback extraction from URLs when content can't be fetched"""
        cik = self._extract_cik_from_urls(document_urls)
        
        return CompanyInfo(
            registered_legal_name=company_name,
            country_of_incorporation="United States",
            incorporation_date="Available in SEC documents",
            registered_business_address="Available in SEC documents",
            company_identifiers={
                "CIK": cik or "Available in SEC documents",
                "DUNS": "Available in SEC documents",
                "LEI": "Available in SEC documents",
                "CUSIP": "Available in SEC documents"
            },
            business_description=f"{company_name} - Business information available in SEC 10-K filings.",
            number_of_employees="Available in SEC documents",
            annual_revenue="Available in SEC documents",
            annual_sales="Available in SEC documents",
            website_url=self._generate_website_url(company_name)
        )
    
    def _extract_cik_from_urls(self, document_urls: List[str]) -> Optional[str]:
        """Extract CIK from SEC document URLs"""
        for url in document_urls:
            cik_match = re.search(r'/data/(\d+)/', url)
            if cik_match:
                return cik_match.group(1).zfill(10)
        return None
    
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
        
        # Generate from first letters
        words = company_name.split()
        if len(words) >= 2:
            return ''.join(word[0].upper() for word in words[:4])
        
        return company_name[:4].upper()
    
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
            'intel': 'https://www.intel.com',
            'cisco': 'https://www.cisco.com'
        }
        
        return special_cases.get(clean_name, f"https://www.{clean_name}.com")
    
    def _create_empty_result(self, company_name: str, error_message: str) -> Dict[str, Any]:
        """Create empty result for failed extractions"""
        return {
            'search_timestamp': datetime.now().isoformat(),
            'company_searched': company_name,
            'error': error_message,
            'extraction_method': 'Failed',
            'company_information': {
                'registered_legal_name': company_name,
                'error': error_message
            }
        }
    
    def _save_results(self, result: Dict[str, Any], company_name: str):
        """Save results to JSON file"""
        safe_name = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_name}_improved_extraction_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {filepath}")
    
    def display_results(self, result: Dict[str, Any]):
        """Display results following apple_sec_search.py format"""
        if 'error' in result:
            print(f"\nERROR: {result['error']}")
            return
        
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
        print(f"Year Documents: {result.get('documents_with_year', 0)}")
        print(f"10-K Documents: {result.get('documents_with_10k', 0)}")
        print(f"Query: {result.get('search_query', 'N/A')}")
        
        sec_docs = result.get('sec_documents', [])
        if sec_docs:
            print(f"\nLATEST 10-K DOCUMENTS FOUND (by priority):")
            for i, doc in enumerate(sec_docs[:5], 1):
                priority_indicator = "⭐" * min(3, doc.get('priority_score', 0) // 20)
                year_indicator = "📅 2024" if doc.get('is_2024', False) else ""
                doc_type = "📋 10-K" if doc.get('is_10k', False) else ""
                print(f"{i}. {priority_indicator} {doc['title']}")
                print(f"   URL: {doc['url']}")
                print(f"   {year_indicator} {doc_type} Priority: {doc.get('priority_score', 0)}")
                print()

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python improved_sec_extractor.py \"Company Name\"")
        print("\nExamples:")
        print("  python improved_sec_extractor.py \"Apple Inc\"")
        print("  python improved_sec_extractor.py \"Microsoft Corporation\"")
        print("  python improved_sec_extractor.py \"Tesla Inc\"")
        return
    
    company_name = sys.argv[1]
    
    try:
        # Initialize the improved extractor
        extractor = ImprovedSECExtractor()
        
        # Extract company data
        result = extractor.search_and_extract(company_name)
        
        # Display results
        extractor.display_results(result)
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
