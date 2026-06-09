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


class ExplainRequest(BaseModel):
    """Request body for SQL EXPLAIN endpoint."""
    sql: str = Field(..., min_length=1, description="SQL text to explain")
    dialect: str = Field(default="ansi", description="SQL dialect")


class AccessType(str):
    """SQL access type constants."""
    FULL_TABLE_SCAN = "full_table_scan"
    INDEX_SCAN = "index_scan"
    INDEX_SEEK = "index_seek"
    TEMPORARY_TABLE = "temporary_table"
    HASH_JOIN = "hash_join"
    NESTED_LOOP = "nested_loop"
    MERGE_JOIN = "merge_join"
    SORT = "sort"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    SUBQUERY = "subquery"
    TABLE_SCAN = "table_scan"


class ExplainNode(BaseModel):
    """Single node in the execution plan tree."""
    id: str = Field(..., description="Unique node identifier")
    operation_type: str = Field(..., description="Operation type (e.g., full_table_scan, index_scan)")
    table_name: Optional[str] = Field(default=None, description="Table name if applicable")
    estimated_rows: int = Field(default=0, ge=0, description="Estimated number of rows")
    access_type: str = Field(..., description="Access type (e.g., full_table_scan, index_scan, temporary_table)")
    cost: float = Field(default=0.0, ge=0.0, description="Estimated cost")
    details: Optional[str] = Field(default=None, description="Additional details about the operation")
    children: List["ExplainNode"] = Field(default_factory=list, description="Child nodes")


class ExplainResponse(BaseModel):
    """Response for SQL EXPLAIN endpoint."""
    success: bool = Field(..., description="Whether the explain was successful")
    root: Optional[ExplainNode] = Field(default=None, description="Root node of the execution plan tree")
    error: Optional[str] = Field(default=None, description="Error message if explain failed")


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
