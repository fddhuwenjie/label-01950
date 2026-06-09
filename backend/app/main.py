"""
FastAPI application entry point for SQLFluff LSP WebSocket Server.
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from .config import settings
from .core import (
    logger,
    setup_logging,
    BaseAppException,
    LSPException,
    WebSocketException,
    ValidationException,
    InternalServerException,
    ErrorCode,
)
from .websocket import websocket_handler, connection_manager
from .services import linter_service, explain_service
from .models import ExplainRequest, ExplainResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging(settings.DEBUG)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Supported dialects: {settings.SUPPORTED_DIALECTS}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await connection_manager.close_all()
    linter_service.shutdown()
    explain_service.shutdown()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="WebSocket server for SQL linting using SQLFluff LSP",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_error_response(
    code: int,
    message: str,
    details: dict = None,
    status_code: int = 400
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {}
            }
        }
    )


@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    """Global exception handler for all application exceptions."""
    logger.error(f"Application Exception: {exc.message} (code: {exc.code})")
    return create_error_response(
        code=exc.code,
        message=exc.user_message,
        details=exc.details,
        status_code=400
    )


@app.exception_handler(LSPException)
async def lsp_exception_handler(request: Request, exc: LSPException):
    """Global exception handler for LSP exceptions."""
    logger.error(f"LSP Exception: {exc.message} (code: {exc.code})")
    return create_error_response(
        code=exc.code,
        message=exc.user_message,
        details=exc.details,
        status_code=400
    )


@app.exception_handler(WebSocketException)
async def websocket_exception_handler(request: Request, exc: WebSocketException):
    """Global exception handler for WebSocket exceptions."""
    logger.error(f"WebSocket Exception: {exc.message} (code: {exc.code})")
    return create_error_response(
        code=exc.code,
        message=exc.user_message,
        details=exc.details,
        status_code=400
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors with friendly messages."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    # Extract field errors
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}")
    
    return create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="请求参数验证失败，请检查输入",
        details={"errors": errors},
        status_code=422
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with friendly messages."""
    logger.warning(f"Pydantic validation error: {exc.errors()}")
    
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}")
    
    return create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="数据验证失败，请检查输入格式",
        details={"errors": errors},
        status_code=422
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with friendly messages."""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    # Map HTTP status codes to friendly messages
    status_messages = {
        400: "请求格式错误，请检查输入",
        401: "未授权访问，请先登录",
        403: "没有权限执行此操作",
        404: "请求的资源不存在",
        405: "不支持的请求方法",
        408: "请求超时，请稍后重试",
        429: "请求过于频繁，请稍后重试",
        500: "服务器内部错误，请稍后重试",
        502: "网关错误，请稍后重试",
        503: "服务暂时不可用，请稍后重试",
        504: "网关超时，请稍后重试",
    }
    
    message = status_messages.get(exc.status_code, str(exc.detail))
    
    return create_error_response(
        code=exc.status_code,
        message=message,
        details={"original_detail": str(exc.detail)} if exc.detail else {},
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors."""
    # Log the full exception for debugging
    logger.exception(f"Unexpected error: {type(exc).__name__}: {exc}")
    
    # Return a friendly error message to the user
    return create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message="服务器内部错误，请稍后重试。如果问题持续存在，请联系技术支持。",
        details={
            "error_type": type(exc).__name__,
            "request_path": str(request.url.path)
        },
        status_code=500
    )


@app.get("/")
async def root():
    """Root endpoint returning server info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "connections": connection_manager.active_count
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connections": connection_manager.active_count
    }


@app.get("/dialects")
async def get_dialects():
    """Get list of supported SQL dialects."""
    return {
        "dialects": settings.SUPPORTED_DIALECTS,
        "default": settings.DEFAULT_DIALECT
    }


@app.post("/api/explain", response_model=ExplainResponse)
async def explain_sql(request: ExplainRequest):
    """
    Generate a simulated execution plan for the given SQL.

    Validates SQL syntax using SQLFluff Linter, then parses the SQL AST
    to generate a simulated execution plan tree with cost estimates.
    """
    logger.info(f"Explain request received, dialect: {request.dialect}, sql length: {len(request.sql)}")

    result = await explain_service.explain(request.sql, request.dialect)

    if not result["success"]:
        return ExplainResponse(success=False, root=None, error=result["error"])

    return ExplainResponse(success=True, root=result["root"], error=None)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(default=None)
):
    """
    WebSocket endpoint for LSP communication.
    
    Args:
        websocket: WebSocket connection.
        client_id: Optional client identifier (auto-generated if not provided).
    """
    if not client_id:
        client_id = str(uuid.uuid4())
    
    logger.info(f"WebSocket connection request from {client_id}")
    await websocket_handler.handle_connection(websocket, client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
