from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from services.github_service import GitHubService, GitHubServiceError
from models.schemas import Repository

router = APIRouter(prefix="/repos", tags=["repositories"])

@router.get("/", response_model=List[Repository])
async def list_repositories(service: GitHubService = Depends()):
    """
    List all repositories accessible to the authenticated GitHub App.
    """
    try:
        return await service.get_all_repos()
    except GitHubServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{owner}/{repo}", response_model=Repository)
async def get_repository(
    owner: str,
    repo: str,
    service: GitHubService = Depends()
):
    """
    Get details for a specific repository.
    """
    try:
        # This is a simplified example - you'd need to implement get_repo in the service
        raise NotImplementedError("get_repository endpoint not implemented yet")
    except GitHubServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "Not Found" in str(e)
            else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
