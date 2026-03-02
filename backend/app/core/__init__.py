"""
Core module containing logging and exception handling.
"""
from .logging import logger, setup_logging
from .exceptions import (
    ErrorCode,
    ERROR_MESSAGES,
    get_error_message,
    BaseAppException,
    LSPException,
    WebSocketException,
    LintTimeoutException,
    InvalidDialectException,
    DocumentTooLargeException,
    DocumentNotFoundException,
    ValidationException,
    InvalidPositionException,
    ConnectionLimitException,
    InternalServerException,
)

__all__ = [
    "logger",
    "setup_logging",
    "ErrorCode",
    "ERROR_MESSAGES",
    "get_error_message",
    "BaseAppException",
    "LSPException",
    "WebSocketException",
    "LintTimeoutException",
    "InvalidDialectException",
    "DocumentTooLargeException",
    "DocumentNotFoundException",
    "ValidationException",
    "InvalidPositionException",
    "ConnectionLimitException",
    "InternalServerException",
]
