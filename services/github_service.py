import time
import jwt
import json
import httpx
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from config import settings
from models.schemas import Repository, Issue, IssueCreate, IssueUpdate

class GitHubServiceError(Exception):
    """Base exception for GitHub service errors"""
    pass

class GitHubService:
    BASE_URL = "https://api.github.com"
    REDIS_PREFIX = "github:token"
    TOKEN_TTL = 60 * 55  # 55 minutes (GitHub tokens expire in 60 minutes)

    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.client = httpx.AsyncClient()
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        await self.redis.close()
    
    def _create_jwt(self) -> str:
        """Create a JWT for GitHub App authentication"""
        now = int(time.time())
        payload = {
            'iat': now,
            'exp': now + (10 * 60),  # JWT expires in 10 minutes
            'iss': self.app_id
        }
        
        try:
            return jwt.encode(payload, settings.private_key_bytes, algorithm='RS256')
            
        except Exception as e:
            print(f"ERROR: Failed to create JWT: {str(e)}")
            if hasattr(settings, 'private_key_bytes'):
                print(f"Key type: {type(settings.private_key_bytes).__name__}")
                print(f"Key length: {len(settings.private_key_bytes) if hasattr(settings.private_key_bytes, '__len__') else 'N/A'}")
            raise
    
    async def _get_installation_token(self, installation_id: str) -> str:
        """Get or create an installation access token with Redis caching"""
        cache_key = f"{self.REDIS_PREFIX}:{installation_id}"
        now = datetime.utcnow()
        
        try:
            # Try to get token from Redis
            cached = await self.redis.get(cache_key)
            if cached:
                token_data = json.loads(cached)
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                
                # Return cached token if it's still valid (with 5 min buffer)
                if now < expires_at - timedelta(minutes=5):
                    return token_data['token']
        except Exception as e:
            print(f"Redis cache error (non-fatal): {e}")
        
        # Get a new token from GitHub
        jwt_token = self._create_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = await self.client.post(
            f"{self.BASE_URL}/app/installations/{installation_id}/access_tokens",
            headers=headers
        )
        response.raise_for_status()
        
        token_data = response.json()
        expires_at = datetime.strptime(token_data['expires_at'], '%Y-%m-%dT%H:%M:%SZ')
        
        # Cache the token in Redis
        try:
            cache_data = {
                'token': token_data['token'],
                'expires_at': expires_at.isoformat()
            }
            await self.redis.setex(
                cache_key,
                self.TOKEN_TTL,
                json.dumps(cache_data)
            )
        except Exception as e:
            print(f"Failed to cache token in Redis: {e}")
        
        return token_data['token']
    
    async def get_authenticated_client(self, installation_id: str) -> httpx.AsyncClient:
        """Get an authenticated HTTP client for a specific installation"""
        token = await self._get_installation_token(installation_id)
        return self.client
    
    async def get_installations(self) -> List[dict]:
        """Get all installations for the authenticated app"""
        jwt_token = self._create_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f"{self.BASE_URL}/app/installations"
        response = await self.client.get(url, headers=headers)
        
        if response.status_code != 200:
            raise GitHubServiceError(
                f"Failed to get installations: {response.text}"
            )
            
        return response.json()
    
    async def get_installation_repos(self, installation_id: str) -> List[Repository]:
        """Get repositories accessible to an installation"""
        token = await self._get_installation_token(installation_id)
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f"{self.BASE_URL}/installation/repositories"
        response = await self.client.get(url, headers=headers)
        
        if response.status_code != 200:
            raise GitHubServiceError(
                f"Failed to get installation repos: {response.text}"
            )
        
        data = response.json()
        return [Repository(**repo) for repo in data.get('repositories', [])]
    
    async def get_all_repos(self) -> List[Repository]:
        """Get all repositories across all installations"""
        installations = await self.get_installations()
        all_repos = []
        
        for installation in installations:
            installation_id = installation['id']
            try:
                repos = await self.get_installation_repos(installation_id)
                all_repos.extend(repos)
            except Exception as e:
                print(f"Error getting repos for installation {installation_id}: {str(e)}")
                continue
                
        return all_repos
    
    async def create_issue(
        self,
        repo_full_name: str,
        issue: IssueCreate,
        installation_id: str
    ) -> Issue:
        """Create a new issue in a repository"""
        token = await self._get_installation_token(installation_id)
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f"{self.BASE_URL}/repos/{repo_full_name}/issues"
        payload = issue.dict(exclude_unset=True)
        
        response = await self.client.post(url, headers=headers, json=payload)
        
        if response.status_code != 201:
            raise GitHubServiceError(
                f"Failed to create issue: {response.text}"
            )
            
        return Issue(**response.json())
    
    async def close_issue(
        self,
        repo_full_name: str,
        issue_number: int,
        installation_id: str
    ) -> None:
        """Close an issue"""
        token = await self._get_installation_token(installation_id)
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f"{self.BASE_URL}/repos/{repo_full_name}/issues/{issue_number}"
        payload = {'state': 'closed'}
        
        response = await self.client.patch(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise GitHubServiceError(
                f"Failed to close issue: {response.text}"
            )
