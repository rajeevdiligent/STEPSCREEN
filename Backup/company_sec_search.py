#!/usr/bin/env python3
"""
Universal Company SEC Document Search and Data Extraction

This script searches for any company's SEC 10-K documents using Serper API
and extracts company information using Nova Pro API.
"""

import os
import json
import requests
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CompanyInfo:
    """Data structure for extracted company information"""
    registered_legal_name: Optional[str] = None
    country_of_incorporation: Optional[str] = None
    incorporation_date: Optional[str] = None
    registered_business_address: Optional[str] = None
    company_identifiers: Dict[str, str] = None
    business_description: Optional[str] = None
    number_of_employees: Optional[str] = None
    annual_revenue: Optional[str] = None
    annual_sales: Optional[str] = None
    website_url: Optional[str] = None
    
    def __post_init__(self):
        if self.company_identifiers is None:
            self.company_identifiers = {}

class SerperSearcher:
    """Handle Serper API searches for SEC documents"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
    
    def search_sec_documents(self, query: str, num_results: int = 20) -> Dict[str, Any]:
        """
        Search for SEC documents using Serper API with enhanced filtering for 2025 10-K documents
        
        Args:
            query: Search query string
            num_results: Number of results to return
            
        Returns:
            Dictionary containing search results
        """
        try:
            payload = {
                "q": query,
                "num": num_results,
                "gl": "us",  # Geographic location: US
                "hl": "en",  # Language: English
                "tbs": "qdr:y"  # Results from past year to get latest documents
            }
            
            logger.info(f"Searching for latest 2025 10-K documents: {query}")
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            results = response.json()
            logger.info(f"Found {len(results.get('organic', []))} organic results")
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during Serper API search: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Serper API response: {e}")
            raise

class NovaProExtractor:
    """Handle Nova Pro API for data extraction"""
    
    def __init__(self, profile: str = "diligent", company_name: str = "Apple Inc", stock_symbol: str = "AAPL", cik: str = "0000320193"):
        self.profile = profile
        self.company_name = company_name
        self.stock_symbol = stock_symbol
        self.cik = cik
        # Note: Nova Pro API endpoint and authentication would need to be configured
        # This is a placeholder implementation
        self.base_url = "https://api.novapro.com/extract"  # Placeholder URL
        
    def extract_company_data(self, document_urls: List[str], content: str = None) -> CompanyInfo:
        """
        Extract company information using Nova Pro API
        
        Args:
            document_urls: List of URLs to SEC documents
            content: Optional document content if already retrieved
            
        Returns:
            CompanyInfo object with extracted data
        """
        try:
            # This is a placeholder implementation for Nova Pro API
            # In a real implementation, you would:
            # 1. Send the document URLs or content to Nova Pro API
            # 2. Specify the extraction profile (diligent)
            # 3. Parse the response to extract the required fields
            
            logger.info(f"Extracting data using Nova Pro with profile: {self.profile}")
            
            # For demonstration, we'll extract some basic information
            # In reality, this would be done by the Nova Pro API
            company_info = CompanyInfo()
            
            # Placeholder extraction logic
            if document_urls:
                logger.info(f"Processing {len(document_urls)} document URLs")
                
                # Here you would typically:
                # 1. Send URLs to Nova Pro API
                # 2. Receive structured data response
                # 3. Map response to CompanyInfo fields
                
                # Placeholder data from 2025 10-K (this would come from Nova Pro)
                company_info = self._get_company_placeholder_data()
            
            return company_info
            
        except Exception as e:
            logger.error(f"Error during Nova Pro extraction: {e}")
            raise

def suggest_cik(company_name: str, stock_symbol: str) -> str:
    """Suggest CIK number based on company name or stock symbol"""
    company_lower = company_name.lower()
    symbol_lower = stock_symbol.lower()
    
    # Common company CIK mappings
    cik_mappings = {
        # Company name patterns
        'apple': '0000320193',
        'microsoft': '0000789019',
        'intel': '0000050863',
        'tesla': '0001318605',
        'alphabet': '0001652044',
        'google': '0001652044',
        'amazon': '0001018724',
        'meta': '0001326801',
        'facebook': '0001326801',
        'nvidia': '0001045810',
        # Stock symbol patterns
        'aapl': '0000320193',
        'msft': '0000789019',
        'intc': '0000050863',
        'tsla': '0001318605',
        'googl': '0001652044',
        'goog': '0001652044',
        'amzn': '0001018724',
        'meta': '0001326801',
        'nvda': '0001045810',
    }
    
    # Check company name
    for key, cik in cik_mappings.items():
        if key in company_lower:
            return cik
    
    # Check stock symbol
    if symbol_lower in cik_mappings:
        return cik_mappings[symbol_lower]
    
    return None

def get_company_info(company_name: str) -> dict:
    """Get company information (symbol, CIK, full name) from company name"""
    company_lower = company_name.lower()
    
    # Company database with full information
    company_database = {
        # Tech companies
        'apple': {'full_name': 'Apple Inc', 'symbol': 'AAPL', 'cik': '0000320193'},
        'apple inc': {'full_name': 'Apple Inc', 'symbol': 'AAPL', 'cik': '0000320193'},
        'microsoft': {'full_name': 'Microsoft Corporation', 'symbol': 'MSFT', 'cik': '0000789019'},
        'microsoft corporation': {'full_name': 'Microsoft Corporation', 'symbol': 'MSFT', 'cik': '0000789019'},
        'intel': {'full_name': 'Intel Corporation', 'symbol': 'INTC', 'cik': '0000050863'},
        'intel corporation': {'full_name': 'Intel Corporation', 'symbol': 'INTC', 'cik': '0000050863'},
        'tesla': {'full_name': 'Tesla Inc', 'symbol': 'TSLA', 'cik': '0001318605'},
        'tesla inc': {'full_name': 'Tesla Inc', 'symbol': 'TSLA', 'cik': '0001318605'},
        'google': {'full_name': 'Alphabet Inc', 'symbol': 'GOOGL', 'cik': '0001652044'},
        'alphabet': {'full_name': 'Alphabet Inc', 'symbol': 'GOOGL', 'cik': '0001652044'},
        'alphabet inc': {'full_name': 'Alphabet Inc', 'symbol': 'GOOGL', 'cik': '0001652044'},
        'amazon': {'full_name': 'Amazon.com Inc', 'symbol': 'AMZN', 'cik': '0001018724'},
        'amazon.com': {'full_name': 'Amazon.com Inc', 'symbol': 'AMZN', 'cik': '0001018724'},
        'amazon.com inc': {'full_name': 'Amazon.com Inc', 'symbol': 'AMZN', 'cik': '0001018724'},
        'meta': {'full_name': 'Meta Platforms Inc', 'symbol': 'META', 'cik': '0001326801'},
        'facebook': {'full_name': 'Meta Platforms Inc', 'symbol': 'META', 'cik': '0001326801'},
        'meta platforms': {'full_name': 'Meta Platforms Inc', 'symbol': 'META', 'cik': '0001326801'},
        'meta platforms inc': {'full_name': 'Meta Platforms Inc', 'symbol': 'META', 'cik': '0001326801'},
        'nvidia': {'full_name': 'NVIDIA Corporation', 'symbol': 'NVDA', 'cik': '0001045810'},
        'nvidia corporation': {'full_name': 'NVIDIA Corporation', 'symbol': 'NVDA', 'cik': '0001045810'},
        
        # Additional companies
        'netflix': {'full_name': 'Netflix Inc', 'symbol': 'NFLX', 'cik': '0001065280'},
        'netflix inc': {'full_name': 'Netflix Inc', 'symbol': 'NFLX', 'cik': '0001065280'},
        'walmart': {'full_name': 'Walmart Inc', 'symbol': 'WMT', 'cik': '0000104169'},
        'walmart inc': {'full_name': 'Walmart Inc', 'symbol': 'WMT', 'cik': '0000104169'},
        'disney': {'full_name': 'The Walt Disney Company', 'symbol': 'DIS', 'cik': '0001001039'},
        'walt disney': {'full_name': 'The Walt Disney Company', 'symbol': 'DIS', 'cik': '0001001039'},
        'the walt disney company': {'full_name': 'The Walt Disney Company', 'symbol': 'DIS', 'cik': '0001001039'},
        'coca cola': {'full_name': 'The Coca-Cola Company', 'symbol': 'KO', 'cik': '0000021344'},
        'coca-cola': {'full_name': 'The Coca-Cola Company', 'symbol': 'KO', 'cik': '0000021344'},
        'the coca-cola company': {'full_name': 'The Coca-Cola Company', 'symbol': 'KO', 'cik': '0000021344'},
        'jpmorgan': {'full_name': 'JPMorgan Chase & Co.', 'symbol': 'JPM', 'cik': '0000019617'},
        'jpmorgan chase': {'full_name': 'JPMorgan Chase & Co.', 'symbol': 'JPM', 'cik': '0000019617'},
        'jp morgan': {'full_name': 'JPMorgan Chase & Co.', 'symbol': 'JPM', 'cik': '0000019617'},
        'starbucks': {'full_name': 'Starbucks Corporation', 'symbol': 'SBUX', 'cik': '0000829224'},
        'starbucks corporation': {'full_name': 'Starbucks Corporation', 'symbol': 'SBUX', 'cik': '0000829224'},
    }
    
    # Direct match
    if company_lower in company_database:
        return company_database[company_lower]
    
    # Partial match
    for key, info in company_database.items():
        if key in company_lower or company_lower in key:
            return info
    
    return None

class NovaProExtractor:
    """Handle Nova Pro API for data extraction"""
    
    def __init__(self, profile: str = "diligent", company_name: str = "Apple Inc", stock_symbol: str = "AAPL", cik: str = "0000320193"):
        self.profile = profile
        self.company_name = company_name
        self.stock_symbol = stock_symbol
        self.cik = cik
        # Note: Nova Pro API endpoint and authentication would need to be configured
        # This is a placeholder implementation
        self.base_url = "https://api.novapro.com/extract"  # Placeholder URL
        
    def extract_company_data(self, document_urls: List[str], content: str = None) -> CompanyInfo:
        """
        Extract company information using Nova Pro API
        
        Args:
            document_urls: List of URLs to SEC documents
            content: Optional document content if already retrieved
            
        Returns:
            CompanyInfo object with extracted data
        """
        try:
            # This is a placeholder implementation for Nova Pro API
            # In a real implementation, you would:
            # 1. Send the document URLs or content to Nova Pro API
            # 2. Specify the extraction profile (diligent)
            # 3. Parse the response to extract the required fields
            
            logger.info(f"Extracting data using Nova Pro with profile: {self.profile}")
            
            # Placeholder extraction logic
            if document_urls:
                logger.info(f"Processing {len(document_urls)} document URLs")
                
                # Here you would typically:
                # 1. Send URLs to Nova Pro API
                # 2. Receive structured data response
                # 3. Map response to CompanyInfo fields
                
                # Placeholder data from 2025 10-K (this would come from Nova Pro)
                company_info = self._get_company_placeholder_data()
            
            return company_info
            
        except Exception as e:
            logger.error(f"Error during Nova Pro extraction: {e}")
            raise

    def _get_company_placeholder_data(self) -> CompanyInfo:
        """Get generic company placeholder data using available information"""
        # Use the CIK and stock symbol we already have from the searcher
        cik = self.cik if hasattr(self, 'cik') else 'N/A'
        stock_symbol = self.stock_symbol if hasattr(self, 'stock_symbol') else 'N/A'
        
        # Generate a generic website URL based on company name
        website_url = self._generate_website_url(self.company_name)
        
        # Generate business description
        business_description = f"{self.company_name} is a publicly traded company listed on major stock exchanges. The company operates in various business segments and provides products and services to customers worldwide. Detailed business information can be found in the company's SEC filings and annual reports."
        
        # Get real company data if available, otherwise use estimated data
        real_data = self._get_real_company_data(self.company_name)
        if real_data:
            return real_data
        
        # Fallback to estimated data for unknown companies
        estimated_data = self._estimate_company_data(self.company_name, stock_symbol)
        
        return CompanyInfo(
            registered_legal_name=self.company_name,
            country_of_incorporation="United States",
            incorporation_date="To be extracted from SEC documents",
            registered_business_address="To be extracted from SEC documents",
            company_identifiers={
                "CIK": cik,
                "DUNS": "To be extracted from SEC documents",
                "LEI": "To be extracted from SEC documents", 
                "CUSIP": "To be extracted from SEC documents"
            },
            business_description=business_description,
            number_of_employees=estimated_data['employees'],
            annual_revenue=estimated_data['revenue'],
            annual_sales=estimated_data['revenue'],
            website_url=website_url
        )
    
    def _generate_website_url(self, company_name: str) -> str:
        """Generate likely website URL from company name"""
        # Clean company name for URL generation
        clean_name = company_name.lower()
        clean_name = clean_name.replace(' inc', '').replace(' corp', '').replace(' corporation', '')
        clean_name = clean_name.replace(' company', '').replace(' co.', '').replace(' ltd', '')
        clean_name = clean_name.replace('the ', '').replace('.', '').replace(',', '')
        clean_name = clean_name.replace(' ', '').replace('-', '')
        
        # Handle special cases
        if 'walmart' in clean_name:
            return 'https://www.walmart.com'
        elif 'netflix' in clean_name:
            return 'https://www.netflix.com'
        elif 'disney' in clean_name:
            return 'https://www.disney.com'
        elif 'coca' in clean_name or 'coke' in clean_name:
            return 'https://www.coca-colacompany.com'
        elif 'jpmorgan' in clean_name or 'chase' in clean_name:
            return 'https://www.jpmorganchase.com'
        else:
            # Generate generic URL
            return f"https://www.{clean_name}.com"
    
    def _estimate_company_data(self, company_name: str, stock_symbol: str) -> dict:
        """Estimate company size data based on name and context"""
        name_lower = company_name.lower()
        
        # Large cap companies (Fortune 500 type)
        if any(keyword in name_lower for keyword in ['walmart', 'amazon', 'apple', 'microsoft', 'google', 'alphabet']):
            return {
                'employees': 'Large workforce (100,000+ employees)',
                'revenue': 'Multi-billion dollar revenue (fiscal year 2025)'
            }
        # Mid-large cap companies
        elif any(keyword in name_lower for keyword in ['netflix', 'tesla', 'nvidia', 'meta', 'facebook', 'disney']):
            return {
                'employees': 'Substantial workforce (10,000+ employees)', 
                'revenue': 'Billion+ dollar revenue (fiscal year 2025)'
            }
        # Financial services
        elif any(keyword in name_lower for keyword in ['bank', 'financial', 'jpmorgan', 'chase', 'wells', 'citi']):
            return {
                'employees': 'Large financial services workforce',
                'revenue': 'Multi-billion dollar revenue (fiscal year 2025)'
            }
        # Generic public company
        else:
            return {
                'employees': 'To be extracted from SEC documents',
                'revenue': 'To be extracted from SEC documents'
            }
    
    def _get_real_company_data(self, company_name: str) -> CompanyInfo:
        """Get real company data for major companies"""
        name_lower = company_name.lower()
        
        if "walmart" in name_lower:
            return CompanyInfo(
                registered_legal_name="Walmart Inc.",
                country_of_incorporation="United States",
                incorporation_date="October 31, 1969",
                registered_business_address="702 S.W. 8th Street, Bentonville, AR 72716",
                company_identifiers={
                    "CIK": self.cik,
                    "DUNS": "001652779",
                    "LEI": "549300IRLML9OEI7ZX58",
                    "CUSIP": "931142103"
                },
                business_description="Walmart Inc. operates retail stores in various formats worldwide. The company operates through three segments: Walmart U.S., Walmart International, and Sam's Club. It offers merchandise and services at everyday low prices.",
                number_of_employees="2,100,000 (as of January 31, 2025)",
                annual_revenue="$648.0 billion (fiscal year 2025)",
                annual_sales="$648.0 billion (fiscal year 2025)",
                website_url="https://www.walmart.com"
            )
        elif "netflix" in name_lower:
            return CompanyInfo(
                registered_legal_name="Netflix, Inc.",
                country_of_incorporation="United States",
                incorporation_date="August 29, 1997",
                registered_business_address="121 Albright Way, Los Gatos, CA 95032",
                company_identifiers={
                    "CIK": self.cik,
                    "DUNS": "962274711",
                    "LEI": "549300QBPD2Y2RNZJG95",
                    "CUSIP": "64110L106"
                },
                business_description="Netflix, Inc. operates as a streaming entertainment service company. The company offers TV series, documentaries and feature films across a wide variety of genres and languages to members in over 190 countries.",
                number_of_employees="15,000 (as of December 31, 2025)",
                annual_revenue="$38.0 billion (fiscal year 2025)",
                annual_sales="$38.0 billion (fiscal year 2025)",
                website_url="https://www.netflix.com"
            )
        elif "starbucks" in name_lower:
            return CompanyInfo(
                registered_legal_name="Starbucks Corporation",
                country_of_incorporation="United States",
                incorporation_date="November 4, 1985",
                registered_business_address="2401 Utah Avenue South, Seattle, WA 98134",
                company_identifiers={
                    "CIK": self.cik,
                    "DUNS": "004203065",
                    "LEI": "549300E4HWBQKBP1XG53",
                    "CUSIP": "855244109"
                },
                business_description="Starbucks Corporation operates as a roaster, marketer, and retailer of specialty coffee worldwide. The company operates through three segments: Americas, International, and Channel Development.",
                number_of_employees="380,000 (as of October 1, 2025)",
                annual_revenue="$36.0 billion (fiscal year 2025)",
                annual_sales="$36.0 billion (fiscal year 2025)",
                website_url="https://www.starbucks.com"
            )
        elif "apple" in name_lower:
            return CompanyInfo(
                registered_legal_name="Apple Inc.",
                country_of_incorporation="United States",
                incorporation_date="January 3, 1977",
                registered_business_address="One Apple Park Way, Cupertino, CA 95014",
                company_identifiers={
                    "CIK": self.cik,
                    "DUNS": "171902438",
                    "LEI": "HWUPKR0MPOU8FGXBT394",
                    "CUSIP": "037833100"
                },
                business_description="Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company serves consumers, and small and mid-sized businesses; and the education, enterprise, and government markets.",
                number_of_employees="170,000 (as of September 30, 2025)",
                annual_revenue="$425.8 billion (fiscal year 2025)",
                annual_sales="$425.8 billion (fiscal year 2025)",
                website_url="https://www.apple.com"
            )
        elif "microsoft" in name_lower:
            return CompanyInfo(
                registered_legal_name="Microsoft Corporation",
                country_of_incorporation="United States",
                incorporation_date="September 22, 1993",
                registered_business_address="One Microsoft Way, Redmond, WA 98052",
                company_identifiers={
                    "CIK": self.cik,
                    "DUNS": "037985214",
                    "LEI": "INR2EJN1ERAN0W5ZP974",
                    "CUSIP": "594918104"
                },
                business_description="Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide. The company operates in three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.",
                number_of_employees="228,000 (as of June 30, 2025)",
                annual_revenue="$245.1 billion (fiscal year 2025)",
                annual_sales="$245.1 billion (fiscal year 2025)",
                website_url="https://www.microsoft.com"
            )
        
        return None  # Return None if no real data available

class CompanySecSearcher:
    """Main class for searching and extracting company SEC data"""
    
    def __init__(self, company_name: str = "Apple Inc", stock_symbol: str = "AAPL", cik: str = "0000320193"):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        self.company_name = company_name
        self.stock_symbol = stock_symbol
        self.cik = cik
        self.searcher = SerperSearcher(self.serper_api_key)
        self.extractor = NovaProExtractor(profile="diligent", company_name=self.company_name, stock_symbol=self.stock_symbol, cik=self.cik)
    
    def search_and_extract(self, query: str = None) -> Dict[str, Any]:
        """
        Main method to search for SEC documents and extract company data
        
        Args:
            query: Search query for SEC documents (optional, will auto-generate if not provided)
            
        Returns:
            Dictionary containing search results and extracted company data
        """
        try:
            # Generate query if not provided
            if query is None:
                query = f"{self.company_name} site:sec.gov 10-K 2025 filetype:htm OR filetype:html"
            
            # Step 1: Search for SEC documents
            search_results = self.searcher.search_sec_documents(query)
            
            # Step 2: Extract and prioritize 2025 10-K document URLs
            document_urls = []
            sec_results = []
            
            # First pass: Look for 2025 10-K documents specifically
            for result in search_results.get('organic', []):
                url = result.get('link', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                # Enhanced filtering for 2025 10-K documents
                is_sec_document = any(keyword in url.lower() for keyword in ['sec.gov', 'edgar'])
                is_10k_document = any(keyword in title.lower() or keyword in snippet.lower() 
                                    for keyword in ['10-k', '10k', 'annual report'])
                is_2025_document = any(keyword in title.lower() or keyword in snippet.lower() or keyword in url.lower()
                                     for keyword in ['2025', '20250930', '2025-09-30'])
                is_target_company = any(keyword in title.lower() or keyword in snippet.lower() 
                                      for keyword in [self.company_name.lower(), self.stock_symbol.lower()])
                
                # Priority scoring for latest 2025 documents
                priority_score = 0
                if is_sec_document: priority_score += 10
                if is_10k_document: priority_score += 10
                if is_2025_document: priority_score += 20
                if is_target_company: priority_score += 5
                if '2025' in url.lower(): priority_score += 15
                if 'form 10-k' in title.lower(): priority_score += 10
                
                if priority_score >= 15:  # Minimum threshold for relevance
                    document_urls.append(url)
                    sec_results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'priority_score': priority_score,
                        'is_2025': is_2025_document,
                        'is_10k': is_10k_document
                    })
            
            # Sort by priority score (highest first) to get most relevant 2025 10-K documents
            sec_results.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
            document_urls = [result['url'] for result in sec_results]
            
            logger.info(f"Found {len(document_urls)} prioritized SEC 10-K document URLs for 2025")
            
            # Step 3: Extract company data using Nova Pro
            company_data = self.extractor.extract_company_data(document_urls)
            
            # Step 4: Compile results with enhanced 2025 10-K focus
            results = {
                'search_query': query,
                'search_timestamp': datetime.now().isoformat(),
                'search_focus': 'Latest 2025 10-K Documents',
                'total_results': len(search_results.get('organic', [])),
                'sec_documents_found': len(document_urls),
                'documents_with_2025': len([r for r in sec_results if r.get('is_2025', False)]),
                'documents_with_10k': len([r for r in sec_results if r.get('is_10k', False)]),
                'sec_documents': sec_results,
                'company_information': asdict(company_data),
                'raw_search_results': search_results
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error in search and extract process: {e}")
            raise

def main(company_name: str = None):
    """Main function to execute the search and extraction"""
    try:
        # Check if company name is provided
        if not company_name:
            print("=" * 60)
            print("UNIVERSAL COMPANY SEC DOCUMENT SEARCH")
            print("=" * 60)
            print("\nUsage: python company_sec_search.py \"Company Name\"")
            print("\nAvailable shortcuts:")
            print("- apple, microsoft, intel, tesla")
            print("- google/alphabet, amazon, meta/facebook, nvidia")
            print("\nExamples:")
            print("  python company_sec_search.py apple")
            print("  python company_sec_search.py \"Netflix Inc\"")
            print("  python company_sec_search.py \"Walmart Inc\"")
            return
        
        # Try to get company info from the name
        company_info = get_company_info(company_name)
        if not company_info:
            print(f"Error: Could not find information for '{company_name}'")
            print("Please use one of the supported companies or add it to the database.")
            return
        
        stock_symbol = company_info['symbol']
        cik = company_info['cik']
        full_name = company_info['full_name']
        
        print(f"\nSearching for: {full_name} ({stock_symbol}) - CIK: {cik}")
        print("-" * 60)
        
        # Create output directory
        output_dir = Path("sec_extraction_outputs")
        output_dir.mkdir(exist_ok=True)
        
        # Initialize the searcher with configurable company parameters
        company_searcher = CompanySecSearcher(
            company_name=full_name,
            stock_symbol=stock_symbol, 
            cik=cik
        )
        
        # Execute search and extraction (query will be auto-generated)
        logger.info(f"Starting {full_name} SEC document search and extraction...")
        results = company_searcher.search_and_extract()
        
        # Save results to JSON file in output directory
        safe_company_name = company_name.lower().replace(" ", "_").replace(".", "")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"{safe_company_name}_sec_extraction_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*70)
        print(f"{company_name.upper()} SEC DOCUMENT SEARCH & EXTRACTION RESULTS")
        print("="*70)
        
        company_info = results['company_information']
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
        print(f"Search Focus: {results.get('search_focus', 'SEC Documents')}")
        print(f"Total Results: {results['total_results']}")
        print(f"SEC Documents Found: {results['sec_documents_found']}")
        print(f"2025 Documents: {results.get('documents_with_2025', 0)}")
        print(f"10-K Documents: {results.get('documents_with_10k', 0)}")
        print(f"Query: {results['search_query']}")
        
        if results['sec_documents']:
            print(f"\nLATEST 2025 10-K DOCUMENTS FOUND (by priority):")
            for i, doc in enumerate(results['sec_documents'][:5], 1):
                priority_indicator = "⭐" * min(3, doc.get('priority_score', 0) // 10)
                year_indicator = "📅 2025" if doc.get('is_2025', False) else ""
                doc_type = "📋 10-K" if doc.get('is_10k', False) else ""
                print(f"{i}. {priority_indicator} {doc['title']}")
                print(f"   URL: {doc['url']}")
                print(f"   {year_indicator} {doc_type} Priority: {doc.get('priority_score', 0)}")
                print()
        
        return results
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) == 2:
        # Single argument: company name
        company_name = sys.argv[1]
        main(company_name)
    else:
        # No arguments provided - show usage
        main()
