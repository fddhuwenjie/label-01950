"""
Custom exception classes for the application.
All exceptions return user-friendly error messages instead of system errors.
"""
from typing import Optional, Dict, Any
from enum import IntEnum


class ErrorCode(IntEnum):
    """Error codes for the application."""
    # WebSocket errors (1001-1099)
    WEBSOCKET_CONNECTION_FAILED = 1001
    WEBSOCKET_SEND_FAILED = 1002
    WEBSOCKET_RECEIVE_FAILED = 1003
    WEBSOCKET_CONNECTION_LIMIT = 1004
    
    # LSP errors (1101-1199)
    LSP_SERVICE_UNAVAILABLE = 1101
    LSP_INVALID_REQUEST = 1102
    LSP_METHOD_NOT_FOUND = 1103
    LSP_INVALID_PARAMS = 1104
    
    # Linter errors (1201-1299)
    LINT_TIMEOUT = 1201
    LINT_PARSE_ERROR = 1202
    LINT_INTERNAL_ERROR = 1203
    
    # Dialect errors (1301-1399)
    INVALID_DIALECT = 1301
    DIALECT_NOT_SUPPORTED = 1302
    
    # Document errors (1401-1499)
    DOCUMENT_TOO_LARGE = 1401
    DOCUMENT_NOT_FOUND = 1402
    DOCUMENT_INVALID_URI = 1403
    
    # Validation errors (1501-1599)
    VALIDATION_ERROR = 1501
    INVALID_POSITION = 1502
    INVALID_RANGE = 1503
    
    # Internal errors (1901-1999)
    INTERNAL_ERROR = 1901
    UNKNOWN_ERROR = 1999


# User-friendly error messages
ERROR_MESSAGES: Dict[int, str] = {
    ErrorCode.WEBSOCKET_CONNECTION_FAILED: "无法建立WebSocket连接，请检查网络后重试",
    ErrorCode.WEBSOCKET_SEND_FAILED: "消息发送失败，请检查连接状态",
    ErrorCode.WEBSOCKET_RECEIVE_FAILED: "消息接收失败，请刷新页面重试",
    ErrorCode.WEBSOCKET_CONNECTION_LIMIT: "连接数已达上限，请稍后重试",
    
    ErrorCode.LSP_SERVICE_UNAVAILABLE: "语言服务暂时不可用，请稍后重试",
    ErrorCode.LSP_INVALID_REQUEST: "请求格式无效，请检查请求参数",
    ErrorCode.LSP_METHOD_NOT_FOUND: "不支持的操作类型",
    ErrorCode.LSP_INVALID_PARAMS: "请求参数无效，请检查输入",
    
    ErrorCode.LINT_TIMEOUT: "SQL分析超时，请尝试简化SQL语句或稍后重试",
    ErrorCode.LINT_PARSE_ERROR: "SQL解析失败，请检查SQL语法",
    ErrorCode.LINT_INTERNAL_ERROR: "SQL分析服务内部错误，请稍后重试",
    
    ErrorCode.INVALID_DIALECT: "不支持的SQL方言",
    ErrorCode.DIALECT_NOT_SUPPORTED: "该SQL方言暂不支持",
    
    ErrorCode.DOCUMENT_TOO_LARGE: "文档过大，请减少代码量后重试",
    ErrorCode.DOCUMENT_NOT_FOUND: "文档不存在",
    ErrorCode.DOCUMENT_INVALID_URI: "无效的文档URI",
    
    ErrorCode.VALIDATION_ERROR: "输入验证失败，请检查输入内容",
    ErrorCode.INVALID_POSITION: "无效的光标位置",
    ErrorCode.INVALID_RANGE: "无效的文本范围",
    
    ErrorCode.INTERNAL_ERROR: "服务器内部错误，请稍后重试",
    ErrorCode.UNKNOWN_ERROR: "发生未知错误，请稍后重试",
}


def get_error_message(code: int, default: str = "发生错误，请稍后重试") -> str:
    """Get user-friendly error message by error code."""
    return ERROR_MESSAGES.get(code, default)


class BaseAppException(Exception):
    """Base exception class for all application exceptions."""
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: int = ErrorCode.UNKNOWN_ERROR,
        details: Optional[dict] = None,
        user_message: Optional[str] = None
    ):
        # Technical message for logging
        self.message = message or get_error_message(code)
        self.code = code
        self.details = details or {}
        # User-friendly message for frontend display
        self.user_message = user_message or get_error_message(code)
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.user_message,
                "details": self.details
            }
        }


class LSPException(BaseAppException):
    """Base exception for LSP-related errors."""
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: int = ErrorCode.LSP_SERVICE_UNAVAILABLE,
        details: Optional[dict] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message, code, details, user_message)


class WebSocketException(BaseAppException):
    """Exception for WebSocket-related errors."""
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: int = ErrorCode.WEBSOCKET_CONNECTION_FAILED,
        details: Optional[dict] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message, code, details, user_message)


class LintTimeoutException(LSPException):
    """Exception raised when linting operation times out."""
    
    def __init__(self, timeout_seconds: Optional[float] = None):
        details = {"timeout_seconds": timeout_seconds} if timeout_seconds else {}
        super().__init__(
            message=f"Lint operation timed out after {timeout_seconds}s" if timeout_seconds else "Lint operation timed out",
            code=ErrorCode.LINT_TIMEOUT,
            details=details,
            user_message="SQL分析超时，请尝试简化SQL语句或稍后重试"
        )


class InvalidDialectException(LSPException):
    """Exception raised when an invalid SQL dialect is specified."""
    
    def __init__(self, dialect: str, supported_dialects: Optional[list] = None):
        details = {"dialect": dialect}
        if supported_dialects:
            details["supported_dialects"] = supported_dialects
        
        super().__init__(
            message=f"Invalid SQL dialect: {dialect}",
            code=ErrorCode.INVALID_DIALECT,
            details=details,
            user_message=f"不支持的SQL方言: {dialect}。支持的方言: {', '.join(supported_dialects or [])}"
        )


class DocumentTooLargeException(LSPException):
    """Exception raised when document exceeds size limit."""
    
    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"Document size ({size} bytes) exceeds maximum ({max_size} bytes)",
            code=ErrorCode.DOCUMENT_TOO_LARGE,
            details={"size": size, "max_size": max_size},
            user_message=f"文档过大（{size // 1024}KB），最大支持{max_size // 1024}KB"
        )


class DocumentNotFoundException(LSPException):
    """Exception raised when document is not found."""
    
    def __init__(self, uri: str):
        super().__init__(
            message=f"Document not found: {uri}",
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            details={"uri": uri},
            user_message="文档不存在，请重新打开文档"
        )


class ValidationException(BaseAppException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details=error_details,
            user_message=f"输入验证失败: {message}"
        )


class InvalidPositionException(ValidationException):
    """Exception for invalid cursor position."""
    
    def __init__(self, line: int, character: int):
        super().__init__(
            message=f"Invalid position: line {line}, character {character}",
            field="position",
            details={"line": line, "character": character}
        )
        self.code = ErrorCode.INVALID_POSITION
        self.user_message = f"无效的光标位置: 第{line + 1}行, 第{character + 1}列"


class ConnectionLimitException(WebSocketException):
    """Exception when connection limit is reached."""
    
    def __init__(self, current_connections: int, max_connections: int):
        super().__init__(
            message=f"Connection limit reached: {current_connections}/{max_connections}",
            code=ErrorCode.WEBSOCKET_CONNECTION_LIMIT,
            details={"current": current_connections, "max": max_connections},
            user_message="服务器连接数已满，请稍后重试"
        )


class InternalServerException(BaseAppException):
    """Exception for internal server errors."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[dict] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INTERNAL_ERROR,
            details=details,
            user_message="服务器内部错误，请稍后重试"
        )


__all__ = [
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
