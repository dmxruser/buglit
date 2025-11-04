import time
import jwt
import json
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import List, Optional
from github import Github, GithubIntegration, Auth
from config import settings
from models.schemas import Repository, Issue, IssueCreate, IssueUpdate

class GitHubServiceError(Exception):
    """Base exception for GitHub service errors"""
    pass

async def get_github_service() -> 'GitHubService':
    """Factory function to create and return a GitHubService instance"""
    service = GitHubService()
    await service.initialize()
    return service

class GitHubService:
    REDIS_PREFIX = "github:token"
    TOKEN_TTL = 60 * 55  # 55 minutes (GitHub tokens expire in 60 minutes)
    
    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.private_key = settings.private_key_bytes
        self.redis = None
        self.integration = None
    
    async def initialize(self):
        """Initialize async components"""
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        
        # Create GitHub Integration for app-level operations
        auth = Auth.AppAuth(self.app_id, self.private_key)
        self.integration = GithubIntegration(auth=auth)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.redis:
            await self.redis.close()
    
    async def _get_installation_token(self, installation_id: int) -> str:
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
        token_obj = self.integration.get_access_token(installation_id)
        
        # Cache the token in Redis
        try:
            cache_data = {
                'token': token_obj.token,
                'expires_at': token_obj.expires_at.isoformat()
            }
            await self.redis.setex(
                cache_key,
                self.TOKEN_TTL,
                json.dumps(cache_data)
            )
        except Exception as e:
            print(f"Failed to cache token in Redis: {e}")
        
        return token_obj.token
    
    async def _get_github_client(self, installation_id: int) -> Github:
        """Get an authenticated GitHub client for a specific installation"""
        token = await self._get_installation_token(installation_id)
        return Github(token)
    
    async def get_installations(self) -> List[dict]:
        """Get all installations for the authenticated app"""
        installations = self.integration.get_installations()
        return [
            {
                'id': inst.id,
                'account': inst.account.login,
                'target_type': inst.target_type
            }
            for inst in installations
        ]
    
    async def get_installation_repos(self, installation_id: int) -> List[Repository]:
        """Get repositories accessible to an installation"""
        g = await self._get_github_client(installation_id)
        installation = g.get_installation(installation_id)
        
        repos = []
        for repo in installation.get_repos():
            repos.append(Repository(
                id=repo.id,
                name=repo.name,
                full_name=repo.full_name,
                private=repo.private,
                description=repo.description,
                html_url=repo.html_url,
                default_branch=repo.default_branch
            ))
        
        return repos
    
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
        installation_id: int
    ) -> Issue:
        """Create a new issue in a repository"""
        g = await self._get_github_client(installation_id)
        repo = g.get_repo(repo_full_name)
        
        gh_issue = repo.create_issue(
            title=issue.title,
            body=issue.body or "",
            labels=issue.labels or [],
            assignees=issue.assignees or []
        )
        
        return Issue(
            id=gh_issue.id,
            number=gh_issue.number,
            title=gh_issue.title,
            body=gh_issue.body,
            state=gh_issue.state,
            html_url=gh_issue.html_url,
            created_at=gh_issue.created_at,
            updated_at=gh_issue.updated_at
        )
    
    async def close_issue(
        self,
        repo_full_name: str,
        issue_number: int,
        installation_id: int
    ) -> None:
        """Close an issue"""
        g = await self._get_github_client(installation_id)
        repo = g.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        issue.edit(state='closed')
    
    async def get_user_repos(self) -> List[Repository]:
        """Get repositories for the authenticated user"""
        installations = await self.get_installations()
        if not installations:
            raise GitHubServiceError("No GitHub App installations found")
            
        return await self.get_all_repos()

    async def create_or_update_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str,
        installation_id: int
    ) -> dict:
        """Create or update a file in a repository"""
        g = await self._get_github_client(installation_id)
        repo = g.get_repo(repo_full_name)
        
        try:
            # Try to get existing file
            file = repo.get_contents(file_path, ref=branch)
            result = repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=file.sha,
                branch=branch
            )
        except:
            # File doesn't exist, create it
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch
            )
        
        return {
            'commit': result['commit'].sha,
            'content': result['content'].path
        }
    
    async def create_branch(
        self,
        repo_full_name: str,
        new_branch_name: str,
        base_branch: str,
        installation_id: int
    ):
        """Create a new branch"""
        g = await self._get_github_client(installation_id)
        repo = g.get_repo(repo_full_name)
        
        # Get the base branch reference
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha
        
        # Create new branch
        repo.create_git_ref(
            ref=f"refs/heads/{new_branch_name}",
            sha=base_sha
        )
    
    async def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        head_branch: str,
        base_branch: str,
        body: str,
        installation_id: int
    ) -> dict:
        """Create a pull request"""
        g = await self._get_github_client(installation_id)
        repo = g.get_repo(repo_full_name)
        
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )
        
        return {
            'number': pr.number,
            'html_url': pr.html_url,
            'title': pr.title,
            'state': pr.state
        }
    
    async def commit_and_create_pr(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        pr_title: str,
        pr_body: str,
        base_branch: str,
        installation_id: int,
        new_branch_name: Optional[str] = None
    ) -> dict:
        """
        Complete workflow: create branch, commit file, and create PR
        
        Args:
            repo_full_name: Repository in format "owner/repo"
            file_path: Path to file in repo
            content: File content
            commit_message: Commit message
            pr_title: Pull request title
            pr_body: Pull request description
            base_branch: Base branch (usually "main" or "master")
            installation_id: GitHub App installation ID
            new_branch_name: Optional custom branch name
        
        Returns:
            Dict with PR details and commit info
        """
        # Generate branch name if not provided
        if not new_branch_name:
            timestamp = int(time.time())
            new_branch_name = f"update-{file_path.replace('/', '-')}-{timestamp}"
        
        try:
            # Step 1: Create new branch
            await self.create_branch(
                repo_full_name=repo_full_name,
                new_branch_name=new_branch_name,
                base_branch=base_branch,
                installation_id=installation_id
            )
            
            # Step 2: Commit file to new branch
            commit_result = await self.create_or_update_file(
                repo_full_name=repo_full_name,
                file_path=file_path,
                content=content,
                commit_message=commit_message,
                branch=new_branch_name,
                installation_id=installation_id
            )
            
            # Step 3: Create pull request
            pr_result = await self.create_pull_request(
                repo_full_name=repo_full_name,
                title=pr_title,
                head_branch=new_branch_name,
                base_branch=base_branch,
                body=pr_body,
                installation_id=installation_id
            )
            
            return {
                'success': True,
                'branch': new_branch_name,
                'commit': commit_result['commit'],
                'pr': pr_result
            }
            
        except Exception as e:
            raise GitHubServiceError(f"Failed to commit and create PR: {str(e)}")