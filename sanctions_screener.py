"""
Sanctions & Watchlist Screening Module

This module screens companies and their executives against global sanctions and watchlists including:
- OFAC SDN (Office of Foreign Assets Control - Specially Designated Nationals)
- UN Sanctions
- EU Sanctions
- UK HMT (Her Majesty's Treasury)
- Regulatory watchlists (FinCEN, Interpol)
- Politically Exposed Persons (PEPs)

Input: Company name and list of executives from DynamoDB
Output: Sanctions matches with confidence levels, justifications, and source URLs
"""

import os
import sys
import json
import time
import logging
import requests
import argparse
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SanctionsMatch:
    """Represents a potential sanctions/watchlist match"""
    entity_name: str  # Company or individual name
    entity_type: str  # "company" or "individual"
    match_type: str  # "OFAC SDN", "UN Sanctions", "EU Sanctions", "UK HMT", "PEP", "Interpol", etc.
    confidence_level: str  # "High", "Medium", "Low"
    confidence_justification: str  # 50-100 words explaining the confidence level
    match_reason: str  # Why this is a match (e.g., "Exact name match on OFAC SDN List")
    source: str  # Source name (e.g., "OFAC SDN List", "UN Sanctions Committee")
    source_url: str  # Mandatory URL to the source
    match_details: Dict[str, Any] = field(default_factory=dict)  # Additional details
    screened_date: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SanctionsScreeningResult:
    """Complete sanctions screening result"""
    company_id: str
    company_name: str
    screening_timestamp: str
    total_entities_screened: int
    total_matches_found: int
    company_matches: List[SanctionsMatch] = field(default_factory=list)
    executive_matches: List[SanctionsMatch] = field(default_factory=list)


class SerperSanctionsSearcher:
    """Searches for sanctions and watchlist matches using Serper API"""
    
    # Official sanctions list sources
    SANCTIONS_SOURCES = {
        'OFAC_SDN': {
            'name': 'OFAC SDN List',
            'query_template': '"{entity_name}" site:ofac.treasury.gov OR site:sanctionssearch.ofac.treas.gov',
            'priority': 1
        },
        'UN_SANCTIONS': {
            'name': 'UN Sanctions',
            'query_template': '"{entity_name}" site:un.org/securitycouncil/sanctions',
            'priority': 2
        },
        'EU_SANCTIONS': {
            'name': 'EU Sanctions',
            'query_template': '"{entity_name}" site:ec.europa.eu/info/business-economy-euro/banking-and-finance/international-relations/restrictive-measures-sanctions',
            'priority': 3
        },
        'UK_HMT': {
            'name': 'UK HM Treasury Sanctions',
            'query_template': '"{entity_name}" site:gov.uk/government/organisations/hm-treasury/about/publication-scheme sanctions',
            'priority': 4
        },
        'FINCEN': {
            'name': 'FinCEN Watchlist',
            'query_template': '"{entity_name}" site:fincen.gov enforcement OR sanctions OR violations',
            'priority': 5
        },
        'INTERPOL': {
            'name': 'Interpol Wanted/Notices',
            'query_template': '"{entity_name}" site:interpol.int wanted OR red-notice',
            'priority': 6
        },
        'PEP': {
            'name': 'Politically Exposed Persons',
            'query_template': '"{entity_name}" "politically exposed person" OR PEP OR "government official"',
            'priority': 7
        }
    }
    
    def __init__(self, api_key: str, aws_profile: str = None):
        self.api_key = api_key
        self.aws_profile = aws_profile
        
        # Initialize AWS clients
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
            self.bedrock_client = session.client('bedrock-runtime', region_name='us-east-1')
            self.dynamodb = session.resource('dynamodb', region_name='us-east-1')
        else:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        self.table_name = 'CompanySanctionsScreening'
    
    def get_company_data_from_dynamodb(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve company and executive data from DynamoDB
        
        Company name sources (in order of priority):
        1. CompanySECData - for public companies
        2. CompanyPrivateData - for private companies
        
        Executive data source:
        - CompanyCXOData - for all companies
        """
        try:
            # Normalize company name to company_id format
            company_id = self._normalize_company_id(company_name)
            
            company_data = None
            data_source = None
            
            # Try CompanySECData first (public companies)
            logger.info(f"   🔍 Searching CompanySECData for company_id: {company_id}")
            sec_table = self.dynamodb.Table('CompanySECData')
            sec_response = sec_table.query(
                KeyConditionExpression='company_id = :company_id',
                ExpressionAttributeValues={':company_id': company_id},
                ScanIndexForward=False,
                Limit=1
            )
            
            if sec_response['Items']:
                company_data = sec_response['Items'][0]
                data_source = 'CompanySECData'
                logger.info(f"   ✅ Found in CompanySECData")
            else:
                # Try CompanyPrivateData (private companies)
                logger.info(f"   🔍 Not found in SEC data, checking CompanyPrivateData...")
                private_table = self.dynamodb.Table('CompanyPrivateData')
                private_response = private_table.query(
                    KeyConditionExpression='company_id = :company_id',
                    ExpressionAttributeValues={':company_id': company_id},
                    ScanIndexForward=False,
                    Limit=1
                )
                
                if private_response['Items']:
                    company_data = private_response['Items'][0]
                    data_source = 'CompanyPrivateData'
                    logger.info(f"   ✅ Found in CompanyPrivateData")
                else:
                    logger.warning(f"   ⚠️  Company not found in either SEC or Private data tables")
            
            # Get CXO data (for all companies)
            logger.info(f"   🔍 Retrieving executives from CompanyCXOData...")
            cxo_table = self.dynamodb.Table('CompanyCXOData')
            cxo_response = cxo_table.query(
                KeyConditionExpression='company_id = :company_id',
                ExpressionAttributeValues={':company_id': company_id}
            )
            
            executives = cxo_response.get('Items', [])
            logger.info(f"   ✅ Found {len(executives)} executives")
            
            # Extract official company name
            if company_data:
                official_name = company_data.get('company_name', company_name)
            else:
                # No company data found, use provided name
                official_name = company_name
                logger.warning(f"   ⚠️  Using provided company name: {official_name}")
            
            result = {
                'company_id': company_id,
                'company_name': official_name,
                'executives': executives,
                'company_data': company_data,
                'data_source': data_source
            }
            
            logger.info(f"✅ Retrieved data from DynamoDB:")
            logger.info(f"   Company: {official_name}")
            logger.info(f"   Company ID: {company_id}")
            logger.info(f"   Data Source: {data_source or 'None'}")
            logger.info(f"   Executives: {len(executives)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving data from DynamoDB: {e}")
            return None
    
    def _normalize_company_id(self, company_name: str) -> str:
        """Normalize company name to match DynamoDB company_id format"""
        # Convert to lowercase and replace spaces with underscores
        normalized = company_name.lower().replace(' ', '_')
        # Remove punctuation but keep underscores
        normalized = normalized.replace(',', '').replace('.', '')
        # Remove extra underscores
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        return normalized.strip('_')
    
    def screen_entity(self, entity_name: str, entity_type: str) -> SanctionsScreeningResult:
        """
        Screen a single entity (company or individual) against all sanctions lists
        
        Args:
            entity_name: Name of the company or individual
            entity_type: "company" or "individual"
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 Screening {entity_type.upper()}: {entity_name}")
        logger.info(f"{'='*80}")
        
        start_time = time.time()
        
        # Step 1: Parallel Serper searches across all sanctions sources
        logger.info(f"\n📡 Step 1: Searching {len(self.SANCTIONS_SOURCES)} sanctions sources...")
        search_results = self._parallel_sanctions_search(entity_name)
        
        # Step 2: Analyze results with AWS Nova Pro
        logger.info(f"\n🤖 Step 2: Analyzing matches with AWS Nova Pro...")
        matches = self._analyze_sanctions_matches(entity_name, entity_type, search_results)
        
        duration = time.time() - start_time
        logger.info(f"\n✅ Screening complete in {duration:.1f}s - Found {len(matches)} potential matches")
        
        return matches
    
    def screen_company_and_executives(self, company_name: str) -> SanctionsScreeningResult:
        """
        Complete sanctions screening for a company and all its executives
        
        Args:
            company_name: Name of the company to screen
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🛡️  SANCTIONS & WATCHLIST SCREENING")
        logger.info(f"{'='*80}")
        logger.info(f"Company: {company_name}")
        
        start_time = time.time()
        
        # Get company and executive data from DynamoDB
        logger.info(f"\n📊 Retrieving data from DynamoDB...")
        data = self.get_company_data_from_dynamodb(company_name)
        
        if not data:
            logger.error(f"❌ No data found for {company_name}")
            return None
        
        company_id = data['company_id']
        company_name_official = data['company_name']
        executives = data['executives']
        data_source = data.get('data_source', 'Unknown')
        
        logger.info(f"\n{'='*80}")
        
        # Screen company
        logger.info(f"\n{'='*80}")
        logger.info(f"🏢 SCREENING COMPANY")
        logger.info(f"{'='*80}")
        company_matches = self.screen_entity(company_name_official, "company")
        
        # Screen executives
        logger.info(f"\n{'='*80}")
        logger.info(f"👥 SCREENING EXECUTIVES ({len(executives)})")
        logger.info(f"{'='*80}")
        executive_matches = []
        
        for i, executive in enumerate(executives, 1):
            exec_name = executive.get('name', 'Unknown')
            logger.info(f"\n[{i}/{len(executives)}] Screening: {exec_name}")
            matches = self.screen_entity(exec_name, "individual")
            executive_matches.extend(matches)
        
        # Compile results
        result = SanctionsScreeningResult(
            company_id=company_id,
            company_name=company_name_official,
            screening_timestamp=datetime.utcnow().isoformat(),
            total_entities_screened=1 + len(executives),
            total_matches_found=len(company_matches) + len(executive_matches),
            company_matches=company_matches,
            executive_matches=executive_matches
        )
        
        # Save to DynamoDB
        self._save_to_dynamodb(result, data_source=data_source)
        
        duration = time.time() - start_time
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ SCREENING COMPLETE - Duration: {duration:.1f}s")
        logger.info(f"{'='*80}")
        logger.info(f"   Total Entities Screened: {result.total_entities_screened}")
        logger.info(f"   Total Matches Found: {result.total_matches_found}")
        logger.info(f"   Company Matches: {len(result.company_matches)}")
        logger.info(f"   Executive Matches: {len(result.executive_matches)}")
        logger.info(f"{'='*80}")
        
        return result
    
    def _parallel_sanctions_search(self, entity_name: str) -> Dict[str, Any]:
        """Perform parallel Serper searches across all sanctions sources"""
        
        queries = []
        for source_key, source_config in self.SANCTIONS_SOURCES.items():
            query = source_config['query_template'].format(entity_name=entity_name)
            queries.append({
                'source_key': source_key,
                'query': query,
                'source_name': source_config['name']
            })
        
        all_results = {}
        max_workers = 7  # One per sanctions source
        
        print(f"   🚀 Running {len(queries)} parallel searches...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_query = {
                executor.submit(self._perform_serper_search, q['query']): q
                for q in queries
            }
            
            completed = 0
            for future in as_completed(future_to_query):
                query_info = future_to_query[future]
                completed += 1
                try:
                    search_data = future.result()
                    all_results[query_info['source_key']] = {
                        'source_name': query_info['source_name'],
                        'results': search_data
                    }
                    result_count = len(search_data.get('organic', []))
                    print(f"      ✅ [{completed}/{len(queries)}] {query_info['source_name']}: {result_count} results")
                except Exception as e:
                    print(f"      ❌ [{completed}/{len(queries)}] {query_info['source_name']}: {str(e)[:60]}")
                    all_results[query_info['source_key']] = {
                        'source_name': query_info['source_name'],
                        'results': {}
                    }
        
        return all_results
    
    def _perform_serper_search(self, query: str) -> Dict[str, Any]:
        """Perform a single Serper API search"""
        try:
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'num': 10,  # Get top 10 results per source
                'gl': 'us',
                'hl': 'en'
            }
            
            response = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            return {}
    
    def _analyze_sanctions_matches(self, entity_name: str, entity_type: str, search_results: Dict[str, Any]) -> List[SanctionsMatch]:
        """Analyze search results using AWS Nova Pro to determine genuine matches"""
        
        # Compile all search results for Nova Pro analysis
        analysis_data = {
            'entity_name': entity_name,
            'entity_type': entity_type,
            'search_results': {}
        }
        
        for source_key, source_data in search_results.items():
            results = source_data.get('results', {})
            organic = results.get('organic', [])
            
            if organic:
                analysis_data['search_results'][source_key] = {
                    'source_name': source_data['source_name'],
                    'articles': [
                        {
                            'title': r.get('title', ''),
                            'snippet': r.get('snippet', ''),
                            'link': r.get('link', '')
                        }
                        for r in organic[:5]  # Top 5 results per source
                    ]
                }
        
        # Call Nova Pro for analysis
        prompt = self._build_sanctions_analysis_prompt(entity_name, entity_type, analysis_data)
        nova_response = self._call_nova_pro(prompt)
        
        # Parse Nova Pro response
        matches = self._parse_nova_sanctions_response(nova_response, entity_name, entity_type)
        
        return matches
    
    def _build_sanctions_analysis_prompt(self, entity_name: str, entity_type: str, analysis_data: Dict[str, Any]) -> str:
        """Build prompt for Nova Pro sanctions analysis"""
        
        prompt = f"""You are a sanctions compliance analyst. Analyze the following search results to determine if "{entity_name}" ({entity_type}) appears on any sanctions or watchlists.

Entity Name: {entity_name}
Entity Type: {entity_type}

Search Results from Official Sources:

"""
        
        for source_key, source_info in analysis_data['search_results'].items():
            source_name = source_info['source_name']
            articles = source_info['articles']
            
            prompt += f"\n{'='*80}\n"
            prompt += f"Source: {source_name}\n"
            prompt += f"{'='*80}\n"
            
            for i, article in enumerate(articles, 1):
                prompt += f"\nResult {i}:\n"
                prompt += f"Title: {article['title']}\n"
                prompt += f"Snippet: {article['snippet']}\n"
                prompt += f"URL: {article['link']}\n"
        
        prompt += f"""

{'='*80}
ANALYSIS TASK
{'='*80}

For each potential match found, provide:

1. **Match Type**: Which list/source (OFAC SDN, UN Sanctions, EU Sanctions, UK HMT, FinCEN, Interpol, PEP)
2. **Confidence Level**: High / Medium / Low
   - High: Exact name match + additional identifying information (DOB, address, passport, etc.)
   - Medium: Strong name match with some context but missing key identifiers
   - Low: Name similarity but significant uncertainty
3. **Confidence Justification**: 50-100 words clearly explaining WHY you assigned this confidence level, backing it with specific evidence from the search results
4. **Match Reason**: Specific reason (e.g., "Exact name and date of birth match on OFAC SDN List")
5. **Source**: Official source name
6. **Source URL**: The direct URL where this match was found (MANDATORY)
7. **Match Details**: Any additional relevant information (aliases, dates, identifiers, addresses, etc.)

IMPORTANT:
- Only report GENUINE matches where the entity name clearly matches the search results
- If NO genuine matches found, return an empty list
- Be conservative - when in doubt, use "Low" confidence or exclude the match
- Always include the source URL (this is mandatory)
- For PEP matches, verify the person holds or held a significant government/political position

Output Format (JSON):
{{
  "matches": [
    {{
      "match_type": "OFAC SDN",
      "confidence_level": "High",
      "confidence_justification": "Exact name match with John Doe appearing on the OFAC SDN list with matching date of birth (1975-03-15) and passport number ending in 7894. The address listed in Miami, FL matches known business operations. Multiple identifying details align perfectly.",
      "match_reason": "Exact name, DOB, and passport match on OFAC SDN List",
      "source": "OFAC SDN List",
      "source_url": "https://sanctionssearch.ofac.treas.gov/Details.aspx?id=12345",
      "match_details": {{
        "aliases": ["J. Doe", "Jonathan Doe"],
        "dob": "1975-03-15",
        "passport": "***7894",
        "address": "Miami, FL, USA"
      }}
    }}
  ]
}}

Analyze now:
"""
        
        return prompt
    
    def _call_nova_pro(self, prompt: str) -> str:
        """Call AWS Nova Pro for analysis"""
        try:
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "temperature": 0.2,
                    "topP": 0.9,
                    "maxTokens": 4000
                }
            }
            
            response = self.bedrock_client.invoke_model(
                modelId='us.amazon.nova-pro-v1:0',
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Nova Pro API error: {e}")
            return "{\"matches\": []}"
    
    def _parse_nova_sanctions_response(self, response_text: str, entity_name: str, entity_type: str) -> List[SanctionsMatch]:
        """Parse Nova Pro response and create SanctionsMatch objects"""
        
        matches = []
        
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in Nova Pro response")
                return matches
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            for match_data in data.get('matches', []):
                match = SanctionsMatch(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    match_type=match_data.get('match_type', 'Unknown'),
                    confidence_level=match_data.get('confidence_level', 'Low'),
                    confidence_justification=match_data.get('confidence_justification', ''),
                    match_reason=match_data.get('match_reason', ''),
                    source=match_data.get('source', ''),
                    source_url=match_data.get('source_url', ''),
                    match_details=match_data.get('match_details', {})
                )
                matches.append(match)
                
                logger.info(f"   ⚠️  Match Found: {match.match_type} - Confidence: {match.confidence_level}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
        except Exception as e:
            logger.error(f"Error parsing Nova response: {e}")
        
        return matches
    
    def _save_to_dynamodb(self, result: SanctionsScreeningResult, data_source: str = None):
        """Save sanctions screening results to DynamoDB"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Convert dataclasses to dictionaries and handle Decimal conversion
            def convert_to_dynamodb_format(obj):
                """Recursively convert objects to DynamoDB-compatible format"""
                if isinstance(obj, list):
                    return [convert_to_dynamodb_format(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: convert_to_dynamodb_format(v) for k, v in obj.items()}
                elif isinstance(obj, float):
                    return Decimal(str(obj))
                else:
                    return obj
            
            # Prepare matches data
            company_matches_data = [convert_to_dynamodb_format(asdict(m)) for m in result.company_matches]
            executive_matches_data = [convert_to_dynamodb_format(asdict(m)) for m in result.executive_matches]
            
            item = {
                'company_id': result.company_id,
                'screening_id': f"sanctions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'company_name': result.company_name,
                'screening_timestamp': result.screening_timestamp,
                'total_entities_screened': result.total_entities_screened,
                'total_matches_found': result.total_matches_found,
                'company_matches': company_matches_data,
                'executive_matches': executive_matches_data,
                'data_source': data_source or 'Unknown'  # Track where company data came from
            }
            
            table.put_item(Item=item)
            logger.info(f"\n💾 Saved to DynamoDB table: {self.table_name}")
            logger.info(f"   Company ID: {result.company_id}")
            logger.info(f"   Screening ID: {item['screening_id']}")
            
        except Exception as e:
            logger.error(f"Error saving to DynamoDB: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Screen companies and executives against sanctions and watchlists'
    )
    parser.add_argument(
        'company_name',
        help='Name of the company to screen'
    )
    
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        logger.error("❌ SERPER_API_KEY not found in environment variables")
        sys.exit(1)
    
    aws_profile = os.getenv('AWS_PROFILE', 'diligent')
    
    # Create screener and run
    screener = SerperSanctionsSearcher(api_key=api_key, aws_profile=aws_profile)
    result = screener.screen_company_and_executives(args.company_name)
    
    if result:
        # Print summary
        print(f"\n{'='*80}")
        print(f"📊 SANCTIONS SCREENING SUMMARY")
        print(f"{'='*80}")
        print(f"Company: {result.company_name}")
        print(f"Entities Screened: {result.total_entities_screened}")
        print(f"Total Matches: {result.total_matches_found}")
        print(f"\nCompany Matches: {len(result.company_matches)}")
        for match in result.company_matches:
            print(f"   - {match.match_type}: {match.confidence_level} confidence")
            print(f"     {match.source_url}")
        print(f"\nExecutive Matches: {len(result.executive_matches)}")
        for match in result.executive_matches:
            print(f"   - {match.entity_name} ({match.match_type}): {match.confidence_level} confidence")
            print(f"     {match.source_url}")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()

