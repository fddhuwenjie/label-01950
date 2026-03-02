"""
Tests for exception handling and error messages.
Verifies all exceptions return user-friendly messages.
"""
import pytest

from app.core.exceptions import (
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


class TestErrorCode:
    """Tests for ErrorCode enum."""
    
    def test_error_codes_are_unique(self):
        """Test all error codes are unique."""
        codes = [code.value for code in ErrorCode]
        assert len(codes) == len(set(codes))
    
    def test_error_codes_are_integers(self):
        """Test all error codes are integers."""
        for code in ErrorCode:
            assert isinstance(code.value, int)
    
    def test_websocket_errors_in_range(self):
        """Test WebSocket error codes are in 1001-1099 range."""
        ws_codes = [
            ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            ErrorCode.WEBSOCKET_SEND_FAILED,
            ErrorCode.WEBSOCKET_RECEIVE_FAILED,
            ErrorCode.WEBSOCKET_CONNECTION_LIMIT,
        ]
        for code in ws_codes:
            assert 1001 <= code.value <= 1099
    
    def test_lsp_errors_in_range(self):
        """Test LSP error codes are in 1101-1199 range."""
        lsp_codes = [
            ErrorCode.LSP_SERVICE_UNAVAILABLE,
            ErrorCode.LSP_INVALID_REQUEST,
            ErrorCode.LSP_METHOD_NOT_FOUND,
            ErrorCode.LSP_INVALID_PARAMS,
        ]
        for code in lsp_codes:
            assert 1101 <= code.value <= 1199
    
    def test_lint_errors_in_range(self):
        """Test Lint error codes are in 1201-1299 range."""
        lint_codes = [
            ErrorCode.LINT_TIMEOUT,
            ErrorCode.LINT_PARSE_ERROR,
            ErrorCode.LINT_INTERNAL_ERROR,
        ]
        for code in lint_codes:
            assert 1201 <= code.value <= 1299


class TestErrorMessages:
    """Tests for error message mapping."""
    
    def test_all_error_codes_have_messages(self):
        """Test all error codes have corresponding messages."""
        for code in ErrorCode:
            assert code.value in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[code.value]) > 0
    
    def test_messages_are_user_friendly(self):
        """Test error messages are user-friendly (Chinese)."""
        for code, message in ERROR_MESSAGES.items():
            # Messages should not contain technical terms
            assert "exception" not in message.lower()
            assert "error:" not in message.lower()
            assert "traceback" not in message.lower()
            # Messages should be in Chinese or user-friendly
            assert len(message) > 0
    
    def test_get_error_message_returns_correct_message(self):
        """Test get_error_message returns correct message."""
        message = get_error_message(ErrorCode.LINT_TIMEOUT)
        assert message == ERROR_MESSAGES[ErrorCode.LINT_TIMEOUT]
    
    def test_get_error_message_returns_default_for_unknown(self):
        """Test get_error_message returns default for unknown code."""
        message = get_error_message(99999, "默认错误")
        assert message == "默认错误"


class TestBaseAppException:
    """Tests for BaseAppException."""
    
    def test_exception_has_required_attributes(self):
        """Test exception has all required attributes."""
        exc = BaseAppException(
            message="Test error",
            code=ErrorCode.UNKNOWN_ERROR,
            details={"key": "value"},
            user_message="用户友好消息"
        )
        
        assert exc.message == "Test error"
        assert exc.code == ErrorCode.UNKNOWN_ERROR
        assert exc.details == {"key": "value"}
        assert exc.user_message == "用户友好消息"
    
    def test_exception_uses_default_message(self):
        """Test exception uses default message when not provided."""
        exc = BaseAppException(code=ErrorCode.INTERNAL_ERROR)
        
        assert exc.message == ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR]
        assert exc.user_message == ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR]
    
    def test_to_dict_returns_correct_structure(self):
        """Test to_dict returns correct structure."""
        exc = BaseAppException(
            message="Test error",
            code=1234,
            details={"field": "value"},
            user_message="友好消息"
        )
        
        result = exc.to_dict()
        
        assert result["success"] is False
        assert result["error"]["code"] == 1234
        assert result["error"]["message"] == "友好消息"
        assert result["error"]["details"] == {"field": "value"}
    
    def test_exception_is_raisable(self):
        """Test exception can be raised and caught."""
        with pytest.raises(BaseAppException) as exc_info:
            raise BaseAppException(message="Test", code=1000)
        
        assert exc_info.value.message == "Test"
        assert exc_info.value.code == 1000


class TestLSPException:
    """Tests for LSPException."""
    
    def test_default_code(self):
        """Test LSPException has correct default code."""
        exc = LSPException()
        assert exc.code == ErrorCode.LSP_SERVICE_UNAVAILABLE
    
    def test_inherits_from_base(self):
        """Test LSPException inherits from BaseAppException."""
        exc = LSPException()
        assert isinstance(exc, BaseAppException)
    
    def test_custom_message(self):
        """Test LSPException with custom message."""
        exc = LSPException(
            message="Custom LSP error",
            user_message="自定义LSP错误"
        )
        assert exc.message == "Custom LSP error"
        assert exc.user_message == "自定义LSP错误"


class TestLintTimeoutException:
    """Tests for LintTimeoutException."""
    
    def test_default_message(self):
        """Test LintTimeoutException has default message."""
        exc = LintTimeoutException()
        assert exc.code == ErrorCode.LINT_TIMEOUT
        assert "超时" in exc.user_message
    
    def test_with_timeout_seconds(self):
        """Test LintTimeoutException with timeout value."""
        exc = LintTimeoutException(timeout_seconds=5.0)
        assert exc.details["timeout_seconds"] == 5.0
        assert "5.0" in exc.message
    
    def test_user_message_is_friendly(self):
        """Test user message is friendly."""
        exc = LintTimeoutException()
        assert "SQL分析超时" in exc.user_message
        assert "请" in exc.user_message  # Contains suggestion


class TestInvalidDialectException:
    """Tests for InvalidDialectException."""
    
    def test_includes_dialect_in_message(self):
        """Test exception includes dialect in message."""
        exc = InvalidDialectException("mysql")
        assert "mysql" in exc.message
        assert "mysql" in exc.user_message
    
    def test_includes_supported_dialects(self):
        """Test exception includes supported dialects."""
        exc = InvalidDialectException("mysql", ["ansi", "sparksql", "hive"])
        assert exc.details["supported_dialects"] == ["ansi", "sparksql", "hive"]
        assert "ansi" in exc.user_message
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = InvalidDialectException("mysql")
        assert exc.code == ErrorCode.INVALID_DIALECT


class TestDocumentTooLargeException:
    """Tests for DocumentTooLargeException."""
    
    def test_includes_sizes(self):
        """Test exception includes document sizes."""
        exc = DocumentTooLargeException(size=2048000, max_size=1024000)
        
        assert exc.details["size"] == 2048000
        assert exc.details["max_size"] == 1024000
    
    def test_user_message_shows_kb(self):
        """Test user message shows sizes in KB."""
        exc = DocumentTooLargeException(size=2048000, max_size=1024000)
        
        # Should show KB, not bytes
        assert "KB" in exc.user_message or "kb" in exc.user_message.lower()
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = DocumentTooLargeException(size=2048000, max_size=1024000)
        assert exc.code == ErrorCode.DOCUMENT_TOO_LARGE


class TestDocumentNotFoundException:
    """Tests for DocumentNotFoundException."""
    
    def test_includes_uri(self):
        """Test exception includes document URI."""
        exc = DocumentNotFoundException("file:///test.sql")
        
        assert exc.details["uri"] == "file:///test.sql"
        assert "file:///test.sql" in exc.message
    
    def test_user_message_is_friendly(self):
        """Test user message is friendly."""
        exc = DocumentNotFoundException("file:///test.sql")
        
        assert "文档不存在" in exc.user_message
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = DocumentNotFoundException("file:///test.sql")
        assert exc.code == ErrorCode.DOCUMENT_NOT_FOUND


class TestValidationException:
    """Tests for ValidationException."""
    
    def test_includes_field(self):
        """Test exception includes field name."""
        exc = ValidationException(message="Invalid value", field="username")
        
        assert exc.details["field"] == "username"
    
    def test_user_message_includes_reason(self):
        """Test user message includes validation reason."""
        exc = ValidationException(message="Value too long")
        
        assert "Value too long" in exc.user_message
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = ValidationException(message="Invalid")
        assert exc.code == ErrorCode.VALIDATION_ERROR


class TestInvalidPositionException:
    """Tests for InvalidPositionException."""
    
    def test_includes_position(self):
        """Test exception includes line and character."""
        exc = InvalidPositionException(line=5, character=10)
        
        assert exc.details["line"] == 5
        assert exc.details["character"] == 10
    
    def test_user_message_shows_1_indexed(self):
        """Test user message shows 1-indexed position."""
        exc = InvalidPositionException(line=5, character=10)
        
        # Should show line 6, column 11 (1-indexed)
        assert "6" in exc.user_message
        assert "11" in exc.user_message
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = InvalidPositionException(line=0, character=0)
        assert exc.code == ErrorCode.INVALID_POSITION


class TestConnectionLimitException:
    """Tests for ConnectionLimitException."""
    
    def test_includes_connection_counts(self):
        """Test exception includes connection counts."""
        exc = ConnectionLimitException(current_connections=100, max_connections=100)
        
        assert exc.details["current"] == 100
        assert exc.details["max"] == 100
    
    def test_user_message_is_friendly(self):
        """Test user message is friendly."""
        exc = ConnectionLimitException(current_connections=100, max_connections=100)
        
        assert "连接" in exc.user_message
        assert "稍后" in exc.user_message
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = ConnectionLimitException(current_connections=100, max_connections=100)
        assert exc.code == ErrorCode.WEBSOCKET_CONNECTION_LIMIT


class TestInternalServerException:
    """Tests for InternalServerException."""
    
    def test_default_message(self):
        """Test exception has default message."""
        exc = InternalServerException()
        
        assert exc.message == "Internal server error"
    
    def test_user_message_is_friendly(self):
        """Test user message is friendly."""
        exc = InternalServerException()
        
        assert "服务器内部错误" in exc.user_message
        assert "稍后" in exc.user_message
    
    def test_with_details(self):
        """Test exception with details."""
        exc = InternalServerException(
            message="Database connection failed",
            details={"db": "mysql"}
        )
        
        assert exc.details["db"] == "mysql"
    
    def test_error_code(self):
        """Test exception has correct error code."""
        exc = InternalServerException()
        assert exc.code == ErrorCode.INTERNAL_ERROR
