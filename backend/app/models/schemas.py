"""
Pydantic schemas for LSP protocol messages.
"""
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class DiagnosticSeverity(IntEnum):
    """LSP Diagnostic severity levels."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class CompletionItemKind(IntEnum):
    """LSP Completion item kinds."""
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18
    FOLDER = 19
    ENUM_MEMBER = 20
    CONSTANT = 21
    STRUCT = 22
    EVENT = 23
    OPERATOR = 24
    TYPE_PARAMETER = 25


class Position(BaseModel):
    """Position in a text document (0-indexed)."""
    line: int = Field(..., ge=0, description="Line number (0-indexed)")
    character: int = Field(..., ge=0, description="Character offset (0-indexed)")


class Range(BaseModel):
    """Range in a text document."""
    start: Position
    end: Position


class Diagnostic(BaseModel):
    """Represents a diagnostic (error, warning, etc.)."""
    range: Range
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    code: Optional[str] = None
    source: str = "sqlfluff"
    message: str


class TextDocumentItem(BaseModel):
    """Text document item for didOpen notification."""
    uri: str
    languageId: str = "sql"
    version: int = 1
    text: str


class TextDocumentContentChangeEvent(BaseModel):
    """Content change event for didChange notification."""
    text: str
    range: Optional[Range] = None


class CompletionItem(BaseModel):
    """Completion item for code completion."""
    label: str
    kind: CompletionItemKind = CompletionItemKind.KEYWORD
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insertText: Optional[str] = None
    sortText: Optional[str] = None


class LSPMessage(BaseModel):
    """Base LSP message structure."""
    jsonrpc: str = "2.0"


class LSPRequest(LSPMessage):
    """LSP request message."""
    id: Optional[Union[int, str]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class LSPResponse(LSPMessage):
    """LSP response message."""
    id: Optional[Union[int, str]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class DiagnosticsParams(BaseModel):
    """Parameters for publishDiagnostics notification."""
    uri: str
    diagnostics: List[Diagnostic]


class CompletionParams(BaseModel):
    """Parameters for completion request."""
    uri: str
    position: Position


class SetDialectParams(BaseModel):
    """Parameters for setDialect request."""
    dialect: str


# ==========================================
# SQL Explain (Execution Plan) Schemas
# ==========================================

class ExplainRequest(BaseModel):
    """Request body for POST /api/explain endpoint."""
    sql: str = Field(..., description="SQL text to analyze")
    dialect: str = Field(default="ansi", description="SQL dialect")


class ExplainNode(BaseModel):
    """
    A node in the SQL execution plan tree.

    This structure mirrors the TypeScript `ExplainNode` interface in the
    frontend so that backend and frontend stay in sync.
    """
    id: str = Field(..., description="Unique node identifier")
    operation: str = Field(..., description="Operation type, e.g. SELECT / JOIN / FILTER")
    table: Optional[str] = Field(default=None, description="Table name involved (if any)")
    estimated_rows: int = Field(..., ge=0, description="Estimated number of output rows")
    access_type: str = Field(
        ...,
        description="Access type: full_scan / index_scan / temp_table / const / ref / unknown"
    )
    cost: float = Field(..., ge=0.0, description="Estimated cost of this node")
    bottleneck: bool = Field(
        default=False,
        description="Whether this node is a performance bottleneck"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details such as join type / where condition / subquery info"
    )
    children: List["ExplainNode"] = Field(
        default_factory=list,
        description="Child nodes representing sub-operations"
    )


class ExplainResponse(BaseModel):
    """Response body for POST /api/explain endpoint."""
    success: bool = True
    dialect: str
    root: ExplainNode
    total_cost: float = Field(..., ge=0.0, description="Total estimated cost of the plan")
    warnings: List[str] = Field(default_factory=list, description="Performance warnings")


# Allow recursive ExplainNode model
ExplainNode.model_rebuild()


__all__ = [
    "Position",
    "Range",
    "Diagnostic",
    "DiagnosticSeverity",
    "TextDocumentItem",
    "TextDocumentContentChangeEvent",
    "CompletionItem",
    "CompletionItemKind",
    "LSPMessage",
    "LSPRequest",
    "LSPResponse",
    "DiagnosticsParams",
    "CompletionParams",
    "SetDialectParams",
    "ExplainRequest",
    "ExplainNode",
    "ExplainResponse",
]
