from fastapi import APIRouter
from .endpoints import repos, issues, user, ai, cron

api_router = APIRouter()

@api_router.get("/health")
async def health():
    return {"status": "ok"}

api_router.include_router(repos.router)
api_router.include_router(issues.router)
api_router.include_router(user.router)
api_router.include_router(ai.router)
api_router.include_router(cron.router)
