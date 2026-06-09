/**
 * HTTP API client for SQL Explain (execution plan) endpoint.
 *
 * The `ExplainNode` interface mirrors the backend Pydantic `ExplainNode`
 * model defined in `backend/app/models/schemas.py`.
 */

export type AccessType =
  | 'full_scan'
  | 'index_scan'
  | 'temp_table'
  | 'const'
  | 'ref'
  | 'unknown'

export interface ExplainNode {
  id: string
  operation: string
  table?: string | null
  estimated_rows: number
  access_type: AccessType
  cost: number
  bottleneck: boolean
  details?: Record<string, unknown> | null
  children: ExplainNode[]
}

export interface ExplainResponse {
  success: boolean
  dialect: string
  root: ExplainNode
  total_cost: number
  warnings: string[]
}

export interface ExplainErrorResponse {
  success: false
  error: {
    code: number
    message: string
    details?: Record<string, unknown>
  }
}

export interface ExplainRequestPayload {
  sql: string
  dialect: string
}

/**
 * Call POST /api/explain to obtain a mocked SQL execution plan tree.
 * Throws Error with the user-friendly server message on failure.
 */
export async function fetchExplainPlan(
  payload: ExplainRequestPayload,
): Promise<ExplainResponse> {
  const baseUrl = import.meta.env.PROD ? '' : ''
  const res = await fetch(`${baseUrl}/api/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const text = await res.text()
  let data: ExplainResponse | ExplainErrorResponse
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error(`服务器返回了无效响应 (${res.status})`)
  }

  if (!res.ok || (data as ExplainErrorResponse).success === false) {
    const err = (data as ExplainErrorResponse).error
    throw new Error(err?.message || `请求失败 (${res.status})`)
  }

  return data as ExplainResponse
}
