from fastapi import APIRouter

from app.api.v1.endpoints import items, login, private, users, utils
from app.api.v1.orders import infos
from app.api.v1.ai_agents import router as ai_agents
from app.api.v1.liama_index import router as llamaindex_router

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(private.router, prefix="/private", tags=["private"])
api_router.include_router(infos.router, prefix="/orders", tags=["orders"])
api_router.include_router(ai_agents.router, prefix="/ai-agents", tags=["ai-agents"])
api_router.include_router(llamaindex_router, prefix="/llamaindex", tags=["llamaindex"])
