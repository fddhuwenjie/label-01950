/**
 * Types and API client for SQL execution plan.
 */

export type ExplainNodeType =
  | 'SELECT'
  | 'FROM'
  | 'JOIN'
  | 'WHERE'
  | 'GROUP_BY'
  | 'ORDER_BY'
  | 'LIMIT'
  | 'SUBQUERY'
  | 'TABLE_SCAN'
  | 'INDEX_SCAN'
  | 'TEMP_TABLE'
  | 'SORT'
  | 'AGGREGATE'
  | 'HASH_JOIN'
  | 'NESTED_LOOP_JOIN'
  | 'MERGE_JOIN'

export interface ExplainPlanNode {
  id: string
  operation_type: ExplainNodeType
  table_name: string | null
  estimated_rows: number
  access_type: string | null
  cost: number
  description: string
  is_bottleneck: boolean
  bottleneck_reason: string | null
  children: ExplainPlanNode[]
}

export interface ExplainResponse {
  success: boolean
  plan: ExplainPlanNode
  total_cost: number
  total_estimated_rows: number
  has_bottlenecks: boolean
  bottleneck_count: number
}

export interface ExplainRequest {
  sql: string
  dialect: string
}

const API_BASE_URL = import.meta.env.PROD
  ? ''
  : 'http://localhost:8000'

export async function explainSql(request: ExplainRequest): Promise<ExplainResponse> {
  const response = await fetch(`${API_BASE_URL}/api/explain`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    const errorMessage = errorData?.error?.message || '请求失败'
    throw new Error(errorMessage)
  }

  return response.json()
}
