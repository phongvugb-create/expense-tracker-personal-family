from fastapi import APIRouter

from app.api.v1.accounts import router as accounts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.categories import router as categories_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.families import router as families_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.recurring_transactions import recurring_router
from app.api.v1.reports import reports_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.transfers import router as transfers_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_v1_router.include_router(recurring_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(accounts_router)
api_v1_router.include_router(families_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(transfers_router)
api_v1_router.include_router(budgets_router)
