from fastapi import APIRouter
from .endpoints import repos, issues

api_router = APIRouter()
api_router.include_router(repos.router)
api_router.include_router(issues.router)
