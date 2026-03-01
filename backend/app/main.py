from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.controllers.completion_controller import router as completion_router
from app.controllers.dialect_controller import router as dialect_router
from app.controllers.health_controller import router as health_router
from app.controllers.lsp_controller import router as lsp_router
from app.controllers.workspace_controller import router as workspace_router
from app.core import database
from app.core.exceptions import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="SQL AI Editor API")
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(workspace_router)
    app.include_router(completion_router)
    app.include_router(dialect_router)
    app.include_router(lsp_router)

    @app.on_event("startup")
    def on_startup() -> None:
        database.Base.metadata.create_all(bind=database.engine)

    return app


app = create_app()
