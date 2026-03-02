"""
LSP Service orchestrating linting and completion.
"""
import asyncio
from typing import Any, Dict, List, Optional

from ..config import settings
from ..core import logger, InvalidDialectException
from ..models import (
    Diagnostic,
    CompletionItem,
    LSPRequest,
    LSPResponse,
    DiagnosticsParams,
)
from .linter_service import linter_service
from .completion_service import completion_service


class LSPService:
    """
    Main LSP service that coordinates linting and completion.
    """
    
    def __init__(self):
        self._documents: Dict[str, str] = {}
        self._dialects: Dict[str, str] = {}
        self._pending_lint: Dict[str, asyncio.Task] = {}
        logger.info("LSPService initialized")
    
    def get_dialect(self, uri: str) -> str:
        """Get dialect for a document."""
        return self._dialects.get(uri, settings.DEFAULT_DIALECT)
    
    def set_dialect(self, uri: str, dialect: str) -> None:
        """
        Set dialect for a document.
        
        Args:
            uri: Document URI.
            dialect: SQL dialect.
            
        Raises:
            InvalidDialectException: If dialect is not supported.
        """
        if dialect not in settings.SUPPORTED_DIALECTS:
            raise InvalidDialectException(dialect)
        
        self._dialects[uri] = dialect
        logger.info(f"Set dialect for {uri}: {dialect}")
    
    async def handle_did_open(
        self,
        uri: str,
        text: str,
        language_id: str = "sql"
    ) -> List[Diagnostic]:
        """
        Handle textDocument/didOpen notification.
        
        Args:
            uri: Document URI.
            text: Document content.
            language_id: Language identifier.
            
        Returns:
            List of diagnostics.
        """
        self._documents[uri] = text
        logger.info(f"Document opened: {uri}")
        
        return await self._lint_document(uri)
    
    async def handle_did_change(
        self,
        uri: str,
        text: str
    ) -> List[Diagnostic]:
        """
        Handle textDocument/didChange notification.
        
        Args:
            uri: Document URI.
            text: New document content.
            
        Returns:
            List of diagnostics.
        """
        self._documents[uri] = text
        
        # Cancel pending lint task for this document
        if uri in self._pending_lint:
            self._pending_lint[uri].cancel()
        
        return await self._lint_document(uri)
    
    async def handle_did_close(self, uri: str) -> None:
        """
        Handle textDocument/didClose notification.
        
        Args:
            uri: Document URI.
        """
        self._documents.pop(uri, None)
        self._dialects.pop(uri, None)
        
        if uri in self._pending_lint:
            self._pending_lint[uri].cancel()
            del self._pending_lint[uri]
        
        logger.info(f"Document closed: {uri}")
    
    async def handle_completion(
        self,
        uri: str,
        line: int,
        character: int
    ) -> List[CompletionItem]:
        """
        Handle textDocument/completion request.
        
        Args:
            uri: Document URI.
            line: Line number (0-indexed).
            character: Character position (0-indexed).
            
        Returns:
            List of completion items.
        """
        text = self._documents.get(uri, "")
        dialect = self.get_dialect(uri)
        
        return completion_service.get_completions(text, line, character, dialect)
    
    async def _lint_document(self, uri: str) -> List[Diagnostic]:
        """
        Lint a document and return diagnostics.
        
        Args:
            uri: Document URI.
            
        Returns:
            List of diagnostics.
        """
        text = self._documents.get(uri, "")
        if not text.strip():
            return []
        
        dialect = self.get_dialect(uri)
        
        try:
            diagnostics = await linter_service.lint(text, dialect)
            logger.debug(f"Lint completed for {uri}: {len(diagnostics)} issues")
            return diagnostics
        except Exception as e:
            logger.error(f"Lint failed for {uri}: {e}")
            return []
    
    async def process_request(self, request: LSPRequest) -> Optional[LSPResponse]:
        """
        Process an LSP request and return response.
        
        Args:
            request: LSP request message.
            
        Returns:
            LSP response or None for notifications.
        """
        method = request.method
        params = request.params or {}
        
        logger.debug(f"Processing LSP request: {method}")
        
        try:
            if method == "textDocument/didOpen":
                uri = params.get("textDocument", {}).get("uri", "")
                text = params.get("textDocument", {}).get("text", "")
                language_id = params.get("textDocument", {}).get("languageId", "sql")
                
                diagnostics = await self.handle_did_open(uri, text, language_id)
                
                return LSPResponse(
                    id=request.id,
                    result=DiagnosticsParams(uri=uri, diagnostics=diagnostics).model_dump()
                )
            
            elif method == "textDocument/didChange":
                uri = params.get("textDocument", {}).get("uri", "")
                changes = params.get("contentChanges", [])
                text = changes[0].get("text", "") if changes else ""
                
                diagnostics = await self.handle_did_change(uri, text)
                
                return LSPResponse(
                    id=request.id,
                    result=DiagnosticsParams(uri=uri, diagnostics=diagnostics).model_dump()
                )
            
            elif method == "textDocument/didClose":
                uri = params.get("textDocument", {}).get("uri", "")
                await self.handle_did_close(uri)
                return None
            
            elif method == "textDocument/completion":
                uri = params.get("textDocument", {}).get("uri", "")
                position = params.get("position", {})
                line = position.get("line", 0)
                character = position.get("character", 0)
                
                items = await self.handle_completion(uri, line, character)
                
                return LSPResponse(
                    id=request.id,
                    result={"items": [item.model_dump() for item in items]}
                )
            
            elif method == "setDialect":
                uri = params.get("uri", "file:///editor.sql")
                dialect = params.get("dialect", settings.DEFAULT_DIALECT)
                
                self.set_dialect(uri, dialect)
                
                # Re-lint with new dialect
                diagnostics = await self._lint_document(uri)
                
                return LSPResponse(
                    id=request.id,
                    result={
                        "success": True,
                        "dialect": dialect,
                        "uri": uri,
                        "diagnostics": [d.model_dump() for d in diagnostics]
                    }
                )
            
            else:
                logger.warning(f"Unknown LSP method: {method}")
                return LSPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Method not found: {method}"}
                )
        
        except InvalidDialectException as e:
            return LSPResponse(
                id=request.id,
                error={"code": e.code, "message": e.message}
            )
        except Exception as e:
            logger.exception(f"Error processing request: {e}")
            return LSPResponse(
                id=request.id,
                error={"code": -32603, "message": str(e)}
            )


# Singleton instance
lsp_service = LSPService()


__all__ = ["LSPService", "lsp_service"]
