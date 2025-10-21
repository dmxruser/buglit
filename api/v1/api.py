from fastapi import APIRouter
from .endpoints import repos, issues, user, ai

api_router = APIRouter()
api_router.include_router(repos.router)
api_router.include_router(issues.router)
api_router.include_router(user.router)
api_router.include_router(ai.router)
