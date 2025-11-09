from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List
from services.github_service import GitHubService, GitHubServiceError, get_github_service
from models.schemas import Issue, IssueCreate, IssueUpdate

router = APIRouter(prefix="/issues", tags=["issues"])

@router.post("/{owner}/{repo}", response_model=Issue, status_code=status.HTTP_201_CREATED)
async def create_issue(
    owner: str,
    repo: str,
    issue: IssueCreate,
    service: GitHubService = Depends(get_github_service)
):
    """
    Create a new issue in the specified repository.
    """
    repo_full_name = f"{owner}/{repo}"
    try:
        # Get installations to find the right one for this repo
        installations = await service.get_installations()
        
        # Find the installation that has access to this repo
        for installation in installations:
            installation_id = installation['id']
            try:
                repos = await service.get_installation_repos(installation_id)
                if any(r.full_name == repo_full_name for r in repos):
                    return await service.create_issue(repo_full_name, issue, installation_id)
            except GitHubServiceError:
                continue
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No installation found with access to {repo_full_name}"
        )
        
    except GitHubServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/{owner}/{repo}/{issue_number}", response_model=Issue)
async def update_issue(
    owner: str,
    repo: str,
    issue_number: int = Path(..., gt=0),
    issue_update: IssueUpdate = None,
    service: GitHubService = Depends(get_github_service)
):
    """
    Update an existing issue.
    """
    # Implementation would be similar to create_issue
    raise NotImplementedError("update_issue endpoint not implemented yet")

@router.delete(
    "/{owner}/{repo}/{issue_number}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def close_issue(
    owner: str,
    repo: str,
    issue_number: int = Path(..., gt=0),
    service: GitHubService = Depends(get_github_service)
):
    """
    Close an issue.
    """
    repo_full_name = f"{owner}/{repo}"
    try:
        installations = await service.get_installations()
        
        for installation in installations:
            installation_id = installation['id']
            try:
                repos = await service.get_installation_repos(installation_id)
                if any(r.full_name == repo_full_name for r in repos):
                    await service.close_issue(repo_full_name, issue_number, installation_id)
                    return None
            except GitHubServiceError:
                continue
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_full_name} not found or access denied"
        )
        
    except GitHubServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
