"""
Pydantic schemas for LSP protocol messages and execution plan.
"""
from enum import IntEnum, Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ExplainNodeType(str, Enum):
    """Types of execution plan nodes."""
    SELECT = "SELECT"
    FROM = "FROM"
    JOIN = "JOIN"
    WHERE = "WHERE"
    GROUP_BY = "GROUP_BY"
    ORDER_BY = "ORDER_BY"
    LIMIT = "LIMIT"
    SUBQUERY = "SUBQUERY"
    TABLE_SCAN = "TABLE_SCAN"
    INDEX_SCAN = "INDEX_SCAN"
    TEMP_TABLE = "TEMP_TABLE"
    SORT = "SORT"
    AGGREGATE = "AGGREGATE"
    HASH_JOIN = "HASH_JOIN"
    NESTED_LOOP_JOIN = "NESTED_LOOP_JOIN"
    MERGE_JOIN = "MERGE_JOIN"


class ExplainRequest(BaseModel):
    """Request body for SQL explain endpoint."""
    sql: str = Field(..., description="SQL statement to explain")
    dialect: str = Field(default="ansi", description="SQL dialect")


class ExplainPlanNode(BaseModel):
    """Node in the execution plan tree."""
    id: str = Field(..., description="Unique node identifier")
    operation_type: ExplainNodeType = Field(..., description="Type of operation")
    table_name: Optional[str] = Field(None, description="Table name if applicable")
    estimated_rows: int = Field(..., description="Estimated number of rows")
    access_type: Optional[str] = Field(None, description="Access type (full scan, index, etc.)")
    cost: float = Field(..., description="Estimated cost")
    description: str = Field(..., description="Human-readable description")
    is_bottleneck: bool = Field(default=False, description="Whether this node is a performance bottleneck")
    bottleneck_reason: Optional[str] = Field(None, description="Reason for being a bottleneck")
    children: List["ExplainPlanNode"] = Field(default_factory=list, description="Child nodes")


class ExplainResponse(BaseModel):
    """Response containing execution plan."""
    success: bool = True
    plan: ExplainPlanNode
    total_cost: float
    total_estimated_rows: int
    has_bottlenecks: bool
    bottleneck_count: int


ExplainPlanNode.model_rebuild()


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
    "ExplainNodeType",
    "ExplainRequest",
    "ExplainPlanNode",
    "ExplainResponse",
]
