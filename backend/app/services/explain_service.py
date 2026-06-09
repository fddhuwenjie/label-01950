"""
SQL Execution Plan service - parses SQL AST and generates simulated execution plans.
"""
import asyncio
import hashlib
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from sqlfluff.core import Linter
from sqlfluff.core.config import FluffConfig
from sqlfluff.core.parser import BaseSegment

from ..config import settings
from ..core import logger
from ..models import ExplainNode, Diagnostic


class ExplainService:
    """Service for generating simulated SQL execution plans from AST analysis."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._linters: dict = {}
        logger.info("ExplainService initialized")

    def _get_linter(self, dialect: str) -> Linter:
        if dialect not in settings.SUPPORTED_DIALECTS:
            dialect = settings.DEFAULT_DIALECT
        if dialect not in self._linters:
            config = FluffConfig.from_kwargs(dialect=dialect)
            self._linters[dialect] = Linter(config=config)
        return self._linters[dialect]

    def _validate_sql(self, sql: str, dialect: str) -> List[Diagnostic]:
        linter = self._get_linter(dialect)
        result = linter.lint_string(sql)
        diagnostics: List[Diagnostic] = []
        for violation in result.violations:
            if violation.rule_code().startswith("PRS"):
                from ..models import Position, Range, DiagnosticSeverity
                line = max(0, violation.line_no - 1)
                char = max(0, violation.line_pos - 1)
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=line, character=char),
                            end=Position(line=line, character=char + 1),
                        ),
                        severity=DiagnosticSeverity.ERROR,
                        code=violation.rule_code(),
                        source="sqlfluff",
                        message=violation.desc(),
                    )
                )
        return diagnostics

    def _parse_sql(self, sql: str, dialect: str) -> Optional[BaseSegment]:
        linter = self._get_linter(dialect)
        parsed = linter.parse_string(sql)
        if parsed.violations:
            prs_errors = [v for v in parsed.violations if v.rule_code().startswith("PRS")]
            if prs_errors:
                return None
        return parsed.tree

    def _generate_node_id(self, prefix: str, index: int) -> str:
        raw = f"{prefix}-{index}-{random.randint(0, 9999)}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def _estimate_rows(self, table_name: str) -> int:
        random.seed(hashlib.md5(table_name.encode()).hexdigest())
        base = random.choice([100, 500, 1000, 5000, 10000, 50000, 100000])
        return base

    def _estimate_cost(self, rows: int, access_type: str) -> float:
        multipliers = {
            "full_table_scan": 1.0,
            "index_scan": 0.1,
            "index_seek": 0.05,
            "temporary_table": 0.8,
            "hash_join": 0.6,
            "nested_loop": 0.7,
            "merge_join": 0.4,
            "sort": 0.5,
            "filter": 0.3,
            "aggregate": 0.4,
            "subquery": 0.9,
        }
        multiplier = multipliers.get(access_type, 0.5)
        return round(rows * multiplier, 2)

    def _find_segments(self, tree: BaseSegment, segment_type: str) -> List[BaseSegment]:
        results = []
        for segment in tree.recursive_crawl(segment_type):
            results.append(segment)
        return results

    def _analyze_from_clause(self, from_segment: BaseSegment, node_counter: list) -> List[ExplainNode]:
        nodes = []
        table_refs = list(from_segment.recursive_crawl("table_reference"))
        join_clauses = list(from_segment.recursive_crawl("join_clause"))
        subquery_segments = list(from_segment.recursive_crawl("select_statement"))

        for sq in subquery_segments:
            node_counter[0] += 1
            nodes.append(
                ExplainNode(
                    id=self._generate_node_id("subquery", node_counter[0]),
                    operation_type="subquery",
                    table_name=None,
                    estimated_rows=self._estimate_rows(f"subquery_{node_counter[0]}"),
                    access_type="subquery",
                    cost=self._estimate_cost(self._estimate_rows(f"subquery_{node_counter[0]}"), "subquery"),
                    details="Derived table (subquery in FROM clause)",
                    children=self._analyze_select(sq, node_counter),
                )
            )

        for join_clause in join_clauses:
            join_tables = list(join_clause.recursive_crawl("table_reference"))
            join_type_seg = list(join_clause.recursive_crawl("keyword"))

            join_keyword = "JOIN"
            for kw in join_type_seg:
                kw_upper = kw.raw_upper if hasattr(kw, "raw_upper") else str(kw).upper()
                if kw_upper in ("LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL"):
                    join_keyword = kw_upper

            join_access = "hash_join"
            if join_keyword in ("CROSS",):
                join_access = "nested_loop"
            elif join_keyword in ("INNER",):
                join_access = "hash_join"
            elif join_keyword in ("LEFT", "RIGHT", "FULL"):
                join_access = "merge_join"

            for tbl in join_tables:
                table_name = tbl.raw if hasattr(tbl, "raw") else str(tbl)
                if table_name.upper() in ("LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL", "JOIN", "ON", "AS"):
                    continue
                node_counter[0] += 1
                rows = self._estimate_rows(table_name)
                nodes.append(
                    ExplainNode(
                        id=self._generate_node_id("join", node_counter[0]),
                        operation_type=f"{join_keyword} JOIN",
                        table_name=table_name,
                        estimated_rows=rows,
                        access_type=join_access,
                        cost=self._estimate_cost(rows, join_access),
                        details=f"{join_keyword} JOIN on {table_name}",
                        children=[],
                    )
                )

        for tbl in table_refs:
            table_name = tbl.raw if hasattr(tbl, "raw") else str(tbl)
            if table_name.upper() in ("LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL", "JOIN", "ON", "AS"):
                continue
            already_in_join = False
            for jn in nodes:
                if jn.table_name == table_name and jn.operation_type != "full_table_scan":
                    already_in_join = True
                    break
            if already_in_join:
                continue

            node_counter[0] += 1
            rows = self._estimate_rows(table_name)
            has_where = False
            nodes.append(
                ExplainNode(
                    id=self._generate_node_id("scan", node_counter[0]),
                    operation_type="full_table_scan" if not has_where else "table_scan",
                    table_name=table_name,
                    estimated_rows=rows,
                    access_type="full_table_scan",
                    cost=self._estimate_cost(rows, "full_table_scan"),
                    details=f"Full table scan on {table_name}",
                    children=[],
                )
            )

        return nodes

    def _analyze_where_clause(self, where_segment: BaseSegment, node_counter: list) -> Optional[ExplainNode]:
        conditions = list(where_segment.recursive_crawl("expression"))
        subqueries = list(where_segment.recursive_crawl("select_statement"))

        children = []
        for sq in subqueries:
            node_counter[0] += 1
            children.append(
                ExplainNode(
                    id=self._generate_node_id("where_subquery", node_counter[0]),
                    operation_type="subquery",
                    table_name=None,
                    estimated_rows=self._estimate_rows(f"where_sub_{node_counter[0]}"),
                    access_type="subquery",
                    cost=self._estimate_cost(
                        self._estimate_rows(f"where_sub_{node_counter[0]}"), "subquery"
                    ),
                    details="Correlated/uncorrelated subquery in WHERE",
                    children=self._analyze_select(sq, node_counter),
                )
            )

        node_counter[0] += 1
        condition_text = where_segment.raw if hasattr(where_segment, "raw") else "WHERE conditions"
        return ExplainNode(
            id=self._generate_node_id("filter", node_counter[0]),
            operation_type="filter",
            table_name=None,
            estimated_rows=random.randint(50, 5000),
            access_type="filter",
            cost=self._estimate_cost(random.randint(50, 5000), "filter"),
            details=f"Filter: {condition_text[:80]}",
            children=children,
        )

    def _analyze_group_by(self, group_segment: BaseSegment, node_counter: list) -> ExplainNode:
        has_distinct = False
        node_counter[0] += 1
        rows = random.randint(10, 1000)
        return ExplainNode(
            id=self._generate_node_id("aggregate", node_counter[0]),
            operation_type="aggregate",
            table_name=None,
            estimated_rows=rows,
            access_type="temporary_table" if has_distinct else "aggregate",
            cost=self._estimate_cost(rows, "temporary_table" if has_distinct else "aggregate"),
            details="GROUP BY / Aggregation",
            children=[],
        )

    def _analyze_order_by(self, order_segment: BaseSegment, node_counter: list) -> ExplainNode:
        node_counter[0] += 1
        rows = random.randint(100, 10000)
        return ExplainNode(
            id=self._generate_node_id("sort", node_counter[0]),
            operation_type="sort",
            table_name=None,
            estimated_rows=rows,
            access_type="sort",
            cost=self._estimate_cost(rows, "sort"),
            details="ORDER BY sort",
            children=[],
        )

    def _analyze_select(self, select_segment: BaseSegment, node_counter: list) -> List[ExplainNode]:
        nodes = []

        from_segments = list(select_segment.recursive_crawl("from_clause"))
        where_segments = list(select_segment.recursive_crawl("where_clause"))
        group_segments = list(select_segment.recursive_crawl("groupby_clause"))
        order_segments = list(select_segment.recursive_crawl("orderby_clause"))

        for from_seg in from_segments:
            nodes.extend(self._analyze_from_clause(from_seg, node_counter))

        for where_seg in where_segments:
            filter_node = self._analyze_where_clause(where_seg, node_counter)
            if filter_node:
                nodes.append(filter_node)

        for group_seg in group_segments:
            nodes.append(self._analyze_group_by(group_seg, node_counter))

        for order_seg in order_segments:
            nodes.append(self._analyze_order_by(order_seg, node_counter))

        return nodes

    def _build_explain_tree(self, tree: BaseSegment) -> ExplainNode:
        node_counter = [0]

        select_statements = list(tree.recursive_crawl("select_statement"))

        if not select_statements:
            return ExplainNode(
                id=self._generate_node_id("root", 0),
                operation_type="unknown",
                table_name=None,
                estimated_rows=0,
                access_type="full_table_scan",
                cost=0.0,
                details="No SELECT statement found",
                children=[],
            )

        if len(select_statements) == 1:
            children = self._analyze_select(select_statements[0], node_counter)
            total_rows = sum(c.estimated_rows for c in children) if children else 0
            total_cost = sum(c.cost for c in children) if children else 0.0
            return ExplainNode(
                id=self._generate_node_id("root", 0),
                operation_type="query",
                table_name=None,
                estimated_rows=total_rows,
                access_type="full_table_scan",
                cost=round(total_cost, 2),
                details="SELECT query",
                children=children,
            )

        children = []
        for i, select_stmt in enumerate(select_statements):
            sub_children = self._analyze_select(select_stmt, node_counter)
            sub_rows = sum(c.estimated_rows for c in sub_children) if sub_children else 0
            sub_cost = sum(c.cost for c in sub_children) if sub_children else 0.0
            node_counter[0] += 1
            children.append(
                ExplainNode(
                    id=self._generate_node_id("union", node_counter[0]),
                    operation_type="compound_query",
                    table_name=None,
                    estimated_rows=sub_rows,
                    access_type="temporary_table",
                    cost=round(sub_cost, 2),
                    details=f"Query component {i + 1}",
                    children=sub_children,
                )
            )

        total_rows = sum(c.estimated_rows for c in children)
        total_cost = sum(c.cost for c in children)
        return ExplainNode(
            id=self._generate_node_id("root", 0),
            operation_type="compound_query",
            table_name=None,
            estimated_rows=total_rows,
            access_type="temporary_table",
            cost=round(total_cost, 2),
            details="Compound query (UNION/compound)",
            children=children,
        )

    def _explain_sync(self, sql: str, dialect: str) -> ExplainNode:
        tree = self._parse_sql(sql, dialect)
        if tree is None:
            return ExplainNode(
                id="error",
                operation_type="error",
                table_name=None,
                estimated_rows=0,
                access_type="full_table_scan",
                cost=0.0,
                details="Failed to parse SQL",
                children=[],
            )
        return self._build_explain_tree(tree)

    async def explain(self, sql: str, dialect: str = "ansi") -> dict:
        """
        Generate a simulated execution plan for the given SQL.

        First validates SQL with SQLFluff Linter, then parses AST to build
        a simulated execution plan tree.

        Returns:
            dict with 'success', 'root', and optional 'error' keys.
        """
        parse_errors = self._validate_sql(sql, dialect)
        if parse_errors:
            error_messages = [d.message for d in parse_errors]
            return {
                "success": False,
                "root": None,
                "error": "SQL syntax validation failed: " + "; ".join(error_messages),
            }

        loop = asyncio.get_event_loop()
        try:
            root_node = await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._explain_sync, sql, dialect),
                timeout=settings.LINT_TIMEOUT,
            )
            return {"success": True, "root": root_node, "error": None}
        except asyncio.TimeoutError:
            logger.warning(f"Explain timed out after {settings.LINT_TIMEOUT}s")
            return {
                "success": False,
                "root": None,
                "error": f"Execution plan generation timed out after {settings.LINT_TIMEOUT}s",
            }
        except Exception as e:
            logger.exception(f"Explain failed: {e}")
            return {
                "success": False,
                "root": None,
                "error": f"Failed to generate execution plan: {str(e)}",
            }

    def shutdown(self):
        self._executor.shutdown(wait=False)
        logger.info("ExplainService shutdown")


explain_service = ExplainService()

__all__ = ["ExplainService", "explain_service"]
