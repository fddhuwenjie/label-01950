"""
SQL Explain service: parses SQL AST and generates simulated execution plan.
"""
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple, Any

from sqlfluff.core import Linter
from sqlfluff.core.config import FluffConfig

from ..config import settings
from ..core import logger
from ..models import (
    AccessType,
    BottleneckLevel,
    ExplainResponse,
    ExplainRequest,
    ExecutionPlanNode,
    NodeType,
)


class ExplainService:
    """Service for generating simulated SQL execution plans using SQL AST analysis."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._linters: dict = {}
        logger.info("ExplainService initialized")

    def _get_linter(self, dialect: str) -> Linter:
        if dialect not in settings.SUPPORTED_DIALECTS:
            dialect = "ansi"
        if dialect not in self._linters:
            config = FluffConfig.from_kwargs(dialect=dialect)
            self._linters[dialect] = Linter(config=config)
        return self._linters[dialect]

    def _validate_sql(self, sql: str, dialect: str) -> Tuple[bool, List[str], Any]:
        linter = self._get_linter(dialect)
        parsed = linter.parse_string(sql)
        errors = []

        for violation in parsed.violations:
            if violation.rule_code().startswith("PRS"):
                errors.append(f"Line {violation.line_no}: {violation.desc()}")

        return len(errors) == 0, errors, parsed.tree

    def _generate_id(self) -> str:
        return f"node_{uuid.uuid4().hex[:8]}"

    def _find_segments(self, tree: Any, segment_type: str) -> List[Any]:
        results = []
        if tree is None:
            return results
        if hasattr(tree, "is_type") and tree.is_type(segment_type):
            results.append(tree)
        if hasattr(tree, "segments"):
            for seg in tree.segments:
                results.extend(self._find_segments(seg, segment_type))
        return results

    def _extract_table_names(self, tree: Any) -> List[Tuple[str, Optional[str]]]:
        tables = []
        from_clauses = self._find_segments(tree, "from_clause")
        join_clauses = self._find_segments(tree, "join_clause")

        all_refs = []
        for clause in from_clauses + join_clauses:
            for seg in getattr(clause, "segments", []):
                if hasattr(seg, "is_type"):
                    if seg.is_type("table_reference"):
                        all_refs.append(seg)

        for ref in all_refs:
            parts = []
            alias = None
            for seg in getattr(ref, "segments", []):
                if hasattr(seg, "is_type") and seg.is_type("naked_identifier"):
                    parts.append(seg.raw)
                if hasattr(seg, "is_type") and seg.is_type("alias_expression"):
                    for a_seg in getattr(seg, "segments", []):
                        if hasattr(a_seg, "is_type") and a_seg.is_type("naked_identifier"):
                            alias = a_seg.raw
            if parts:
                tables.append((".".join(parts), alias))

        return tables

    def _detect_join_types(self, tree: Any) -> List[Tuple[str, Optional[str]]]:
        joins = []
        join_clauses = self._find_segments(tree, "join_clause")
        for join_clause in join_clauses:
            join_type = "INNER"
            for seg in getattr(join_clause, "segments", []):
                raw_upper = seg.raw.upper().strip()
                if "LEFT" in raw_upper and "JOIN" in raw_upper:
                    join_type = "LEFT"
                elif "RIGHT" in raw_upper and "JOIN" in raw_upper:
                    join_type = "RIGHT"
                elif "FULL" in raw_upper and "JOIN" in raw_upper:
                    join_type = "FULL"
                elif "CROSS" in raw_upper and "JOIN" in raw_upper:
                    join_type = "CROSS"
                elif "INNER" in raw_upper or raw_upper == "JOIN":
                    join_type = "INNER"
            joins.append((join_type, join_clause))
        return joins

    def _has_where_clause(self, tree: Any) -> bool:
        return len(self._find_segments(tree, "where_clause")) > 0

    def _extract_where_conditions(self, tree: Any) -> List[str]:
        conditions = []
        where_clauses = self._find_segments(tree, "where_clause")
        for wc in where_clauses:
            for seg in getattr(wc, "segments", []):
                if hasattr(seg, "is_type") and seg.is_type("expression"):
                    conditions.append(seg.raw.strip())
        return conditions

    def _has_group_by(self, tree: Any) -> bool:
        return len(self._find_segments(tree, "groupby_clause")) > 0

    def _has_order_by(self, tree: Any) -> bool:
        return len(self._find_segments(tree, "orderby_clause")) > 0

    def _has_limit(self, tree: Any) -> bool:
        return len(self._find_segments(tree, "limit_clause")) > 0

    def _has_subquery(self, tree: Any) -> bool:
        for seg_type in ["select_statement", "set_expression"]:
            found = self._find_segments(tree, seg_type)
            if len(found) > 1:
                return True
        return False

    def _has_distinct(self, tree: Any) -> bool:
        select_clauses = self._find_segments(tree, "select_clause")
        for sc in select_clauses:
            for seg in getattr(sc, "segments", []):
                if seg.raw.upper().strip() == "DISTINCT":
                    return True
        return False

    def _has_aggregate_functions(self, tree: Any) -> bool:
        agg_keywords = ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX(", "GROUP_CONCAT("]
        sql_upper = tree.raw.upper() if hasattr(tree, "raw") else ""
        return any(kw in sql_upper for kw in agg_keywords)

    def _estimate_table_rows(self, table_name: str, has_where: bool, has_index_hint: bool) -> Tuple[int, AccessType, BottleneckLevel]:
        base_rows = 10000
        name_hash = sum(ord(c) for c in table_name)
        base_rows = base_rows + (name_hash % 90000)

        if has_index_hint:
            return max(1, base_rows // 100), AccessType.REF, BottleneckLevel.NONE
        elif has_where:
            if name_hash % 3 == 0:
                return max(1, base_rows), AccessType.ALL, BottleneckLevel.CRITICAL
            elif name_hash % 3 == 1:
                return max(1, base_rows // 50), AccessType.RANGE_SCAN, BottleneckLevel.NONE
            else:
                return max(1, base_rows // 200), AccessType.REF, BottleneckLevel.NONE
        else:
            if name_hash % 4 == 0:
                return base_rows, AccessType.ALL, BottleneckLevel.CRITICAL
            else:
                return max(1, base_rows // 10), AccessType.INDEX_SCAN, BottleneckLevel.NONE

    def _create_table_scan_node(
        self,
        table_name: str,
        alias: Optional[str],
        has_where: bool,
        conditions: List[str],
        has_index_hint: bool = False
    ) -> ExecutionPlanNode:
        rows, access_type, bottleneck = self._estimate_table_rows(table_name, has_where, has_index_hint)

        op_type = "全表扫描" if access_type == AccessType.ALL else "索引扫描" if access_type == AccessType.INDEX_SCAN else "范围扫描"

        desc_parts = [f"访问表 {table_name}"]
        if alias:
            desc_parts.append(f"(别名: {alias})")
        desc_parts.append(f"使用 {access_type.value} 访问方式")
        if conditions:
            desc_parts.append(f"过滤条件: {', '.join(conditions[:2])}")

        node_type = NodeType.TABLE_SCAN if access_type == AccessType.ALL else NodeType.INDEX_SCAN
        cost = rows * (1.0 if access_type == AccessType.ALL else 0.2)

        return ExecutionPlanNode(
            id=self._generate_id(),
            node_type=node_type,
            operation_type=op_type,
            table_name=table_name,
            access_type=access_type,
            estimated_rows=rows,
            estimated_cost=round(cost, 2),
            bottleneck=bottleneck,
            description=" ".join(desc_parts),
            extra_info={
                "alias": alias,
                "conditions": conditions,
            }
        )

    def _build_plan_tree(self, tree: Any) -> Tuple[ExecutionPlanNode, List[str], float]:
        warnings = []
        total_cost = 0.0

        tables = self._extract_table_names(tree)
        joins = self._detect_join_types(tree)
        has_where = self._has_where_clause(tree)
        where_conditions = self._extract_where_conditions(tree)
        has_group = self._has_group_by(tree)
        has_order = self._has_order_by(tree)
        has_limit = self._has_limit(tree)
        has_subquery_flag = self._has_subquery(tree)
        has_distinct_flag = self._has_distinct(tree)
        has_agg = self._has_aggregate_functions(tree)

        if not tables:
            tables = [("DUAL", None)]

        children = []
        table_nodes = []

        for idx, (table_name, alias) in enumerate(tables):
            tbl_has_index = (idx == 0 and has_where) or (idx > 0)
            node = self._create_table_scan_node(
                table_name, alias,
                has_where if idx == 0 else True,
                where_conditions if idx == 0 else [],
                has_index_hint=tbl_has_index
            )
            table_nodes.append(node)
            children.append(node)
            total_cost += node.estimated_cost

            if node.bottleneck == BottleneckLevel.CRITICAL:
                warnings.append(f"表 {table_name} 使用全表扫描 (ALL)，建议添加索引")

        if len(tables) > 1:
            join_children = children[:]
            children = []

            for join_idx, (join_type, _) in enumerate(joins):
                if len(join_children) >= 2:
                    right = join_children.pop()
                    left = join_children.pop()

                    join_rows = left.estimated_rows * right.estimated_rows
                    if join_type in ("LEFT", "RIGHT", "INNER"):
                        join_rows = max(left.estimated_rows, right.estimated_rows) * 2
                    join_cost = join_rows * 0.5

                    join_bottleneck = BottleneckLevel.NONE
                    join_op = "嵌套循环连接"

                    if right.access_type == AccessType.ALL:
                        join_bottleneck = BottleneckLevel.WARNING
                        join_op = "嵌套循环连接 (无索引)"
                        warnings.append(f"JOIN 操作中右表 {right.table_name} 使用全表扫描，连接性能较差")

                    join_node = ExecutionPlanNode(
                        id=self._generate_id(),
                        node_type=NodeType.NESTED_LOOP,
                        operation_type=f"{join_type} {join_op}",
                        estimated_rows=join_rows,
                        estimated_cost=round(join_cost, 2),
                        bottleneck=join_bottleneck,
                        description=f"{join_type} JOIN: 连接 {left.table_name} 与 {right.table_name}",
                        children=[left, right],
                        extra_info={"join_type": join_type}
                    )
                    total_cost += join_cost
                    join_children.append(join_node)

            children = join_children

        current_children = children

        if has_where:
            where_children = current_children
            current_children = []
            filtered_rows = max(1, int(where_children[0].estimated_rows * 0.1)) if where_children else 100
            where_cost = filtered_rows * 0.1

            where_node = ExecutionPlanNode(
                id=self._generate_id(),
                node_type=NodeType.WHERE,
                operation_type="过滤 (WHERE)",
                estimated_rows=filtered_rows,
                estimated_cost=round(where_cost, 2),
                bottleneck=BottleneckLevel.NONE,
                description=f"应用 WHERE 条件过滤: {', '.join(where_conditions[:2]) if where_conditions else '条件表达式'}",
                children=where_children,
                extra_info={"conditions": where_conditions}
            )
            total_cost += where_cost
            current_children = [where_node]

        if has_group or has_agg:
            group_children = current_children
            current_children = []
            grouped_rows = max(1, int((group_children[0].estimated_rows if group_children else 1000) * 0.05))
            group_cost = grouped_rows * 1.5

            group_bottleneck = BottleneckLevel.NONE
            if grouped_rows > 5000:
                group_bottleneck = BottleneckLevel.WARNING
                warnings.append("GROUP BY 产生大量分组，可能需要临时表排序")

            group_node = ExecutionPlanNode(
                id=self._generate_id(),
                node_type=NodeType.GROUP_BY,
                operation_type="分组聚合 (GROUP BY)",
                estimated_rows=grouped_rows,
                estimated_cost=round(group_cost, 2),
                bottleneck=group_bottleneck,
                description="执行分组聚合操作" + ("，使用临时表" if grouped_rows > 5000 else ""),
                children=group_children,
                extra_info={"has_aggregate": has_agg}
            )
            total_cost += group_cost
            current_children = [group_node]

        if has_distinct_flag:
            distinct_children = current_children
            current_children = []
            distinct_rows = max(1, int((distinct_children[0].estimated_rows if distinct_children else 100) * 0.8))
            distinct_cost = distinct_rows * 0.8

            distinct_node = ExecutionPlanNode(
                id=self._generate_id(),
                node_type=NodeType.DISTINCT,
                operation_type="去重 (DISTINCT)",
                estimated_rows=distinct_rows,
                estimated_cost=round(distinct_cost, 2),
                bottleneck=BottleneckLevel.WARNING,
                description="执行去重操作，可能需要临时表",
                children=distinct_children,
            )
            total_cost += distinct_cost
            warnings.append("DISTINCT 操作可能导致临时表使用，影响性能")
            current_children = [distinct_node]

        if has_order:
            sort_children = current_children
            current_children = []
            sort_rows = sort_children[0].estimated_rows if sort_children else 100
            sort_cost = sort_rows * (1.0 if sort_rows > 10000 else 0.5)

            sort_bottleneck = BottleneckLevel.NONE
            if sort_rows > 10000:
                sort_bottleneck = BottleneckLevel.WARNING
                warnings.append("ORDER BY 排序大量数据，考虑添加索引避免 filesort")

            sort_node = ExecutionPlanNode(
                id=self._generate_id(),
                node_type=NodeType.SORT,
                operation_type="排序 (ORDER BY)",
                estimated_rows=sort_rows,
                estimated_cost=round(sort_cost, 2),
                bottleneck=sort_bottleneck,
                description=f"对 {sort_rows} 行数据进行排序",
                children=sort_children,
            )
            total_cost += sort_cost
            current_children = [sort_node]

        if has_limit:
            limit_children = current_children
            current_children = []
            limit_rows = 100
            limit_cost = 0.01

            limit_node = ExecutionPlanNode(
                id=self._generate_id(),
                node_type=NodeType.LIMIT,
                operation_type="分页 (LIMIT)",
                estimated_rows=limit_rows,
                estimated_cost=round(limit_cost, 2),
                bottleneck=BottleneckLevel.NONE,
                description="应用 LIMIT 限制返回行数",
                children=limit_children,
            )
            total_cost += limit_cost
            current_children = [limit_node]

        if has_subquery_flag:
            warnings.append("查询包含子查询，建议优化为 JOIN 以获得更好性能")

        root = ExecutionPlanNode(
            id=self._generate_id(),
            node_type=NodeType.SELECT,
            operation_type="查询结果",
            estimated_rows=current_children[0].estimated_rows if current_children else 1,
            estimated_cost=round(total_cost, 2),
            bottleneck=BottleneckLevel.NONE,
            description="SQL 查询执行计划根节点",
            children=current_children,
            extra_info={
                "table_count": len(tables),
                "join_count": len(joins),
                "has_where": has_where,
                "has_group_by": has_group,
                "has_order_by": has_order,
                "has_limit": has_limit,
            }
        )

        return root, warnings, round(total_cost, 2)

    def _explain_sync(self, request: ExplainRequest) -> ExplainResponse:
        sql_valid, errors, tree = self._validate_sql(request.sql, request.dialect)

        if not sql_valid:
            dummy_root = ExecutionPlanNode(
                id=self._generate_id(),
                node_type=NodeType.SELECT,
                operation_type="SQL 语法错误",
                estimated_rows=0,
                estimated_cost=0,
                bottleneck=BottleneckLevel.CRITICAL,
                description="SQL 语法验证失败，无法生成执行计划",
            )
            return ExplainResponse(
                success=False,
                dialect=request.dialect,
                plan_tree=dummy_root,
                total_cost=0,
                warnings=[],
                sql_valid=False,
                validation_errors=errors,
            )

        plan_tree, warnings, total_cost = self._build_plan_tree(tree)

        return ExplainResponse(
            success=True,
            dialect=request.dialect,
            plan_tree=plan_tree,
            total_cost=total_cost,
            warnings=warnings,
            sql_valid=True,
            validation_errors=[],
        )

    async def explain(self, request: ExplainRequest) -> ExplainResponse:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._explain_sync,
            request
        )

    def shutdown(self):
        self._executor.shutdown(wait=False)
        logger.info("ExplainService shutdown")


explain_service = ExplainService()


__all__ = ["ExplainService", "explain_service"]
