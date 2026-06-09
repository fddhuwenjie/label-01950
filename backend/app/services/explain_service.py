"""
SQL Explain (execution plan) service.

Validates SQL syntax via SQLFluff's Linter, then walks the parsed AST to
build a mocked execution-plan tree (no real database connection required).
"""
import asyncio
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from sqlfluff.core import Linter
from sqlfluff.core.config import FluffConfig

from ..config import settings
from ..core import (
    logger,
    InvalidDialectException,
    LintTimeoutException,
    LSPException,
    ErrorCode,
)
from ..models import ExplainNode, ExplainResponse


# Heuristic constants for the mocked cost model.
DEFAULT_TABLE_ROWS = 10000
JOIN_COST_MULTIPLIER = 1.5
SUBQUERY_COST_MULTIPLIER = 2.0
WHERE_SELECTIVITY = 0.3
GROUP_BY_REDUCTION = 0.2
DISTINCT_REDUCTION = 0.5
LIMIT_DEFAULT = 100


class ExplainService:
    """Service producing a mocked SQL execution plan via AST analysis."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._linters: Dict[str, Linter] = {}
        logger.info("ExplainService initialized")

    # ------------------------------------------------------------------
    # Linter helpers
    # ------------------------------------------------------------------
    def _get_linter(self, dialect: str) -> Linter:
        if dialect not in settings.SUPPORTED_DIALECTS:
            raise InvalidDialectException(dialect, settings.SUPPORTED_DIALECTS)

        if dialect not in self._linters:
            config = FluffConfig.from_kwargs(dialect=dialect)
            self._linters[dialect] = Linter(config=config)
            logger.debug(f"Created explain linter for dialect: {dialect}")
        return self._linters[dialect]

    # ------------------------------------------------------------------
    # AST helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _new_id() -> str:
        return f"n_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _segments_of_type(segment: Any, type_name: str) -> List[Any]:
        """Recursively collect all child segments of a given type."""
        out: List[Any] = []
        if segment is None:
            return out
        children = getattr(segment, "segments", None) or []
        for child in children:
            if getattr(child, "type", None) == type_name:
                out.append(child)
            out.extend(ExplainService._segments_of_type(child, type_name))
        return out

    @staticmethod
    def _direct_children_of_type(segment: Any, type_name: str) -> List[Any]:
        """Direct children only, of given type."""
        out: List[Any] = []
        children = getattr(segment, "segments", None) or []
        for child in children:
            if getattr(child, "type", None) == type_name:
                out.append(child)
        return out

    @staticmethod
    def _raw(segment: Any) -> str:
        if segment is None:
            return ""
        raw = getattr(segment, "raw", None)
        return raw if isinstance(raw, str) else str(segment)

    # ------------------------------------------------------------------
    # Plan construction
    # ------------------------------------------------------------------
    def _classify_access_type(
        self,
        table_name: str,
        where_text: str,
    ) -> str:
        """
        Classify access type based on heuristics:
        - Looks like indexed column in WHERE => index_scan
        - Looks like temp/derived alias => temp_table
        - Otherwise => full_scan
        """
        if not table_name:
            return "unknown"

        # Temp/derived table heuristic: name starts with 'tmp', 'temp' or '__'
        lowered = table_name.lower()
        if lowered.startswith(("tmp_", "temp_", "__", "cte_")):
            return "temp_table"

        if where_text:
            # Heuristic: if WHERE references id / pk / *_id columns, assume index_scan
            if re.search(r"\b(id|pk|[a-z_]+_id)\s*(=|in|>|<|>=|<=)", where_text, re.IGNORECASE):
                return "index_scan"

        return "full_scan"

    def _build_table_node(
        self,
        table_segment: Any,
        where_text: str,
    ) -> ExplainNode:
        raw = self._raw(table_segment).strip()
        # Strip alias if any (e.g. "users u")
        table_name = raw.split()[0] if raw else "unknown"

        access_type = self._classify_access_type(table_name, where_text)
        if access_type == "full_scan":
            estimated_rows = DEFAULT_TABLE_ROWS
            cost = float(estimated_rows)
        elif access_type == "index_scan":
            estimated_rows = max(1, int(DEFAULT_TABLE_ROWS * 0.05))
            cost = float(estimated_rows) * 0.5
        elif access_type == "temp_table":
            estimated_rows = max(1, int(DEFAULT_TABLE_ROWS * 0.1))
            cost = float(estimated_rows) * 1.2
        else:
            estimated_rows = DEFAULT_TABLE_ROWS
            cost = float(estimated_rows)

        bottleneck = access_type in ("full_scan", "temp_table")

        return ExplainNode(
            id=self._new_id(),
            operation="TABLE_SCAN",
            table=table_name,
            estimated_rows=estimated_rows,
            access_type=access_type,
            cost=cost,
            bottleneck=bottleneck,
            details={"raw": raw},
            children=[],
        )

    def _build_join_chain(
        self,
        from_clause: Any,
        where_text: str,
    ) -> Optional[ExplainNode]:
        """
        Build a JOIN chain from a from_clause. The first table becomes the
        leftmost leaf; each subsequent join wraps it.
        """
        if from_clause is None:
            return None

        # First table reference (the "from" base table)
        base_tables = self._segments_of_type(from_clause, "from_expression_element")
        if not base_tables:
            return None

        base_node = self._build_table_node(base_tables[0], where_text)
        current: ExplainNode = base_node

        # Each join_clause adds one JOIN above the current root
        join_clauses = self._segments_of_type(from_clause, "join_clause")
        for join in join_clauses:
            join_text = self._raw(join)
            # Determine join type
            join_type = "INNER"
            jt = join_text.upper()
            if "LEFT" in jt:
                join_type = "LEFT"
            elif "RIGHT" in jt:
                join_type = "RIGHT"
            elif "FULL" in jt:
                join_type = "FULL"
            elif "CROSS" in jt:
                join_type = "CROSS"

            # Right-side table of this join
            right_tables = self._segments_of_type(join, "from_expression_element")
            if not right_tables:
                continue
            right_node = self._build_table_node(right_tables[0], where_text)

            combined_rows = max(
                1,
                int(current.estimated_rows * right_node.estimated_rows / DEFAULT_TABLE_ROWS),
            )
            join_cost = (current.cost + right_node.cost) * JOIN_COST_MULTIPLIER

            join_node = ExplainNode(
                id=self._new_id(),
                operation=f"JOIN ({join_type})",
                table=None,
                estimated_rows=combined_rows,
                access_type="ref" if join_type != "CROSS" else "full_scan",
                cost=join_cost,
                bottleneck=join_type == "CROSS",
                details={"join_type": join_type, "raw": join_text.strip()[:120]},
                children=[current, right_node],
            )
            current = join_node

        return current

    def _wrap_with_filter(
        self,
        child: ExplainNode,
        where_clause: Any,
    ) -> ExplainNode:
        where_text = self._raw(where_clause)
        rows = max(1, int(child.estimated_rows * WHERE_SELECTIVITY))
        cost = child.cost + child.estimated_rows  # cost of evaluating predicate

        return ExplainNode(
            id=self._new_id(),
            operation="FILTER",
            table=None,
            estimated_rows=rows,
            access_type="ref",
            cost=cost,
            bottleneck=False,
            details={"condition": where_text.strip()[:200]},
            children=[child],
        )

    def _wrap_with_group_by(self, child: ExplainNode, gb_clause: Any) -> ExplainNode:
        rows = max(1, int(child.estimated_rows * GROUP_BY_REDUCTION))
        cost = child.cost + child.estimated_rows * 1.2
        return ExplainNode(
            id=self._new_id(),
            operation="GROUP_BY",
            table=None,
            estimated_rows=rows,
            access_type="temp_table",
            cost=cost,
            bottleneck=True,
            details={"raw": self._raw(gb_clause).strip()[:200]},
            children=[child],
        )

    def _wrap_with_order_by(self, child: ExplainNode, ob_clause: Any) -> ExplainNode:
        rows = child.estimated_rows
        cost = child.cost + child.estimated_rows * 1.5  # sort cost
        return ExplainNode(
            id=self._new_id(),
            operation="SORT",
            table=None,
            estimated_rows=rows,
            access_type="temp_table",
            cost=cost,
            bottleneck=child.estimated_rows > 1000,
            details={"raw": self._raw(ob_clause).strip()[:200]},
            children=[child],
        )

    def _wrap_with_limit(self, child: ExplainNode, limit_clause: Any) -> ExplainNode:
        text = self._raw(limit_clause)
        m = re.search(r"\d+", text)
        limit_val = int(m.group(0)) if m else LIMIT_DEFAULT
        rows = min(child.estimated_rows, max(1, limit_val))
        cost = child.cost  # limit doesn't add cost
        return ExplainNode(
            id=self._new_id(),
            operation="LIMIT",
            table=None,
            estimated_rows=rows,
            access_type="const",
            cost=cost,
            bottleneck=False,
            details={"limit": limit_val},
            children=[child],
        )

    def _wrap_with_distinct(self, child: ExplainNode) -> ExplainNode:
        rows = max(1, int(child.estimated_rows * DISTINCT_REDUCTION))
        cost = child.cost + child.estimated_rows * 1.2
        return ExplainNode(
            id=self._new_id(),
            operation="DISTINCT",
            table=None,
            estimated_rows=rows,
            access_type="temp_table",
            cost=cost,
            bottleneck=True,
            details={},
            children=[child],
        )

    def _build_select_plan(
        self,
        select_segment: Any,
        depth: int = 0,
    ) -> ExplainNode:
        """Build a plan tree for a single SELECT statement segment."""

        select_clause = None
        from_clause = None
        where_clause = None
        groupby_clause = None
        orderby_clause = None
        limit_clause = None

        for child in getattr(select_segment, "segments", []) or []:
            t = getattr(child, "type", None)
            if t == "select_clause":
                select_clause = child
            elif t == "from_clause":
                from_clause = child
            elif t == "where_clause":
                where_clause = child
            elif t == "groupby_clause":
                groupby_clause = child
            elif t == "orderby_clause":
                orderby_clause = child
            elif t == "limit_clause":
                limit_clause = child

        where_text = self._raw(where_clause) if where_clause is not None else ""

        # Base: from + joins (or a placeholder if no FROM, e.g. SELECT 1)
        base_node = self._build_join_chain(from_clause, where_text)
        if base_node is None:
            base_node = ExplainNode(
                id=self._new_id(),
                operation="CONST",
                table=None,
                estimated_rows=1,
                access_type="const",
                cost=1.0,
                bottleneck=False,
                details={"note": "No FROM clause"},
                children=[],
            )

        # Subqueries inside FROM or WHERE => attach as additional children
        subqueries: List[ExplainNode] = []
        if from_clause is not None:
            for sq in self._segments_of_type(from_clause, "select_statement"):
                if sq is not select_segment:
                    sq_plan = self._build_select_plan(sq, depth + 1)
                    sq_plan.operation = f"SUBQUERY ({sq_plan.operation})"
                    sq_plan.cost = sq_plan.cost * SUBQUERY_COST_MULTIPLIER
                    sq_plan.bottleneck = True
                    subqueries.append(sq_plan)
        if where_clause is not None:
            for sq in self._segments_of_type(where_clause, "select_statement"):
                if sq is not select_segment:
                    sq_plan = self._build_select_plan(sq, depth + 1)
                    sq_plan.operation = f"SUBQUERY ({sq_plan.operation})"
                    sq_plan.cost = sq_plan.cost * SUBQUERY_COST_MULTIPLIER
                    sq_plan.bottleneck = True
                    subqueries.append(sq_plan)

        if subqueries:
            base_node = ExplainNode(
                id=self._new_id(),
                operation="NESTED_LOOP",
                table=None,
                estimated_rows=base_node.estimated_rows,
                access_type="ref",
                cost=base_node.cost + sum(s.cost for s in subqueries),
                bottleneck=True,
                details={"subqueries": len(subqueries)},
                children=[base_node, *subqueries],
            )

        if where_clause is not None:
            base_node = self._wrap_with_filter(base_node, where_clause)

        if groupby_clause is not None:
            base_node = self._wrap_with_group_by(base_node, groupby_clause)

        # SELECT projection (DISTINCT detection)
        is_distinct = False
        if select_clause is not None:
            sc_text = self._raw(select_clause).upper()
            if re.search(r"\bSELECT\s+DISTINCT\b", sc_text):
                is_distinct = True

        # PROJECT node
        project_rows = base_node.estimated_rows
        project_cost = base_node.cost + max(1, base_node.estimated_rows // 10)
        project_node = ExplainNode(
            id=self._new_id(),
            operation="PROJECT",
            table=None,
            estimated_rows=project_rows,
            access_type="ref",
            cost=project_cost,
            bottleneck=False,
            details={
                "columns": self._raw(select_clause).strip()[:200] if select_clause else ""
            },
            children=[base_node],
        )
        base_node = project_node

        if is_distinct:
            base_node = self._wrap_with_distinct(base_node)

        if orderby_clause is not None:
            base_node = self._wrap_with_order_by(base_node, orderby_clause)

        if limit_clause is not None:
            base_node = self._wrap_with_limit(base_node, limit_clause)

        return base_node

    def _collect_warnings(self, node: ExplainNode, out: List[str]) -> None:
        if node.access_type == "full_scan":
            out.append(
                f"全表扫描: {node.table or '(派生表)'}，预计扫描 {node.estimated_rows} 行"
            )
        elif node.access_type == "temp_table":
            out.append(f"使用临时表: {node.operation}，可能影响性能")
        if node.operation.startswith("JOIN (CROSS"):
            out.append("检测到 CROSS JOIN，可能产生笛卡尔积")
        if node.operation.startswith("SUBQUERY"):
            out.append("检测到子查询，存在重复扫描风险")
        for child in node.children:
            self._collect_warnings(child, out)

    @staticmethod
    def _sum_cost(node: ExplainNode) -> float:
        return node.cost + sum(ExplainService._sum_cost(c) for c in node.children)

    # ------------------------------------------------------------------
    # Public sync entry
    # ------------------------------------------------------------------
    def _explain_sync(self, sql: str, dialect: str) -> ExplainResponse:
        linter = self._get_linter(dialect)

        # Step 1: validate syntax via Linter
        lint_result = linter.lint_string(sql)
        parse_errors = [
            v for v in lint_result.violations if v.rule_code().startswith("PRS")
        ]
        if parse_errors:
            first = parse_errors[0]
            raise LSPException(
                message=f"SQL parse error: {first.desc()}",
                code=ErrorCode.LINT_PARSE_ERROR,
                details={
                    "line": first.line_no,
                    "column": first.line_pos,
                    "rule": first.rule_code(),
                    "description": first.desc(),
                },
                user_message=f"SQL 语法错误（第 {first.line_no} 行）: {first.desc()}",
            )

        # Step 2: parse to obtain AST
        parsed = linter.parse_string(sql)
        tree = parsed.tree
        if tree is None:
            raise LSPException(
                message="Failed to obtain parse tree",
                code=ErrorCode.LINT_PARSE_ERROR,
                user_message="SQL 解析失败，无法生成执行计划",
            )

        # Step 3: locate first SELECT statement
        statements = self._segments_of_type(tree, "statement")
        select_segments: List[Any] = []
        for stmt in statements:
            select_segments.extend(
                self._direct_children_of_type(stmt, "select_statement")
            )
        if not select_segments:
            # Fallback: any select_statement anywhere
            select_segments = self._segments_of_type(tree, "select_statement")

        if not select_segments:
            raise LSPException(
                message="No SELECT statement found",
                code=ErrorCode.LINT_PARSE_ERROR,
                user_message="未找到 SELECT 语句，目前仅支持 SELECT 的执行计划",
            )

        root = self._build_select_plan(select_segments[0])
        warnings: List[str] = []
        self._collect_warnings(root, warnings)

        return ExplainResponse(
            success=True,
            dialect=dialect,
            root=root,
            total_cost=round(self._sum_cost(root), 2),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------
    async def explain(
        self,
        sql: str,
        dialect: str = "ansi",
        timeout: Optional[float] = None,
    ) -> ExplainResponse:
        if timeout is None:
            timeout = settings.LINT_TIMEOUT

        if not sql or not sql.strip():
            raise LSPException(
                message="Empty SQL",
                code=ErrorCode.LINT_PARSE_ERROR,
                user_message="SQL 内容不能为空",
            )

        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._explain_sync, sql, dialect),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Explain timed out after {timeout}s")
            raise LintTimeoutException(timeout)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
        logger.info("ExplainService shutdown")


# Singleton
explain_service = ExplainService()


__all__ = ["ExplainService", "explain_service"]
