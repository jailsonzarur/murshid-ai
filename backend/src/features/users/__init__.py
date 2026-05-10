from fastapi import APIRouter

from src.features.users.routes.create_user import router as create_user_router
from src.features.users.routes.delete_user import router as delete_user_router
from src.features.users.routes.get_users import router as get_users_router
from src.features.users.routes.update_user import router as update_user_router
from src.features.users.routes.update_user_role import router as update_user_role_router

router = APIRouter(prefix="/users", tags=["Users"])

router.include_router(get_users_router)
router.include_router(create_user_router)
router.include_router(update_user_router)
router.include_router(update_user_role_router)
router.include_router(delete_user_router)
