from fastapi import APIRouter

from src.features.auth.routes.get_profile import router as profile_router
from src.features.auth.routes.logout import router as logout_router
from src.features.auth.routes.refresh import router as refresh_router
from src.features.auth.routes.sign_in import router as sign_in_router
from src.features.auth.routes.sign_up import router as sign_up_router

router = APIRouter(prefix="/auth", tags=["Auth"])

router.include_router(sign_in_router)
router.include_router(sign_up_router)
router.include_router(profile_router)
router.include_router(refresh_router)
router.include_router(logout_router)
