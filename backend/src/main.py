import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import ALLOWED_ORIGINS
from src.database import close_db, get_db, init_db
from src.features.auth import router as auth_router
from src.features.exams import router as exams_router
from src.features.resolutions import router as resolutions_router
from src.features.users import router as users_router
from src.features.auth.middleware import PermissionMiddleware
from src.shared.utils.error_handler import http_exception_handler, validation_exception_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API v2")
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="API v2",
    description="API mínima com autenticação JWT e gestão de usuários.",
    version="0.1.0",
    lifespan=lifespan,
)
app.router.redirect_slashes = False

app.add_middleware(PermissionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]


@app.get("/health", tags=["Health"])
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(exams_router)
app.include_router(resolutions_router)
