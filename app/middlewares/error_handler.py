"""
app/middlewares/error_handler.py

Registers global exception handlers so every error response follows the
same JSON envelope, regardless of which endpoint raised it.

Handler bodies are intentionally minimal placeholders — response shaping
and error-code mapping will be filled in during the business-logic phase.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_config import logger


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTPException: {exc.status_code} - {exc.detail} - path={request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "data": None, "message": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"ValidationError: path={request.url.path} - {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"success": False, "data": None, "message": "Validation error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception at path={request.url.path}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "message": "Internal server error"},
        )
