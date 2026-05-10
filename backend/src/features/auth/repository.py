from sqlalchemy.ext.asyncio import AsyncSession

from src.features.users.models import UserModel


async def create_user(db: AsyncSession, name: str, email: str, hashed_password: str) -> UserModel:
    user = UserModel(name=name, email=email.lower(), password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
