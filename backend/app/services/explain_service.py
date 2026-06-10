"""
SQL execution plan generation service.
Analyzes SQL AST from SQLFluff to generate simulated execution plans.
"""
import re
import uuid
from typing import List, Optional, Tuple

from sqlfluff.core import Linter
from sqlfluff.core.config import FluffConfig

from ..config import settings
from ..core import logger, InvalidDialectException
from ..models import (
    ExplainPlanNode,
    ExplainOperationType,
    ExplainAccessType,
    ExplainResponse,
)


class ExplainService:
    """Service for generating simulated SQL execution plans."""

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
            logger.debug(f"Created explain linter for dialect: {dialect}")

        return self._linters[dialect]

    def _validate_sql(self, sql: str, dialect: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL syntax using SQLFluff.

        Args:
            sql: SQL statement to validate.
            dialect: SQL dialect.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        linter = self._get_linter(dialect)
        result = linter.lint_string(sql)

        errors = []
        for violation in result.violations:
            if violation.rule_code().startswith("PRS"):
                errors.append(f"Line {violation.line_no}: {violation.desc()}")

        return len(errors) == 0, errors

    def _node_id(self) -> str:
        """Generate a unique node ID."""
        return str(uuid.uuid4())[:8]

    def _parse_tables(self, sql: str) -> List[str]:
        """
        Extract table names from SQL statement.

        Args:
            sql: SQL statement.

        Returns:
            List of table names.
        """
        tables = []
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)

        return list(dict.fromkeys(tables))

    def _count_joins(self, sql: str) -> int:
        """Count the number of JOIN operations."""
        join_patterns = [
            r'\bINNER\s+JOIN\b',
            r'\bLEFT\s+JOIN\b',
            r'\bRIGHT\s+JOIN\b',
            r'\bFULL\s+JOIN\b',
            r'\bCROSS\s+JOIN\b',
            r'(?<!\w)JOIN(?!\w)',
        ]
        count = 0
        for pattern in join_patterns:
            count += len(re.findall(pattern, sql, re.IGNORECASE))
        return count

    def _has_subquery(self, sql: str) -> bool:
        """Check if SQL contains a subquery."""
        return bool(re.search(r'\(\s*SELECT\s', sql, re.IGNORECASE))

    def _has_where(self, sql: str) -> bool:
        """Check if SQL has a WHERE clause."""
        return bool(re.search(r'\bWHERE\b', sql, re.IGNORECASE))

    def _has_group_by(self, sql: str) -> bool:
        """Check if SQL has GROUP BY."""
        return bool(re.search(r'\bGROUP\s+BY\b', sql, re.IGNORECASE))

    def _has_order_by(self, sql: str) -> bool:
        """Check if SQL has ORDER BY."""
        return bool(re.search(r'\bORDER\s+BY\b', sql, re.IGNORECASE))

    def _has_having(self, sql: str) -> bool:
        """Check if SQL has HAVING clause."""
        return bool(re.search(r'\bHAVING\b', sql, re.IGNORECASE))

    def _has_limit(self, sql: str) -> bool:
        """Check if SQL has LIMIT clause."""
        return bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE))

    def _has_distinct(self, sql: str) -> bool:
        """Check if SQL has DISTINCT."""
        return bool(re.search(r'\bSELECT\s+DISTINCT\b', sql, re.IGNORECASE))

    def _has_aggregate(self, sql: str) -> bool:
        """Check if SQL has aggregate functions."""
        agg_funcs = [r'\bCOUNT\s*\(', r'\bSUM\s*\(', r'\bAVG\s*\(', r'\bMAX\s*\(', r'\bMIN\s*\(']
        for pattern in agg_funcs:
            if re.search(pattern, sql, re.IGNORECASE):
                return True
        return False

    def _get_limit_value(self, sql: str) -> Optional[int]:
        """Extract LIMIT value if present."""
        match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _estimate_rows(self, table_name: str, has_where: bool, is_index_scan: bool) -> int:
        """
        Estimate number of rows for a table scan.

        Args:
            table_name: Name of the table.
            has_where: Whether WHERE clause exists.
            is_index_scan: Whether using index scan.

        Returns:
            Estimated row count.
        """
        base_rows = 10000

        if has_where and is_index_scan:
            return max(100, base_rows // 100)
        elif has_where:
            return max(1000, base_rows // 10)
        else:
            return base_rows

    def _create_table_scan_node(
        self,
        table_name: str,
        has_where: bool,
        is_index_scan: bool = False,
    ) -> ExplainPlanNode:
        """
        Create a table scan node.

        Args:
            table_name: Name of the table.
            has_where: Whether WHERE clause filters this table.
            is_index_scan: Whether this is an index scan.

        Returns:
            ExplainPlanNode for the table scan.
        """
        estimated_rows = self._estimate_rows(table_name, has_where, is_index_scan)

        if is_index_scan:
            operation = ExplainOperationType.INDEX_SCAN
            access_type = ExplainAccessType.INDEX_SCAN
            cost = estimated_rows * 0.1
            description = f"Index scan on table {table_name}"
        else:
            operation = ExplainOperationType.TABLE_SCAN
            access_type = ExplainAccessType.FULL_SCAN
            cost = estimated_rows * 1.0
            description = f"Full table scan on table {table_name}"

        return ExplainPlanNode(
            id=self._node_id(),
            operation=operation,
            table_name=table_name,
            estimated_rows=estimated_rows,
            access_type=access_type,
            cost=cost,
            description=description,
            children=[],
        )

    def _create_join_node(
        self,
        join_type: ExplainOperationType,
        left_child: ExplainPlanNode,
        right_child: ExplainPlanNode,
    ) -> ExplainPlanNode:
        """
        Create a JOIN operation node.

        Args:
            join_type: Type of join operation.
            left_child: Left input node.
            right_child: Right input node.

        Returns:
            ExplainPlanNode for the join.
        """
        estimated_rows = max(
            left_child.estimated_rows,
            right_child.estimated_rows
        )
        cost = (
            left_child.cost
            + right_child.cost
            + left_child.estimated_rows * right_child.estimated_rows * 0.001
        )

        join_algorithm = ExplainOperationType.HASH_JOIN
        description = f"{join_type.value} using hash join algorithm"

        if join_type == ExplainOperationType.CROSS_JOIN:
            estimated_rows = left_child.estimated_rows * right_child.estimated_rows
            cost += estimated_rows * 0.5
            description = f"Cartesian product join - potential performance issue"

        return ExplainPlanNode(
            id=self._node_id(),
            operation=join_algorithm,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type=None,
            cost=cost,
            description=description,
            children=[left_child, right_child],
        )

    def _create_filter_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create a WHERE filter node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for the filter operation.
        """
        estimated_rows = max(1, child.estimated_rows // 10)
        cost = child.cost + child.estimated_rows * 0.01

        return ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.WHERE,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type=None,
            cost=cost,
            description="Filter rows based on WHERE conditions",
            children=[child],
        )

    def _create_aggregate_node(
        self,
        child: ExplainPlanNode,
        has_group_by: bool,
    ) -> ExplainPlanNode:
        """
        Create an aggregate/group by node.

        Args:
            child: Child node.
            has_group_by: Whether GROUP BY is present.

        Returns:
            ExplainPlanNode for the aggregate operation.
        """
        if has_group_by:
            estimated_rows = max(1, child.estimated_rows // 20)
            description = "Group rows and compute aggregates"
        else:
            estimated_rows = 1
            description = "Compute scalar aggregate"

        cost = child.cost + child.estimated_rows * 0.05

        return ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.AGGREGATE,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type=ExplainAccessType.MEMORY,
            cost=cost,
            description=description,
            children=[child],
        )

    def _create_sort_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create an ORDER BY sort node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for the sort operation.
        """
        estimated_rows = child.estimated_rows
        cost = child.cost + child.estimated_rows * max(1, child.estimated_rows.bit_length()) * 0.01

        return ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.SORT,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type=None,
            cost=cost,
            description="Sort result set by ORDER BY columns",
            children=[child],
        )

    def _create_limit_node(self, child: ExplainPlanNode, limit: int) -> ExplainPlanNode:
        """
        Create a LIMIT node.

        Args:
            child: Child node.
            limit: Number of rows to limit.

        Returns:
            ExplainPlanNode for the limit operation.
        """
        estimated_rows = min(limit, child.estimated_rows)
        cost = child.cost + 0.1

        return ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.LIMIT,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type=None,
            cost=cost,
            description=f"Limit result set to {limit} rows",
            children=[child],
        )

    def _create_distinct_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create a DISTINCT node.

        Args:
            child: Child node.

        Returns:
            ExplainPlanNode for the distinct operation.
        """
        estimated_rows = max(1, child.estimated_rows // 5)
        cost = child.cost + child.estimated_rows * 0.1

        return ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.DISTINCT,
            table_name=None,
            estimated_rows=estimated_rows,
            access_type=ExplainAccessType.TEMP_TABLE,
            cost=cost,
            description="Remove duplicate rows using temporary table",
            children=[child],
        )

    def _create_subquery_node(self, child: ExplainPlanNode) -> ExplainPlanNode:
        """
        Create a subquery node.

        Args:
            child: Child node representing the subquery.

        Returns:
            ExplainPlanNode for the subquery.
        """
        return ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.SUBQUERY,
            table_name=None,
            estimated_rows=child.estimated_rows,
            access_type=ExplainAccessType.TEMP_TABLE,
            cost=child.cost + child.estimated_rows * 0.2,
            description="Execute subquery and store results in temporary table",
            children=[child],
        )

    def _detect_join_type(self, sql: str, index: int) -> ExplainOperationType:
        """
        Detect the type of JOIN at a given position.

        Args:
            sql: SQL statement.
            index: Index of the JOIN keyword.

        Returns:
            Join operation type.
        """
        before = sql[:index].upper()

        if "LEFT" in before[-20:]:
            return ExplainOperationType.LEFT_JOIN
        elif "RIGHT" in before[-20:]:
            return ExplainOperationType.RIGHT_JOIN
        elif "FULL" in before[-20:]:
            return ExplainOperationType.FULL_JOIN
        elif "CROSS" in before[-20:]:
            return ExplainOperationType.CROSS_JOIN
        elif "INNER" in before[-20:]:
            return ExplainOperationType.INNER_JOIN
        else:
            return ExplainOperationType.INNER_JOIN

    def generate_plan(self, sql: str, dialect: str = "ansi") -> ExplainResponse:
        """
        Generate a simulated execution plan for a SQL statement.

        Args:
            sql: SQL statement to explain.
            dialect: SQL dialect.

        Returns:
            ExplainResponse with the execution plan.

        Raises:
            InvalidDialectException: If dialect is not supported.
            ValidationException: If SQL syntax is invalid.
        """
        from ..core import ValidationException

        logger.info(f"Generating execution plan for dialect: {dialect}")

        is_valid, errors = self._validate_sql(sql, dialect)
        if not is_valid:
            raise ValidationException(
                message="SQL syntax validation failed",
                details={"errors": errors}
            )

        tables = self._parse_tables(sql)
        has_where = self._has_where(sql)
        has_group_by = self._has_group_by(sql)
        has_order_by = self._has_order_by(sql)
        has_having = self._has_having(sql)
        has_limit = self._has_limit(sql)
        has_distinct = self._has_distinct(sql)
        has_aggregate = self._has_aggregate(sql)
        has_subquery = self._has_subquery(sql)
        join_count = self._count_joins(sql)
        limit_value = self._get_limit_value(sql)

        warnings: List[str] = []

        if not tables:
            tables = ["dual"]

        is_index_scan = has_where and not has_subquery

        current_node = self._create_table_scan_node(
            tables[0],
            has_where=has_where,
            is_index_scan=is_index_scan,
        )

        if not is_index_scan:
            warnings.append(
                f"全表扫描 detected on table '{tables[0]}'. "
                "Consider adding indexes for better performance."
            )

        for i in range(1, len(tables)):
            join_type = ExplainOperationType.INNER_JOIN
            right_table_node = self._create_table_scan_node(
                tables[i],
                has_where=False,
                is_index_scan=False,
            )

            if not right_table_node.access_type == ExplainAccessType.INDEX_SCAN:
                warnings.append(
                    f"全表扫描 detected on table '{tables[i]}' for join. "
                    "Consider adding join indexes."
                )

            current_node = self._create_join_node(
                join_type,
                current_node,
                right_table_node,
            )

        if join_count > 3:
            warnings.append(
                f"Query contains {join_count} JOINs. "
                "Many joins can lead to performance issues."
            )

        if has_subquery:
            subquery_tables = ["subquery_table"]
            subquery_node = self._create_table_scan_node(
                subquery_tables[0],
                has_where=True,
                is_index_scan=False,
            )
            subquery_node = self._create_subquery_node(subquery_node)
            current_node.children.append(subquery_node)
            warnings.append("子查询 detected. Consider rewriting as JOIN for better performance.")

        if has_where:
            current_node = self._create_filter_node(current_node)

        if has_group_by or has_aggregate:
            current_node = self._create_aggregate_node(current_node, has_group_by)
            if has_group_by:
                warnings.append("GROUP BY operation may require temporary table.")

        if has_having:
            current_node = ExplainPlanNode(
                id=self._node_id(),
                operation=ExplainOperationType.HAVING,
                table_name=None,
                estimated_rows=max(1, current_node.estimated_rows // 2),
                access_type=None,
                cost=current_node.cost + current_node.estimated_rows * 0.02,
                description="Filter groups by HAVING condition",
                children=[current_node],
            )

        if has_distinct:
            current_node = self._create_distinct_node(current_node)
            warnings.append("DISTINCT operation uses temporary table - performance impact.")

        if has_order_by:
            current_node = self._create_sort_node(current_node)
            if not has_limit:
                warnings.append("ORDER BY without LIMIT can be expensive for large result sets.")

        if has_limit and limit_value is not None:
            current_node = self._create_limit_node(current_node, limit_value)

        select_node = ExplainPlanNode(
            id=self._node_id(),
            operation=ExplainOperationType.SELECT,
            table_name=None,
            estimated_rows=current_node.estimated_rows,
            access_type=None,
            cost=current_node.cost + current_node.estimated_rows * 0.001,
            description="Project columns and return result set",
            children=[current_node],
        )

        total_cost = select_node.cost

        logger.info(f"Execution plan generated, total cost: {total_cost:.2f}")

        return ExplainResponse(
            success=True,
            plan=select_node,
            total_cost=total_cost,
            warnings=warnings,
            dialect=dialect,
        )


explain_service = ExplainService()


__all__ = ["ExplainService", "explain_service"]
