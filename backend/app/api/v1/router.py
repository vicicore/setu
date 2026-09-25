from fastapi import APIRouter

from app.api.v1 import admin, citizens, demo, eligibility, health, vault, webhooks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(demo.router)
api_router.include_router(webhooks.router)
api_router.include_router(eligibility.router)
api_router.include_router(citizens.router)
api_router.include_router(vault.router)
api_router.include_router(admin.router)
