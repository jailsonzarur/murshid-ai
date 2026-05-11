from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.users.schemas.user_schemas import UserListSchema
from src.features.users.services.user_service import list_users
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get("", operation_id="getUsers", response_model=SuccessResponse[list[UserListSchema]])
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users = await list_users(db)
    return SuccessResponse(success=True, errors=None, data=users)
