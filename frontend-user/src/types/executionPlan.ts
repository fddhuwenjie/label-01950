export enum AccessType {
  FULL_SCAN = 'ALL',
  INDEX_SCAN = 'index',
  RANGE_SCAN = 'range',
  REF = 'ref',
  EQ_REF = 'eq_ref',
  CONST = 'const',
  SYSTEM = 'system',
  UNIQUE_SUBQUERY = 'unique_subquery',
  INDEX_SUBQUERY = 'index_subquery',
}

export enum NodeType {
  SELECT = 'SELECT',
  JOIN = 'JOIN',
  TABLE_SCAN = 'TABLE_SCAN',
  INDEX_SCAN = 'INDEX_SCAN',
  WHERE = 'WHERE',
  GROUP_BY = 'GROUP_BY',
  ORDER_BY = 'ORDER_BY',
  HAVING = 'HAVING',
  LIMIT = 'LIMIT',
  SUBQUERY = 'SUBQUERY',
  DERIVED = 'DERIVED',
  TEMPORARY_TABLE = 'TEMPORARY_TABLE',
  NESTED_LOOP = 'NESTED_LOOP',
  HASH_JOIN = 'HASH_JOIN',
  MERGE_JOIN = 'MERGE_JOIN',
  AGGREGATE = 'AGGREGATE',
  SORT = 'SORT',
  DISTINCT = 'DISTINCT',
  UNION = 'UNION',
}

export enum BottleneckLevel {
  NONE = 'none',
  WARNING = 'warning',
  CRITICAL = 'critical',
}

export interface ExecutionPlanNode {
  id: string
  node_type: NodeType
  operation_type: string
  table_name: string | null
  access_type: AccessType | null
  estimated_rows: number
  estimated_cost: number
  bottleneck: BottleneckLevel
  description: string
  children: ExecutionPlanNode[]
  extra_info: Record<string, unknown>
}

export interface ExplainResponse {
  success: boolean
  dialect: string
  plan_tree: ExecutionPlanNode
  total_cost: number
  warnings: string[]
  sql_valid: boolean
  validation_errors: string[]
}

export interface ExplainRequest {
  sql: string
  dialect: string
}

export interface TreeNode {
  name: string
  nodeData: ExecutionPlanNode
  children?: TreeNode[]
}
