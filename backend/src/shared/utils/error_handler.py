from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"success", "errors", "data"}.issubset(exc.detail):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    detail = exc.detail if isinstance(exc.detail, str) else "Erro na requisicao"
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "errors": [detail], "data": None},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"success": False, "errors": [error["msg"] for error in exc.errors()], "data": None},
    )
