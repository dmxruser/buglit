from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from services.github_service import get_github_service, GitHubServiceError
# cute
router = APIRouter(prefix="/user", tags=["user"])

@router.get("/repos", response_model=List[str])
async def get_user_repos(service: get_github_service = Depends()):
    """
    List all repositories for the authenticated user.
    """
    try:
        repos = await service.get_user_repos()
        return [repo.name for repo in repos]
    except GitHubServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/repos/search", response_model=List[str])
async def search_user_repos(query: str = Query(..., min_length=1), service: get_github_service = Depends()):
    """
    Search for repositories for the authenticated user.
    """
    try:
        repos = await service.get_user_repos()
        return [repo.name for repo in repos if query.lower() in repo.name.lower()]
    except GitHubServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
