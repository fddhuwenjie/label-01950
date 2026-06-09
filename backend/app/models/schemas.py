"""
Pydantic schemas for LSP protocol messages and SQL execution plan.
"""
from enum import IntEnum, Enum
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


class AccessType(str, Enum):
    """Table access type for execution plan nodes."""
    FULL_SCAN = "ALL"
    INDEX_SCAN = "index"
    RANGE_SCAN = "range"
    REF = "ref"
    EQ_REF = "eq_ref"
    CONST = "const"
    SYSTEM = "system"
    UNIQUE_SUBQUERY = "unique_subquery"
    INDEX_SUBQUERY = "index_subquery"


class NodeType(str, Enum):
    """Execution plan node operation types."""
    SELECT = "SELECT"
    JOIN = "JOIN"
    TABLE_SCAN = "TABLE_SCAN"
    INDEX_SCAN = "INDEX_SCAN"
    WHERE = "WHERE"
    GROUP_BY = "GROUP_BY"
    ORDER_BY = "ORDER_BY"
    HAVING = "HAVING"
    LIMIT = "LIMIT"
    SUBQUERY = "SUBQUERY"
    DERIVED = "DERIVED"
    TEMPORARY_TABLE = "TEMPORARY_TABLE"
    NESTED_LOOP = "NESTED_LOOP"
    HASH_JOIN = "HASH_JOIN"
    MERGE_JOIN = "MERGE_JOIN"
    AGGREGATE = "AGGREGATE"
    SORT = "SORT"
    DISTINCT = "DISTINCT"
    UNION = "UNION"


class BottleneckLevel(str, Enum):
    """Performance bottleneck severity level."""
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


class ExplainRequest(BaseModel):
    """Request body for /api/explain endpoint."""
    sql: str = Field(..., min_length=1, description="SQL text to analyze")
    dialect: str = Field(default="ansi", description="SQL dialect (ansi, sparksql, hive, etc.)")


class ExecutionPlanNode(BaseModel):
    """A single node in the SQL execution plan tree."""
    id: str = Field(..., description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of operation")
    operation_type: str = Field(..., description="Human-readable operation type")
    table_name: Optional[str] = Field(None, description="Name of the table being accessed")
    access_type: Optional[AccessType] = Field(None, description="Table access type")
    estimated_rows: int = Field(default=1, ge=0, description="Estimated number of rows")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Estimated cost")
    bottleneck: BottleneckLevel = Field(default=BottleneckLevel.NONE, description="Performance bottleneck level")
    description: str = Field(default="", description="Human-readable description of this node")
    children: List["ExecutionPlanNode"] = Field(default_factory=list, description="Child nodes")
    extra_info: Dict[str, Any] = Field(default_factory=dict, description="Additional node information")


class ExplainResponse(BaseModel):
    """Response from /api/explain endpoint."""
    success: bool = Field(default=True)
    dialect: str = Field(..., description="SQL dialect used for analysis")
    plan_tree: ExecutionPlanNode = Field(..., description="Root of the execution plan tree")
    total_cost: float = Field(default=0.0, ge=0.0, description="Total estimated cost")
    warnings: List[str] = Field(default_factory=list, description="Performance warnings")
    sql_valid: bool = Field(default=True, description="Whether SQL passed syntax validation")
    validation_errors: List[str] = Field(default_factory=list, description="Syntax validation errors if any")


ExecutionPlanNode.model_rebuild()


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
    "AccessType",
    "NodeType",
    "BottleneckLevel",
    "ExplainRequest",
    "ExecutionPlanNode",
    "ExplainResponse",
]
