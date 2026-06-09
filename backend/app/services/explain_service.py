"""
SQL execution plan generation service.
"""
import re
import uuid
from typing import List, Optional, Tuple
from sqlfluff.core import Linter
from sqlfluff.core.config import FluffConfig

from ..config import settings
from ..core import logger, LintTimeoutException, InvalidDialectException
from ..models import (
    ExplainPlanNode,
    ExplainResponse,
    ExplainNodeType,
    Diagnostic,
)
from . import linter_service


class ExplainService:
    """Service for generating SQL execution plans."""

    def __init__(self):
        self._linters: dict = {}
        logger.info("ExplainService initialized")

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
            logger.debug(f"Created linter for explain: {dialect}")

        return self._linters[dialect]

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        return str(uuid.uuid4())[:8]

    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """
        Extract table names from SQL using regex.

        Args:
            sql: SQL statement.

        Returns:
            List of table names.
        """
        tables = []
        
        from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        from_matches = re.findall(from_pattern, sql, re.IGNORECASE)
        tables.extend(from_matches)
        
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_matches = re.findall(join_pattern, sql, re.IGNORECASE)
        tables.extend(join_matches)
        
        update_pattern = r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        update_matches = re.findall(update_pattern, sql, re.IGNORECASE)
        tables.extend(update_matches)
        
        insert_pattern = r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        insert_matches = re.findall(insert_pattern, sql, re.IGNORECASE)
        tables.extend(insert_matches)
        
        delete_pattern = r'DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        delete_matches = re.findall(delete_pattern, sql, re.IGNORECASE)
        tables.extend(delete_matches)
        
        unique_tables = []
        seen = set()
        for table in tables:
            if table.lower() not in seen:
                seen.add(table.lower())
                unique_tables.append(table)
        
        return unique_tables

    def _has_where_clause(self, sql: str) -> bool:
        """Check if SQL has a WHERE clause."""
        return bool(re.search(r'\bWHERE\b', sql, re.IGNORECASE))

    def _has_index_hint(self, sql: str) -> bool:
        """Check if SQL has index hints."""
        return bool(re.search(r'\b(INDEX|USE\s+INDEX|FORCE\s+INDEX)\b', sql, re.IGNORECASE))

    def _has_subquery(self, sql: str) -> bool:
        """Check if SQL has subqueries."""
        return sql.count('(') >= 2 and bool(re.search(r'\bSELECT\b.*\(', sql, re.IGNORECASE | re.DOTALL))

    def _has_group_by(self, sql: str) -> bool:
        """Check if SQL has GROUP BY clause."""
        return bool(re.search(r'\bGROUP\s+BY\b', sql, re.IGNORECASE))

    def _has_order_by(self, sql: str) -> bool:
        """Check if SQL has ORDER BY clause."""
        return bool(re.search(r'\bORDER\s+BY\b', sql, re.IGNORECASE))

    def _has_limit(self, sql: str) -> bool:
        """Check if SQL has LIMIT clause."""
        return bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE))

    def _count_joins(self, sql: str) -> int:
        """Count number of JOINs in SQL."""
        return len(re.findall(r'\bJOIN\b', sql, re.IGNORECASE))

    def _has_aggregate_function(self, sql: str) -> bool:
        """Check if SQL has aggregate functions."""
        return bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', sql, re.IGNORECASE))

    def _create_table_scan_node(
        self,
        table_name: str,
        has_where: bool,
        has_index: bool
    ) -> ExplainPlanNode:
        """
        Create a table scan node.

        Args:
            table_name: Name of the table.
            has_where: Whether there's a WHERE clause.
            has_index: Whether index is used.

        Returns:
            ExplainPlanNode for table scan.
        """
        node_id = self._generate_node_id()
        
        if has_index:
            operation_type = ExplainNodeType.INDEX_SCAN
            access_type = "index_scan"
            estimated_rows = 1000 if has_where else 10000
            cost = 100.0 if has_where else 500.0
            is_bottleneck = False
            bottleneck_reason = None
            description = f"Index scan on table {table_name}"
        else:
            operation_type = ExplainNodeType.TABLE_SCAN
            access_type = "full_scan"
            estimated_rows = 10000 if has_where else 100000
            cost = 1000.0 if has_where else 5000.0
            is_bottleneck = True
            bottleneck_reason = "Full table scan - consider adding index"
            description = f"Full table scan on {table_name}"

        return ExplainPlanNode(
            id=node_id,
            operation_type=operation_type,
            table_name=table_name,
            estimated_rows=estimated_rows,
            access_type=access_type,
            cost=cost,
            description=description,
            is_bottleneck=is_bottleneck,
            bottleneck_reason=bottleneck_reason,
            children=[]
        )

    def _create_join_node(
        self,
        left_child: ExplainPlanNode,
        right_child: ExplainPlanNode,
        join_type: str = "HASH_JOIN"
    ) -> ExplainPlanNode:
        """
        Create a JOIN node.

        Args:
            left_child: Left child node.
            right_child: Right child node.
            join_type: Type of join.

        Returns:
            ExplainPlanNode for join.
        """
        node_id = self._generate_node_id()
        operation_type = ExplainNodeType[join_type]
        
        estimated_rows = max(
            left_child.estimated_rows,
            right_child.estimated_rows
        ) // 2
        
        cost = left_child.cost + right_child.cost + estimated_rows * 0.1
        
        is_bottleneck = left_child.is_bottleneck or right_child.is_bottleneck
        bottleneck_reason = None
        if is_bottleneck:
            bottleneck_reason = "Join involves full table scan"

        return ExplainPlanNode(
            id=node_id,
            operation_type=operation_type,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type="join",
            cost=cost,
            description=f"{join_type.replace('_', ' ')} operation",
            is_bottleneck=is_bottleneck,
            bottleneck_reason=bottleneck_reason,
            children=[left_child, right_child]
        )

    def _create_where_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create a WHERE filter node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for WHERE filter.
        """
        node_id = self._generate_node_id()
        
        estimated_rows = child.estimated_rows // 10
        cost = child.cost + child.estimated_rows * 0.01

        return ExplainPlanNode(
            id=node_id,
            operation_type=ExplainNodeType.WHERE,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type="filter",
            cost=cost,
            description="Filter rows by WHERE condition",
            is_bottleneck=False,
            bottleneck_reason=None,
            children=[child]
        )

    def _create_group_by_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create a GROUP BY aggregate node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for GROUP BY.
        """
        node_id = self._generate_node_id()
        
        estimated_rows = child.estimated_rows // 5
        cost = child.cost + child.estimated_rows * 0.2

        return ExplainPlanNode(
            id=node_id,
            operation_type=ExplainNodeType.GROUP_BY,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type="aggregate",
            cost=cost,
            description="Group rows and aggregate",
            is_bottleneck=False,
            bottleneck_reason=None,
            children=[child]
        )

    def _create_sort_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create an ORDER BY sort node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for sort.
        """
        node_id = self._generate_node_id()
        
        estimated_rows = child.estimated_rows
        cost = child.cost + child.estimated_rows * 0.5

        is_bottleneck = child.estimated_rows > 10000
        bottleneck_reason = None
        if is_bottleneck:
            bottleneck_reason = "Sorting large result set - consider LIMIT or index"

        return ExplainPlanNode(
            id=node_id,
            operation_type=ExplainNodeType.ORDER_BY,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type="sort",
            cost=cost,
            description="Sort result set",
            is_bottleneck=is_bottleneck,
            bottleneck_reason=bottleneck_reason,
            children=[child]
        )

    def _create_limit_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create a LIMIT node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for LIMIT.
        """
        node_id = self._generate_node_id()
        
        estimated_rows = min(child.estimated_rows, 100)
        cost = child.cost + 10.0

        return ExplainPlanNode(
            id=node_id,
            operation_type=ExplainNodeType.LIMIT,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type="limit",
            cost=cost,
            description="Limit number of rows",
            is_bottleneck=False,
            bottleneck_reason=None,
            children=[child]
        )

    def _create_subquery_node(self, table_name: str) -> ExplainPlanNode:
        """
        Create a subquery node.

        Args:
            table_name: Alias for the subquery.

        Returns:
            ExplainPlanNode for subquery.
        """
        node_id = self._generate_node_id()
        
        scan_node = self._create_table_scan_node(
            f"subquery_{table_name}",
            has_where=True,
            has_index=False
        )
        
        group_node = self._create_group_by_node(scan_node)
        
        estimated_rows = 5000
        cost = group_node.cost + 500.0

        return ExplainPlanNode(
            id=node_id,
            operation_type=ExplainNodeType.SUBQUERY,
            table_name=table_name,
            estimated_rows=estimated_rows,
            access_type="subquery",
            cost=cost,
            description=f"Subquery result as {table_name}",
            is_bottleneck=True,
            bottleneck_reason="Subquery may cause temporary table",
            children=[group_node]
        )

    def _create_select_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create the top-level SELECT node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for SELECT.
        """
        node_id = self._generate_node_id()

        return ExplainPlanNode(
            id=node_id,
            operation_type=ExplainNodeType.SELECT,
            table_name=None,
            estimated_rows=child.estimated_rows,
            access_type="select",
            cost=child.cost + child.estimated_rows * 0.01,
            description="Final result projection",
            is_bottleneck=child.is_bottleneck,
            bottleneck_reason=child.bottleneck_reason,
            children=[child]
        )

    def _count_bottlenecks(self, node: ExplainPlanNode) -> int:
        """
        Count number of bottleneck nodes in the tree.

        Args:
            node: Root node of the tree.

        Returns:
            Number of bottleneck nodes.
        """
        count = 1 if node.is_bottleneck else 0
        for child in node.children:
            count += self._count_bottlenecks(child)
        return count

    def generate_plan(self, sql: str, dialect: str = "ansi") -> ExplainResponse:
        """
        Generate execution plan for SQL statement.

        Args:
            sql: SQL statement.
            dialect: SQL dialect.

        Returns:
            ExplainResponse with execution plan.

        Raises:
            InvalidDialectException: If dialect is not supported.
            LintTimeoutException: If parsing times out.
        """
        logger.info(f"Generating execution plan for dialect: {dialect}")
        
        linter = self._get_linter(dialect)
        
        result = linter.lint_string(sql)
        if result.violations:
            parse_errors = [v for v in result.violations if v.rule_code().startswith("PRS")]
            if parse_errors:
                error_msg = parse_errors[0].desc()
                logger.warning(f"SQL parse error: {error_msg}")
                raise ValueError(f"SQL syntax error: {error_msg}")

        tables = self._extract_tables_from_sql(sql)
        has_where = self._has_where_clause(sql)
        has_subquery = self._has_subquery(sql)
        has_group_by = self._has_group_by(sql)
        has_order_by = self._has_order_by(sql)
        has_limit = self._has_limit(sql)
        join_count = self._count_joins(sql)
        has_aggregate = self._has_aggregate_function(sql)
        has_index = self._has_index_hint(sql)

        logger.debug(f"SQL analysis: tables={tables}, joins={join_count}, subquery={has_subquery}")

        current_node = None
        
        if has_subquery and len(tables) >= 2:
            subquery_node = self._create_subquery_node("subq")
            main_table_node = self._create_table_scan_node(tables[0], has_where, has_index)
            current_node = self._create_join_node(main_table_node, subquery_node, "HASH_JOIN")
        elif len(tables) == 1:
            current_node = self._create_table_scan_node(tables[0], has_where, has_index)
        elif len(tables) >= 2:
            left_node = self._create_table_scan_node(tables[0], has_where, has_index)
            for i in range(1, len(tables)):
                right_node = self._create_table_scan_node(tables[i], False, False)
                join_type = "HASH_JOIN" if i == 1 else "NESTED_LOOP_JOIN"
                left_node = self._create_join_node(left_node, right_node, join_type)
            current_node = left_node
        else:
            current_node = self._create_table_scan_node("dual", False, True)

        if has_where:
            current_node = self._create_where_node(current_node)

        if has_group_by or has_aggregate:
            current_node = self._create_group_by_node(current_node)

        if has_order_by:
            current_node = self._create_sort_node(current_node)

        if has_limit:
            current_node = self._create_limit_node(current_node)

        root_node = self._create_select_node(current_node)

        bottleneck_count = self._count_bottlenecks(root_node)

        response = ExplainResponse(
            success=True,
            plan=root_node,
            total_cost=root_node.cost,
            total_estimated_rows=root_node.estimated_rows,
            has_bottlenecks=bottleneck_count > 0,
            bottleneck_count=bottleneck_count
        )

        logger.info(f"Execution plan generated: cost={response.total_cost}, bottlenecks={bottleneck_count}")
        return response


explain_service = ExplainService()

__all__ = ["ExplainService", "explain_service"]
