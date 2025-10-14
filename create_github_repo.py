#!/usr/bin/env python3
"""
Create GitHub Repository using GitHub API
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_github_repo():
    """Create a GitHub repository using the GitHub API"""
    
    # Get GitHub token from environment
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found in .env file")
        return None
    
    # Repository details
    repo_name = "STEPSCREEN"
    repo_description = "Company Data Extraction Pipeline - SEC & CXO data extraction using AWS Nova Pro, Lambda, Step Functions, DynamoDB, and S3"
    
    # GitHub API endpoint
    api_url = "https://api.github.com/user/repos"
    
    # Headers for authentication
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Repository configuration
    repo_data = {
        "name": repo_name,
        "description": repo_description,
        "private": False,  # Set to True if you want a private repository
        "auto_init": False,  # Don't create README.md automatically
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True
    }
    
    print("="*70)
    print("GitHub Repository Creation")
    print("="*70)
    print(f"\nRepository Name: {repo_name}")
    print(f"Description: {repo_description}")
    print(f"Visibility: {'Private' if repo_data['private'] else 'Public'}")
    print("\nCreating repository...")
    
    try:
        # Make API request
        response = requests.post(api_url, json=repo_data, headers=headers)
        
        if response.status_code == 201:
            repo_info = response.json()
            print("\n✅ Repository created successfully!")
            print(f"\n📁 Repository Details:")
            print(f"   Name: {repo_info['name']}")
            print(f"   Owner: {repo_info['owner']['login']}")
            print(f"   URL: {repo_info['html_url']}")
            print(f"   Clone URL (HTTPS): {repo_info['clone_url']}")
            print(f"   Clone URL (SSH): {repo_info['ssh_url']}")
            print(f"\n🔗 Next Steps:")
            print(f"   1. Initialize git in your local directory:")
            print(f"      git init")
            print(f"      git add .")
            print(f"      git commit -m 'Initial commit: Company Data Extraction Pipeline'")
            print(f"   2. Add remote and push:")
            print(f"      git remote add origin {repo_info['clone_url']}")
            print(f"      git branch -M main")
            print(f"      git push -u origin main")
            print("="*70)
            
            return repo_info
            
        elif response.status_code == 422:
            error_info = response.json()
            if 'errors' in error_info and any('already exists' in str(err) for err in error_info['errors']):
                print(f"\n⚠️  Repository '{repo_name}' already exists!")
                print(f"   Please check: https://github.com/rchandran/{repo_name}")
            else:
                print(f"\n❌ Error creating repository: {error_info.get('message', 'Unknown error')}")
            return None
            
        elif response.status_code == 401:
            print("\n❌ Authentication failed!")
            print("   Please check your GITHUB_TOKEN in .env file")
            print("   Token should have 'repo' scope permissions")
            return None
            
        else:
            print(f"\n❌ Failed to create repository")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return None


def get_github_user():
    """Get authenticated GitHub user information"""
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        return None
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print(f"\n✅ Authenticated as: {user_info['login']}")
            print(f"   Name: {user_info.get('name', 'Not set')}")
            print(f"   Email: {user_info.get('email', 'Not set')}")
            return user_info
        else:
            print(f"\n❌ Failed to authenticate")
            return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


if __name__ == "__main__":
    # First verify authentication
    user = get_github_user()
    
    if user:
        # Create repository
        repo = create_github_repo()

