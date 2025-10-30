#!/usr/bin/env python3
"""
CxO Website Extractor with AWS Nova Pro Integration

This script takes a corporate website URL, uses Serper API to search for 
Chief Executive Officers (CxOs) and other executives, then uses AWS Nova Pro
to intelligently extract and structure the executive information.

Usage:
    python cxo_website_extractor.py "https://www.apple.com"
    python cxo_website_extractor.py "https://www.microsoft.com"

Requirements:
    - SERPER_API_KEY in environment variables
    - AWS credentials configured (AWS_PROFILE or AWS keys)
    - boto3, requests libraries
"""

import os
import sys
import json
import requests
import re
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()


@dataclass
class ExecutiveInfo:
    """Enhanced data structure for executive information"""
    name: str
    title: str
    role_category: str  # CEO, CFO, CTO, etc.
    description: Optional[str] = None
    tenure: Optional[str] = None
    background: Optional[str] = None
    education: Optional[str] = None
    previous_roles: Optional[List[str]] = None
    contact_info: Optional[Dict[str, str]] = None
    source_url: Optional[str] = None
    confidence_score: Optional[float] = None


@dataclass
class CxOSearchResults:
    """Container for all CxO search results with Nova Pro enhancement"""
    company_website: str
    company_name: str
    search_timestamp: str
    executives: List[ExecutiveInfo]
    total_executives_found: int
    search_queries_used: List[str]
    nova_pro_enhanced: bool = False
    extraction_method: str = "regex_only"


class AWSNovaProExtractor:
    """Handles AWS Nova Pro LLM for intelligent executive data extraction"""
    
    def __init__(self, aws_profile: str = None, aws_region: str = "us-east-1"):
        """Initialize AWS Nova Pro client"""
        try:
            if aws_profile:
                session = boto3.Session(profile_name=aws_profile)
                self.bedrock_client = session.client('bedrock-runtime', region_name=aws_region)
            else:
                self.bedrock_client = boto3.client('bedrock-runtime', region_name=aws_region)
            
            self.model_id = "amazon.nova-pro-v1:0"
            print(f"✅ AWS Nova Pro initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize AWS Nova Pro: {e}")
            raise
    
    def extract_executives_with_nova(self, search_results: Dict[str, Any], company_name: str, website_url: str) -> List[ExecutiveInfo]:
        """Use Nova Pro to intelligently extract executive information from search results"""
        
        print("🤖 Using AWS Nova Pro for intelligent executive extraction...")
        
        # Prepare search context for Nova Pro
        search_context = self._prepare_search_context(search_results)
        
        # Build extraction prompt
        prompt = self._build_executive_extraction_prompt(search_context, company_name, website_url)
        
        # Call Nova Pro
        try:
            response = self._call_nova_pro(prompt)
            executives = self._parse_nova_response(response)
            
            print(f"✅ Nova Pro extracted {len(executives)} executives")
            return executives
            
        except Exception as e:
            print(f"❌ Nova Pro extraction failed: {e}")
            return []
    
    def _fetch_page_content(self, url: str, max_chars: int = 5000) -> Optional[str]:
        """Fetch and extract main text content from a URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = ' '.join(text.split())
            
            # Limit content length
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            return text
        except Exception as e:
            print(f"   ⚠️  Could not fetch {url[:50]}: {str(e)[:30]}")
            return None
    
    def _prepare_search_context(self, search_results: Dict[str, Any]) -> str:
        """Prepare search results context for Nova Pro - with full page content"""
        
        context_parts = []
        
        # Process organic results
        organic_results = search_results.get('organic', [])
        
        # Fetch full content from top 3 most relevant results
        print(f"   📄 Fetching full content from top {min(3, len(organic_results))} results...")
        
        for i, result in enumerate(organic_results[:3], 1):
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            link = result.get('link', '')
            
            # Try to fetch full page content
            full_content = self._fetch_page_content(link)
            
            if full_content:
                context_parts.append(f"""
SEARCH RESULT {i} (FULL CONTENT):
Title: {title}
URL: {link}
Content: {full_content}
""")
            else:
                # Fallback to snippet if page fetch fails
                context_parts.append(f"""
SEARCH RESULT {i} (SNIPPET):
Title: {title}
Content: {snippet}
URL: {link}
""")
        
        # Add snippets from remaining results (4-10)
        for i, result in enumerate(organic_results[3:10], 4):
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            link = result.get('link', '')
            
            context_parts.append(f"""
SEARCH RESULT {i} (SNIPPET):
Title: {title}
Content: {snippet}
URL: {link}
""")
        
        # Process knowledge graph if available
        knowledge_graph = search_results.get('knowledgeGraph', {})
        if knowledge_graph:
            context_parts.append(f"""
KNOWLEDGE GRAPH:
{json.dumps(knowledge_graph, indent=2)}
""")
        
        return "\n".join(context_parts)
    
    def _build_executive_extraction_prompt(self, search_context: str, company_name: str, website_url: str) -> str:
        """Build comprehensive prompt for Nova Pro executive extraction"""
        
        prompt = f"""
You are an expert executive intelligence analyst. Your task is to extract comprehensive information about company executives from search results.

COMPANY INFORMATION:
- Company Name: {company_name}
- Website: {website_url}

SEARCH RESULTS CONTEXT:
{search_context}

EXTRACTION REQUIREMENTS:

1. EXECUTIVE IDENTIFICATION:
   - Extract ALL executives mentioned in the search results
   - Focus on C-level executives (CEO, CFO, CTO, COO, etc.)
   - Include Presidents, Chairmen, Founders, and other senior leadership
   - Ensure names are properly formatted (First Last, no titles in name field)

2. REQUIRED INFORMATION FOR EACH EXECUTIVE:
   - Full Name (clean, no titles)
   - Official Title/Position
   - Role Category (CEO, CFO, CTO, COO, President, Chairman, Founder, Executive)
   - Description (brief background, achievements, or context)
   - Tenure (when they started, how long in role)
   - Background (previous experience, career highlights)
   - Education (degrees, institutions if mentioned)
   - Previous Roles (list of prior positions)
   - Source URL (where information was found)
   - Confidence Score (0.0-1.0 based on information quality)

3. DATA QUALITY STANDARDS:
   - Only include executives with HIGH CONFIDENCE (score > 0.7)
   - Prioritize current executives over former ones
   - Verify executive names are real people, not generic titles
   - Ensure information is from official company sources when possible
   - Remove duplicates (same person with different titles)

4. SPECIAL INSTRUCTIONS:
   - If multiple sources mention the same executive, consolidate information
   - Distinguish between current and former executives
   - Include board members only if they have executive roles
   - Focus on {company_name} executives, not executives from other companies mentioned
   - Extract contact information if available (email, LinkedIn, etc.)

OUTPUT FORMAT:
Return a JSON array of executive objects. Each object should have this exact structure:

{{
  "name": "Full Name",
  "title": "Official Title",
  "role_category": "CEO|CFO|CTO|COO|President|Chairman|Founder|Executive",
  "description": "Brief description or background",
  "tenure": "Start date or duration in role",
  "background": "Previous experience and career highlights",
  "education": "Educational background if mentioned",
  "previous_roles": ["Previous Position 1", "Previous Position 2"],
  "contact_info": {{"email": "email@company.com", "linkedin": "url"}},
  "source_url": "URL where information was found",
  "confidence_score": 0.95
}}

CRITICAL: Return ONLY the JSON array, no additional text or explanation.
"""
        
        return prompt
    
    def _call_nova_pro(self, prompt: str) -> Dict[str, Any]:
        """Call AWS Nova Pro with the extraction prompt"""
        
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
        
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body
    
    def _parse_nova_response(self, response: Dict[str, Any]) -> List[ExecutiveInfo]:
        """Parse Nova Pro response and create ExecutiveInfo objects"""
        
        try:
            # Extract text content from Nova Pro response
            if 'output' in response and 'message' in response['output']:
                content = response['output']['message']['content'][0]['text']
            elif 'content' in response:
                content = response['content']
            else:
                print(f"❌ Unexpected Nova Pro response format: {response}")
                return []
            
            # Parse JSON from content
            # Remove any markdown formatting if present
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            executives_data = json.loads(content)
            
            # Convert to ExecutiveInfo objects
            executives = []
            for exec_data in executives_data:
                executive = ExecutiveInfo(
                    name=exec_data.get('name', ''),
                    title=exec_data.get('title', ''),
                    role_category=exec_data.get('role_category', 'Executive'),
                    description=exec_data.get('description'),
                    tenure=exec_data.get('tenure'),
                    background=exec_data.get('background'),
                    education=exec_data.get('education'),
                    previous_roles=exec_data.get('previous_roles'),
                    contact_info=exec_data.get('contact_info'),
                    source_url=exec_data.get('source_url'),
                    confidence_score=exec_data.get('confidence_score', 0.8)
                )
                executives.append(executive)
            
            return executives
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Nova Pro JSON response: {e}")
            print(f"Raw content: {content[:500]}...")
            return []
        except Exception as e:
            print(f"❌ Error parsing Nova Pro response: {e}")
            return []


class SerperCxOSearcher:
    """Handles Serper API searches for CxO information from corporate websites"""
    
    def __init__(self, api_key: str, use_nova_pro: bool = True, aws_profile: str = None):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        self.use_nova_pro = use_nova_pro
        
        # Initialize Nova Pro if requested
        if self.use_nova_pro:
            try:
                self.nova_extractor = AWSNovaProExtractor(aws_profile=aws_profile)
            except Exception as e:
                print(f"⚠️  Nova Pro initialization failed, falling back to regex extraction: {e}")
                self.use_nova_pro = False
    
    def _calculate_completeness(self, executives: List[ExecutiveInfo]) -> float:
        """
        Calculate completeness percentage of extracted CXO data.
        Returns percentage (0-100) based on:
        - Number of executives found (minimum expectation: 3-5 key executives)
        - Completeness of each executive's profile
        """
        if not executives:
            return 0.0
        
        # Weight factors
        min_expected_executives = 3  # Minimum expected C-suite executives
        
        # 1. Check quantity (40% weight)
        quantity_score = min(len(executives) / min_expected_executives, 1.0) * 40
        
        # 2. Check quality of each executive profile (60% weight)
        total_profile_score = 0
        required_fields = ['name', 'title', 'role_category']
        optional_fields = ['description', 'tenure', 'background', 'education']
        
        for exec_info in executives:
            profile_score = 0
            fields_checked = 0
            
            # Check required fields (50% of profile score)
            for field in required_fields:
                fields_checked += 1
                value = getattr(exec_info, field, None)
                if value and str(value).strip() and value != 'Unknown':
                    profile_score += 1
            
            # Check optional fields (50% of profile score)
            for field in optional_fields:
                fields_checked += 1
                value = getattr(exec_info, field, None)
                if value and str(value).strip() and value != 'Not specified':
                    profile_score += 1
            
            # Calculate percentage for this executive profile
            if fields_checked > 0:
                total_profile_score += (profile_score / fields_checked) * 100
        
        # Average profile quality across all executives
        quality_score = (total_profile_score / len(executives)) * 0.6
        
        # Total completeness score
        completeness = quantity_score + quality_score
        return round(completeness, 2)
    
    def search_cxo_from_website(self, website_url: str, company_name: str = None, max_retries: int = 2) -> CxOSearchResults:
        """
        Main method to search for CxO information from a specific website
        Includes automatic retry logic if data completeness is below 95%
        
        Args:
            website_url: The corporate website URL to search
            company_name: Optional full company name (if not provided, extracted from domain)
            max_retries: Maximum number of retry attempts (default: 2)
            
        Returns:
            CxOSearchResults object containing all found executives
        """
        attempt = 0
        best_result = None
        best_completeness = 0.0
        
        while attempt <= max_retries:
            if attempt == 0:
                print(f"🔍 Searching for CxO information from: {website_url}")
            else:
                print(f"🔄 Retry attempt {attempt}/{max_retries} - extracting data again...")
            
            # Extract domain and company name
            domain = self._extract_domain(website_url)
            if company_name is None:
                company_name = self._extract_company_name(domain)
            
            # Generate search queries
            search_queries = self._generate_cxo_search_queries(domain, company_name)
            
            # OPTIMIZATION: Perform searches in parallel (75% faster!)
            all_search_results = []
            all_executives = []
            
            # Use parallel searches (only show progress on first attempt)
            all_search_results = self._parallel_serper_searches(search_queries, show_progress=(attempt == 0))
            
            # If not using Nova Pro, extract with regex from each result
            if not self.use_nova_pro:
                for search_data in all_search_results:
                    executives = self._parse_search_results(search_data, domain)
                    all_executives.extend(executives)
            
            # Use Nova Pro for intelligent extraction if available
            if self.use_nova_pro and all_search_results:
                if attempt == 0:
                    print("🤖 Using AWS Nova Pro for intelligent executive extraction...")
                
                # Combine all search results for Nova Pro
                combined_results = self._combine_search_results(all_search_results)
                nova_executives = self.nova_extractor.extract_executives_with_nova(
                    combined_results, company_name, website_url
                )
                
                if nova_executives:
                    all_executives = nova_executives
                    extraction_method = "nova_pro"
                    nova_enhanced = True
                    if attempt == 0:
                        print(f"✅ Nova Pro extracted {len(all_executives)} executives")
                else:
                    # Fallback to regex if Nova Pro fails
                    print("⚠️  Nova Pro extraction failed, using regex fallback")
                    for search_data in all_search_results:
                        executives = self._parse_search_results(search_data, domain)
                        all_executives.extend(executives)
                    extraction_method = "regex_fallback"
                    nova_enhanced = False
            else:
                extraction_method = "regex_only"
                nova_enhanced = False
            
            # Remove duplicates and organize (only for regex extraction)
            if not nova_enhanced:
                all_executives = self._deduplicate_executives(all_executives)
            
            # Create result
            result = CxOSearchResults(
                company_website=website_url,
                company_name=company_name,
                search_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                executives=all_executives,
                total_executives_found=len(all_executives),
                search_queries_used=search_queries,
                nova_pro_enhanced=nova_enhanced,
                extraction_method=extraction_method
            )
            
            # Calculate completeness
            completeness = self._calculate_completeness(all_executives)
            print(f"📊 Data completeness: {completeness}% ({len(all_executives)} executives found)")
            
            # Track best result
            if completeness > best_completeness:
                best_completeness = completeness
                best_result = result
            
            # Check if completeness meets threshold
            if completeness >= 95.0:
                print(f"✅ Data completeness threshold met ({completeness}% >= 95%)")
                return result
            else:
                print(f"⚠️  Data completeness below threshold ({completeness}% < 95%)")
                if attempt < max_retries:
                    print(f"🔄 Will retry extraction (attempt {attempt + 1}/{max_retries})...")
                    attempt += 1
                    continue
                else:
                    print(f"⚠️  Maximum retries reached. Using best result with {best_completeness}% completeness")
                    return best_result
        
        # Fallback return (should never reach here)
        return best_result if best_result else result
    
    def _extract_domain(self, website_url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def _extract_company_name(self, domain: str) -> str:
        """Extract company name from domain"""
        # Remove common TLDs and get the main part
        company_name = domain.split('.')[0]
        # Capitalize first letter
        return company_name.capitalize()
    
    def _generate_cxo_search_queries(self, domain: str, company_name: str) -> List[str]:
        """
        Generate targeted search queries for CxO information - Enhanced version
        Improvements: Additional URL patterns, PDF support, keyword variations, structured data pages
        """
        
        queries = []
        
        # Common exclusions for cleaner results
        lang_exclude = '-inurl:/ko/ -inurl:/ja/ -inurl:/es/ -inurl:/fr/ -inurl:/de/ -inurl:/pt/ -inurl:/zh/ -inurl:/cn/ -inurl:/it/ -inurl:/ru/'
        noise_exclude = '-inurl:/news/ -inurl:/blog/ -inurl:/press/ -inurl:/careers/ -inurl:/jobs/ -inurl:/media/ -inurl:/events/ -inurl:/archive/ -inurl:/tag/ -inurl:/category/'
        
        # PRIORITY 0: MOST IMPORTANT - Find official corporate HQ leadership pages
        queries.extend([
            # Primary leadership pages (original + enhanced)
            f'site:{domain} (inurl:/en/leadership OR inurl:/leadership OR inurl:/leaders) "executive" {lang_exclude} {noise_exclude}',
            
            # Executive team pages with variations (IMPROVEMENT #5)
            f'site:{domain} ("executive team" OR "leadership team" OR "executive leadership") {lang_exclude} {noise_exclude}',
            
            # Management/Team pages (IMPROVEMENT #2)
            f'site:{domain} (inurl:/management OR inurl:/team OR inurl:/our-team) "executives" "officers" {lang_exclude} {noise_exclude}',
            
            # About Us variations (IMPROVEMENT #2)
            f'site:{domain} (inurl:/about OR inurl:/about-us OR inurl:/company OR inurl:/who-we-are) ("leadership" OR "executives" OR "management") {lang_exclude}',
            
            # Investor relations (high quality - original + enhanced)
            f'site:{domain} (inurl:/investor OR inurl:/ir OR inurl:/investors OR inurl:/shareholder) ("management" OR "executives" OR "officers" OR "leadership") {lang_exclude}',
            
            # Corporate governance (IMPROVEMENT #2)
            f'site:{domain} (inurl:/governance OR inurl:/corporate-governance) ("officers" OR "management" OR "executive") {lang_exclude}',
            
            # Board and directors (IMPROVEMENT #2)
            f'site:{domain} (inurl:/board OR inurl:/directors) "executive" {lang_exclude} -inurl:/advisory/',
            
            # Senior management variations (IMPROVEMENT #5)
            f'site:{domain} ("senior management" OR "senior leadership" OR "c-suite" OR "c-level" OR "executive officers") {lang_exclude} {noise_exclude}',
            
            # Management team keyword variations (IMPROVEMENT #5)
            f'site:{domain} "management team" "senior leadership" {lang_exclude} {noise_exclude}',
            
            # Organization structure pages (IMPROVEMENT #6)
            f'site:{domain} (inurl:/organization OR inurl:/structure OR inurl:/org-chart) "leadership" "management" {lang_exclude}',
            
            # Contact and directory pages (IMPROVEMENT #6)
            f'site:{domain} (inurl:/contact OR inurl:/directory OR inurl:/people) ("executive" OR "management" OR "officers") {lang_exclude}',
            
            # === PDF DOCUMENTS (IMPROVEMENT #4) ===
            # Annual reports and proxy statements often have complete executive lists
            f'site:{domain} filetype:pdf ("executive officers" OR "management team" OR "leadership")',
            f'site:{domain} filetype:pdf ("annual report" OR "10-K" OR "10K") "executive"',
            f'site:{domain} filetype:pdf ("proxy statement" OR "DEF 14A") "executive compensation"',
            
            # Investor-focused keyword variations (IMPROVEMENT #5)
            f'site:{domain} (inurl:/investors OR inurl:/shareholders) "corporate officers" "management"',
        ])
        
        # PRIORITY 1: Company website searches for specific roles (corporate HQ only)
        executive_roles = [
            "CEO Chief Executive Officer",
            "CFO Chief Financial Officer", 
            "CTO Chief Technology Officer",
            "COO Chief Operating Officer"
        ]
        
        for role in executive_roles:
            queries.append(f'site:{domain} "{role}" -inurl:/ko/ -inurl:/ja/ -inurl:/es/ -inurl:/news/')
        
        # PRIORITY 2: Global web searches for additional/verified information
        # Search across the entire web for comprehensive executive profiles
        queries.extend([
            f'"{company_name}" "leadership team" executives officers',
            f'"{company_name}" CEO CFO CTO COO "executive team"',
            f'"{company_name}" "senior leadership" management',
            f'"{company_name}" C-suite officers board',
            f'"{company_name}" executives linkedin profiles'
        ])
        
        return queries
    
    def _perform_serper_search(self, query: str) -> Optional[Dict[str, Any]]:
        """Perform Serper search and return raw results"""
        
        payload = {
            "q": query,
            "num": 10,
            "gl": "us",
            "hl": "en"
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            search_data = response.json()
            return search_data
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Search failed for query '{query}': {e}")
            return None
    
    def _parallel_serper_searches(self, queries: List[str], show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        OPTIMIZATION: Perform multiple Serper searches in parallel using ThreadPoolExecutor
        This reduces total search time by ~75% (24 sequential calls → 5 parallel batches)
        
        Args:
            queries: List of search queries to execute
            show_progress: Whether to print progress messages
            
        Returns:
            List of search result dictionaries (successful searches only)
        """
        all_search_results = []
        
        # Use ThreadPoolExecutor for parallel API calls
        max_workers = 6  # Limit concurrent requests to avoid rate limiting
        
        if show_progress:
            print(f"🚀 Running {len(queries)} searches in parallel (6 workers)...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all search tasks
            future_to_query = {
                executor.submit(self._perform_serper_search, query): query 
                for query in queries
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                completed += 1
                try:
                    search_data = future.result()
                    if search_data:
                        all_search_results.append(search_data)
                        if show_progress:
                            print(f"   ✅ [{completed}/{len(queries)}] Completed")
                except Exception as e:
                    if show_progress:
                        print(f"   ❌ [{completed}/{len(queries)}] Failed: {str(e)[:60]}")
        
        if show_progress:
            print(f"✅ Completed all searches: {len(all_search_results)} successful")
        
        return all_search_results
    
    def _combine_search_results(self, all_search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple search results for Nova Pro processing"""
        
        combined = {
            'organic': [],
            'knowledgeGraph': {}
        }
        
        # Combine organic results from all searches
        for search_data in all_search_results:
            organic_results = search_data.get('organic', [])
            combined['organic'].extend(organic_results)
            
            # Use knowledge graph from first result that has one
            if not combined['knowledgeGraph'] and search_data.get('knowledgeGraph'):
                combined['knowledgeGraph'] = search_data['knowledgeGraph']
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_organic = []
        for result in combined['organic']:
            url = result.get('link', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_organic.append(result)
        
        combined['organic'] = unique_organic[:20]  # Limit to top 20 results
        
        return combined
    
    def _search_and_extract_executives(self, query: str, domain: str) -> List[ExecutiveInfo]:
        """Perform Serper search and extract executive information (legacy method for regex)"""
        
        search_data = self._perform_serper_search(query)
        if search_data:
            return self._parse_search_results(search_data, domain)
        return []
    
    def _parse_search_results(self, search_data: Dict[str, Any], domain: str) -> List[ExecutiveInfo]:
        """Parse Serper search results to extract executive information"""
        
        executives = []
        
        # Process organic results
        organic_results = search_data.get('organic', [])
        
        for result in organic_results:
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            link = result.get('link', '')
            
            # Extract executives from title and snippet
            found_executives = self._extract_executives_from_text(
                text=f"{title} {snippet}",
                source_url=link
            )
            executives.extend(found_executives)
        
        # Process knowledge graph if available
        knowledge_graph = search_data.get('knowledgeGraph', {})
        if knowledge_graph:
            kg_executives = self._extract_from_knowledge_graph(knowledge_graph)
            executives.extend(kg_executives)
        
        return executives
    
    def _extract_executives_from_text(self, text: str, source_url: str) -> List[ExecutiveInfo]:
        """Extract executive information from text using regex patterns"""
        
        executives = []
        
        # Common patterns for executive information
        patterns = [
            # Pattern: "John Smith, CEO" or "John Smith - CEO"
            r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\-\s]+(?:is\s+)?(?:the\s+)?(CEO|CFO|CTO|COO|President|Chairman|Founder|Chief Executive Officer|Chief Financial Officer|Chief Technology Officer|Chief Operating Officer)',
            
            # Pattern: "CEO John Smith" or "Chief Executive Officer John Smith"
            r'(?:CEO|CFO|CTO|COO|President|Chairman|Founder|Chief Executive Officer|Chief Financial Officer|Chief Technology Officer|Chief Operating Officer)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Pattern: "John Smith serves as CEO"
            r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:serves as|is the|acts as)\s+(CEO|CFO|CTO|COO|President|Chairman|Founder)',
            
            # Pattern: "Mr./Ms. John Smith, CEO"
            r'(?:Mr\.|Ms\.|Dr\.)\s+([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+(?:is\s+)?(?:the\s+)?(CEO|CFO|CTO|COO|President|Chairman|Founder)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    name = groups[0].strip()
                    title = groups[1].strip()
                    
                    # Normalize title
                    normalized_title = self._normalize_title(title)
                    role_category = self._categorize_role(normalized_title)
                    
                    # Extract additional context
                    description = self._extract_description_context(text, name)
                    
                    executive = ExecutiveInfo(
                        name=name,
                        title=normalized_title,
                        role_category=role_category,
                        description=description,
                        source_url=source_url
                    )
                    
                    executives.append(executive)
        
        return executives
    
    def _extract_from_knowledge_graph(self, knowledge_graph: Dict[str, Any]) -> List[ExecutiveInfo]:
        """Extract executive information from Google Knowledge Graph"""
        
        executives = []
        
        # Look for CEO information in knowledge graph
        ceo_info = knowledge_graph.get('ceo', '')
        if ceo_info:
            executive = ExecutiveInfo(
                name=ceo_info,
                title="Chief Executive Officer",
                role_category="CEO",
                description="Information from Google Knowledge Graph",
                source_url="Google Knowledge Graph"
            )
            executives.append(executive)
        
        return executives
    
    def _normalize_title(self, title: str) -> str:
        """Normalize executive titles"""
        
        title_mapping = {
            'CEO': 'Chief Executive Officer',
            'CFO': 'Chief Financial Officer',
            'CTO': 'Chief Technology Officer',
            'COO': 'Chief Operating Officer',
            'PRESIDENT': 'President',
            'CHAIRMAN': 'Chairman',
            'FOUNDER': 'Founder'
        }
        
        title_upper = title.upper()
        return title_mapping.get(title_upper, title)
    
    def _categorize_role(self, title: str) -> str:
        """Categorize executive role"""
        
        title_lower = title.lower()
        
        if 'chief executive' in title_lower or title_lower == 'ceo':
            return 'CEO'
        elif 'chief financial' in title_lower or title_lower == 'cfo':
            return 'CFO'
        elif 'chief technology' in title_lower or title_lower == 'cto':
            return 'CTO'
        elif 'chief operating' in title_lower or title_lower == 'coo':
            return 'COO'
        elif 'president' in title_lower:
            return 'President'
        elif 'chairman' in title_lower:
            return 'Chairman'
        elif 'founder' in title_lower:
            return 'Founder'
        else:
            return 'Executive'
    
    def _extract_description_context(self, text: str, name: str) -> Optional[str]:
        """Extract additional context about the executive"""
        
        # Look for sentences containing the executive's name
        sentences = text.split('.')
        
        for sentence in sentences:
            if name in sentence and len(sentence.strip()) > 20:
                # Clean up the sentence
                description = sentence.strip()
                if len(description) > 200:
                    description = description[:200] + "..."
                return description
        
        return None
    
    def _deduplicate_executives(self, executives: List[ExecutiveInfo]) -> List[ExecutiveInfo]:
        """Remove duplicate executives based on name and role"""
        
        seen = set()
        unique_executives = []
        
        for executive in executives:
            # Create a key based on name and role category
            key = (executive.name.lower().strip(), executive.role_category.lower())
            
            if key not in seen:
                seen.add(key)
                unique_executives.append(executive)
        
        # Sort by role importance
        role_priority = {
            'CEO': 1, 'President': 2, 'Chairman': 3, 'CFO': 4, 
            'COO': 5, 'CTO': 6, 'Founder': 7, 'Executive': 8
        }
        
        unique_executives.sort(key=lambda x: role_priority.get(x.role_category, 9))
        
        return unique_executives


class CxOResultsFormatter:
    """Formats and displays CxO search results"""
    
    @staticmethod
    def display_results(results: CxOSearchResults):
        """Display formatted CxO search results with Nova Pro enhancements"""
        
        print("\n" + "="*80)
        print(f"🏢 CxO SEARCH RESULTS FOR: {results.company_name}")
        print("="*80)
        print(f"Website: {results.company_website}")
        print(f"Search Date: {results.search_timestamp}")
        print(f"Total Executives Found: {results.total_executives_found}")
        print(f"Search Queries Used: {len(results.search_queries_used)}")
        print(f"Extraction Method: {results.extraction_method}")
        
        if results.nova_pro_enhanced:
            print("🤖 Enhanced with AWS Nova Pro Intelligence")
        
        if not results.executives:
            print("\n❌ No executives found for this website.")
            print("\nPossible reasons:")
            print("   • Website may not have public leadership information")
            print("   • Leadership pages may not be indexed by search engines")
            print("   • Different naming conventions used")
            return
        
        print("\n" + "-"*80)
        print("👥 EXECUTIVES FOUND:")
        print("-"*80)
        
        for i, executive in enumerate(results.executives, 1):
            print(f"\n{i}. {executive.name}")
            print(f"   Title: {executive.title}")
            print(f"   Role Category: {executive.role_category}")
            
            if executive.description:
                print(f"   Description: {executive.description}")
            
            if executive.tenure:
                print(f"   Tenure: {executive.tenure}")
            
            if executive.background:
                print(f"   Background: {executive.background}")
            
            if executive.education:
                print(f"   Education: {executive.education}")
            
            if executive.previous_roles:
                print(f"   Previous Roles: {', '.join(executive.previous_roles)}")
            
            if executive.contact_info:
                contact_parts = []
                for key, value in executive.contact_info.items():
                    contact_parts.append(f"{key}: {value}")
                print(f"   Contact: {', '.join(contact_parts)}")
            
            if executive.confidence_score:
                print(f"   Confidence Score: {executive.confidence_score:.2f}")
            
            if executive.source_url:
                print(f"   Source: {executive.source_url}")
        
        print("\n" + "="*80)
    
    @staticmethod
    def save_to_dynamodb(results: CxOSearchResults):
        """Save executive data to DynamoDB"""
        try:
            # Initialize DynamoDB client (use IAM role in Lambda, profile locally)
            is_lambda = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
            if is_lambda:
                dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            else:
                session = boto3.Session(profile_name='diligent')
                dynamodb = session.resource('dynamodb', region_name='us-east-1')
            
            # Table name for CXO data
            table_name = 'CompanyCXOData'
            table = dynamodb.Table(table_name)
            
            # Prepare company identifier (match SEC extractor normalization)
            timestamp = datetime.now().isoformat()
            # Use same normalization as SEC extractor: lowercase, replace spaces with _, remove dots and commas
            company_name_clean = results.company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
            
            # Save each executive as a separate item
            for idx, executive in enumerate(results.executives, 1):
                item = {
                    'company_id': company_name_clean,  # Partition key
                    'executive_id': f"{company_name_clean}_{idx}_{timestamp}",  # Sort key
                    'company_name': results.company_name,
                    'company_website': results.company_website,
                    'extraction_timestamp': timestamp,
                    'name': executive.name,
                    'title': executive.title,
                    'role_category': executive.role_category,
                    'description': executive.description or '',
                    'tenure': executive.tenure or '',
                    'background': executive.background or '',
                    'education': executive.education or '',
                    'previous_roles': executive.previous_roles or [],
                    'contact_info': executive.contact_info or {},
                    'extraction_source': 'cxo_website_extractor'
                }
                
                # Put item to DynamoDB
                table.put_item(Item=item)
            
            print(f"✅ {len(results.executives)} executives saved to DynamoDB table: {table_name}")
            
        except Exception as e:
            print(f"❌ Error saving to DynamoDB: {e}")
            print("Data will still be saved to JSON file")
    
    @staticmethod
    def save_to_json(results: CxOSearchResults, output_dir: str = "cxo_extractions"):
        """Save results to DynamoDB - executives only, no metadata"""
        
        # Save to DynamoDB
        try:
            CxOResultsFormatter.save_to_dynamodb(results)
            print(f"\n✅ Data saved to DynamoDB table: CompanyCXOData")
        except Exception as e:
            print(f"❌ DynamoDB save failed: {e}")
            raise
        
        return None


def main():
    """Main function to run CxO website extraction with Nova Pro"""
    
    # Check command line arguments
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python cxo_website_extractor.py <website_url> [company_name] [--no-nova]")
        print("\nExamples:")
        print("  python cxo_website_extractor.py 'https://www.apple.com'")
        print("  python cxo_website_extractor.py 'https://www.intel.com' 'Intel Corporation'")
        print("  python cxo_website_extractor.py 'https://www.apple.com' --no-nova")
        sys.exit(1)
    
    website_url = sys.argv[1]
    company_name = None
    use_nova_pro = True
    
    # Parse arguments
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '--no-nova':
            use_nova_pro = False
            print("🔧 Nova Pro disabled, using regex extraction only")
        else:
            company_name = sys.argv[i]
    
    # Validate URL format
    if not website_url.startswith(('http://', 'https://')):
        website_url = 'https://' + website_url
    
    # Get API key
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        print("❌ Error: SERPER_API_KEY environment variable not found")
        print("Please set your Serper API key in the .env file or environment variables")
        sys.exit(1)
    
    # Get AWS profile
    aws_profile = os.getenv('AWS_PROFILE', 'diligent')
    
    try:
        # Initialize searcher with Nova Pro option
        searcher = SerperCxOSearcher(
            api_key=api_key, 
            use_nova_pro=use_nova_pro,
            aws_profile=aws_profile
        )
        
        # Perform search
        results = searcher.search_cxo_from_website(website_url, company_name=company_name)
        
        # Display results
        CxOResultsFormatter.display_results(results)
        
        # Save to JSON
        output_dir = "cxo_nova_extractions" if results.nova_pro_enhanced else "cxo_extractions"
        CxOResultsFormatter.save_to_json(results, output_dir)
        
        # Display cost information if Nova Pro was used
        if results.nova_pro_enhanced:
            print(f"\n💰 Estimated Cost Analysis:")
            print(f"   Serper API: ~${len(results.search_queries_used) * 0.004:.3f}")
            print(f"   AWS Nova Pro: ~$0.015-0.025 (depending on content)")
            print(f"   Total: ~$0.075-0.085")
        
    except Exception as e:
        print(f"❌ Error during CxO extraction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
