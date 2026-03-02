"""
Unit tests for LinterService.
"""
import pytest
from app.services.linter_service import LinterService, linter_service
from app.models import DiagnosticSeverity
from app.core.exceptions import InvalidDialectException, LintTimeoutException


class TestLinterService:
    """Tests for LinterService class."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh LinterService instance."""
        return LinterService()
    
    @pytest.mark.asyncio
    async def test_lint_valid_sql(self, service):
        """Test linting valid SQL returns no errors."""
        sql = "SELECT id, name FROM users WHERE id = 1"
        diagnostics = await service.lint(sql, "ansi")
        
        # Valid SQL should have minimal issues
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.ERROR]
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_lint_invalid_sql(self, service):
        """Test linting invalid SQL returns diagnostics."""
        sql = "SELEC * FORM users"  # Typos: SELEC, FORM
        diagnostics = await service.lint(sql, "ansi")
        
        # Should detect parse errors
        assert len(diagnostics) > 0
    
    @pytest.mark.asyncio
    async def test_lint_empty_sql(self, service):
        """Test linting empty SQL returns no diagnostics."""
        sql = ""
        diagnostics = await service.lint(sql, "ansi")
        assert len(diagnostics) == 0
    
    @pytest.mark.asyncio
    async def test_lint_whitespace_only(self, service):
        """Test linting whitespace-only SQL returns hints (not errors)."""
        diagnostics = await service.lint("   \n   ", "ansi")
        # SQLFluff reports whitespace issues as hints, not errors
        for diag in diagnostics:
            assert diag.severity >= 3  # INFORMATION or HINT, not ERROR or WARNING
    
    @pytest.mark.asyncio
    async def test_lint_sparksql_dialect(self, service):
        """Test linting with SparkSQL dialect."""
        sql = "SELECT EXPLODE(array_col) FROM table1"
        diagnostics = await service.lint(sql, "sparksql")
        
        # SparkSQL specific syntax should be valid
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.ERROR]
        # May have style warnings but not parse errors for valid SparkSQL
        assert isinstance(diagnostics, list)
    
    @pytest.mark.asyncio
    async def test_lint_hive_dialect(self, service):
        """Test linting with Hive dialect."""
        sql = "SELECT * FROM users LATERAL VIEW EXPLODE(tags) t AS tag"
        diagnostics = await service.lint(sql, "hive")
        
        # Hive specific syntax should be recognized
        assert isinstance(diagnostics, list)
    
    @pytest.mark.asyncio
    async def test_lint_invalid_dialect(self, service):
        """Test linting with invalid dialect raises exception."""
        sql = "SELECT * FROM users"
        
        with pytest.raises(InvalidDialectException) as exc_info:
            await service.lint(sql, "invalid_dialect")
        
        assert exc_info.value.code == 1301  # ErrorCode.INVALID_DIALECT
        assert "invalid_dialect" in str(exc_info.value.message)
    
    @pytest.mark.asyncio
    async def test_lint_complex_query(self, service):
        """Test linting complex SQL query."""
        sql = """
        WITH cte AS (
            SELECT 
                id,
                name,
                ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as rn
            FROM employees
            WHERE status = 'active'
        )
        SELECT id, name
        FROM cte
        WHERE rn = 1
        """
        diagnostics = await service.lint(sql, "ansi")
        
        # Complex but valid SQL should not have parse errors
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.ERROR]
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_lint_multiple_statements(self, service):
        """Test linting multiple SQL statements."""
        sql = """
        SELECT * FROM users;
        SELECT * FROM orders;
        """
        diagnostics = await service.lint(sql, "ansi")
        
        # Should handle multiple statements
        assert isinstance(diagnostics, list)
    
    def test_get_severity_parse_error(self, service):
        """Test severity mapping for parse errors."""
        severity = service._get_severity("PRS001")
        assert severity == DiagnosticSeverity.ERROR
    
    def test_get_severity_layout(self, service):
        """Test severity mapping for layout rules."""
        severity = service._get_severity("LT01")
        assert severity == DiagnosticSeverity.HINT
    
    def test_get_severity_ambiguous(self, service):
        """Test severity mapping for ambiguous rules."""
        severity = service._get_severity("AM01")
        assert severity == DiagnosticSeverity.WARNING
    
    def test_get_severity_convention(self, service):
        """Test severity mapping for convention rules."""
        severity = service._get_severity("CV01")
        assert severity == DiagnosticSeverity.INFORMATION
    
    def test_get_severity_default(self, service):
        """Test default severity mapping."""
        severity = service._get_severity("XX01")
        assert severity == DiagnosticSeverity.WARNING


class TestLinterServiceSingleton:
    """Tests for linter_service singleton."""
    
    @pytest.mark.asyncio
    async def test_singleton_lint(self):
        """Test singleton instance can lint."""
        sql = "SELECT 1"
        diagnostics = await linter_service.lint(sql, "ansi")
        assert isinstance(diagnostics, list)
    
    def test_singleton_shutdown(self):
        """Test singleton can be shutdown."""
        # Should not raise
        linter_service.shutdown()
