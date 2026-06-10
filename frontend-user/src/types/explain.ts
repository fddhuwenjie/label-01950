/**
 * TypeScript interfaces for SQL Execution Plan visualization.
 * Mirrors the backend Pydantic models in schemas.py.
 */

export interface ExplainNode {
  id: string
  operation_type: string
  table_name: string | null
  estimated_rows: number
  access_type: string
  cost: number
  details: string | null
  children: ExplainNode[]
}

export interface ExplainRequest {
  sql: string
  dialect: string
}

export interface ExplainResponse {
  success: boolean
  root: ExplainNode | null
  error: string | null
}

export type AccessTypeColor = 'red' | 'green' | 'yellow' | 'blue'

export function getAccessTypeColor(accessType: string): AccessTypeColor {
  if (accessType === 'full_table_scan') return 'red'
  if (accessType === 'index_scan' || accessType === 'index_seek') return 'green'
  if (accessType === 'temporary_table') return 'yellow'
  return 'blue'
}

export function getAccessTypeLabel(accessType: string): string {
  const labels: Record<string, string> = {
    full_table_scan: '全表扫描',
    index_scan: '索引扫描',
    index_seek: '索引查找',
    temporary_table: '临时表',
    hash_join: 'Hash Join',
    nested_loop: 'Nested Loop',
    merge_join: 'Merge Join',
    sort: '排序',
    filter: '过滤',
    aggregate: '聚合',
    subquery: '子查询',
    table_scan: '表扫描',
  }
  return labels[accessType] || accessType
}
