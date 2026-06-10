/**
 * SQL Execution Plan types and API client.
 * Mirrors the Pydantic models defined in backend/app/models/schemas.py
 */

import axios from 'axios'

export enum ExplainOperationType {
  SELECT = 'SELECT',
  FROM = 'FROM',
  WHERE = 'WHERE',
  JOIN = 'JOIN',
  LEFT_JOIN = 'LEFT JOIN',
  RIGHT_JOIN = 'RIGHT JOIN',
  INNER_JOIN = 'INNER JOIN',
  FULL_JOIN = 'FULL JOIN',
  CROSS_JOIN = 'CROSS JOIN',
  GROUP_BY = 'GROUP BY',
  ORDER_BY = 'ORDER BY',
  HAVING = 'HAVING',
  LIMIT = 'LIMIT',
  DISTINCT = 'DISTINCT',
  UNION = 'UNION',
  SUBQUERY = 'SUBQUERY',
  AGGREGATE = 'AGGREGATE',
  SORT = 'SORT',
  TABLE_SCAN = 'TABLE SCAN',
  INDEX_SCAN = 'INDEX SCAN',
  TEMP_TABLE = 'TEMP TABLE',
  NESTED_LOOP = 'NESTED LOOP',
  HASH_JOIN = 'HASH JOIN',
  SORT_MERGE_JOIN = 'SORT MERGE JOIN',
}

export enum ExplainAccessType {
  FULL_SCAN = 'full_scan',
  INDEX_SCAN = 'index_scan',
  INDEX_SEEK = 'index_seek',
  TEMP_TABLE = 'temp_table',
  MEMORY = 'memory',
}

export interface ExplainPlanNode {
  id: string
  operation: ExplainOperationType
  table_name: string | null
  estimated_rows: number
  access_type: ExplainAccessType | null
  cost: number
  description: string | null
  children: ExplainPlanNode[]
}

export interface ExplainRequest {
  sql: string
  dialect: string
}

export interface ExplainResponse {
  success: boolean
  plan: ExplainPlanNode
  total_cost: number
  warnings: string[]
  dialect: string
}

const API_BASE_URL = import.meta.env.PROD
  ? window.location.origin
  : 'http://localhost:8000'

export async function explainSql(sql: string, dialect: string): Promise<ExplainResponse> {
  const response = await axios.post<ExplainResponse>(
    `${API_BASE_URL}/api/explain`,
    {
      sql,
      dialect,
    }
  )
  return response.data
}
