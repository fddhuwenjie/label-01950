"""
SQLFluff linter service for SQL syntax checking.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from sqlfluff.core import Linter
from sqlfluff.core.config import FluffConfig

from ..config import settings
from ..core import logger, LintTimeoutException, InvalidDialectException
from ..models import Diagnostic, DiagnosticSeverity, Position, Range


class LinterService:
    """Service for SQL linting using SQLFluff."""
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._linters: dict = {}
        logger.info("LinterService initialized")
    
    def _get_linter(self, dialect: str) -> Linter:
        """
        Get or create a linter instance for the specified dialect.
        
        Args:
            dialect: SQL dialect name.
            
        Returns:
            Configured Linter instance.
            
        Raises:
            InvalidDialectException: If dialect is not supported.
        """
        if dialect not in settings.SUPPORTED_DIALECTS:
            raise InvalidDialectException(dialect)
        
        if dialect not in self._linters:
            config = FluffConfig.from_kwargs(dialect=dialect)
            self._linters[dialect] = Linter(config=config)
            logger.debug(f"Created linter for dialect: {dialect}")
        
        return self._linters[dialect]
    
    def _lint_sync(self, sql: str, dialect: str) -> List[Diagnostic]:
        """
        Synchronously lint SQL code.
        
        Args:
            sql: SQL code to lint.
            dialect: SQL dialect.
            
        Returns:
            List of diagnostics.
        """
        linter = self._get_linter(dialect)
        result = linter.lint_string(sql)
        
        diagnostics: List[Diagnostic] = []
        
        for violation in result.violations:
            # SQLFluff uses 1-indexed lines, LSP uses 0-indexed
            line = max(0, violation.line_no - 1)
            char = max(0, violation.line_pos - 1)
            
            # Determine severity based on rule code
            severity = self._get_severity(violation.rule_code())
            
            diagnostic = Diagnostic(
                range=Range(
                    start=Position(line=line, character=char),
                    end=Position(line=line, character=char + 1)
                ),
                severity=severity,
                code=violation.rule_code(),
                source="sqlfluff",
                message=violation.desc()
            )
            diagnostics.append(diagnostic)
        
        return diagnostics
    
    def _get_severity(self, rule_code: str) -> DiagnosticSeverity:
        """
        Map SQLFluff rule code to diagnostic severity.
        
        Args:
            rule_code: SQLFluff rule code.
            
        Returns:
            Diagnostic severity level.
        """
        # Parse errors are always errors
        if rule_code.startswith("PRS"):
            return DiagnosticSeverity.ERROR
        
        # Layout rules are hints
        if rule_code.startswith("LT"):
            return DiagnosticSeverity.HINT
        
        # Ambiguous rules are warnings
        if rule_code.startswith("AM"):
            return DiagnosticSeverity.WARNING
        
        # Convention rules are information
        if rule_code.startswith("CV"):
            return DiagnosticSeverity.INFORMATION
        
        # Default to warning
        return DiagnosticSeverity.WARNING
    
    async def lint(
        self,
        sql: str,
        dialect: str = "ansi",
        timeout: Optional[float] = None
    ) -> List[Diagnostic]:
        """
        Asynchronously lint SQL code.
        
        Args:
            sql: SQL code to lint.
            dialect: SQL dialect (default: ansi).
            timeout: Timeout in seconds (default: from settings).
            
        Returns:
            List of diagnostics.
            
        Raises:
            LintTimeoutException: If linting times out.
            InvalidDialectException: If dialect is not supported.
        """
        if timeout is None:
            timeout = settings.LINT_TIMEOUT
        
        logger.debug(f"Linting SQL with dialect: {dialect}")
        
        loop = asyncio.get_event_loop()
        
        try:
            diagnostics = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    self._lint_sync,
                    sql,
                    dialect
                ),
                timeout=timeout
            )
            
            logger.debug(f"Linting completed, found {len(diagnostics)} issues")
            return diagnostics
            
        except asyncio.TimeoutError:
            logger.warning(f"Linting timed out after {timeout}s")
            raise LintTimeoutException()
    
    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)
        logger.info("LinterService shutdown")


# Singleton instance
linter_service = LinterService()


__all__ = ["LinterService", "linter_service"]
