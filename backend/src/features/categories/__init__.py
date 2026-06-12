from fastapi import APIRouter

from src.features.categories.routes.create_category import router as create_category_router
from src.features.categories.routes.delete_category import router as delete_category_router
from src.features.categories.routes.list_categories import router as list_categories_router
from src.features.categories.routes.update_category import router as update_category_router

router = APIRouter(tags=["Categories"])

router.include_router(list_categories_router, prefix="/categories")
router.include_router(create_category_router, prefix="/categories")
router.include_router(update_category_router, prefix="/categories")
router.include_router(delete_category_router, prefix="/categories")

__all__ = ["router"]
