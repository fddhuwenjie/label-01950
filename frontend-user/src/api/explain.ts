import axios from 'axios'
import type { ExplainRequest, ExplainResponse } from '@/types/executionPlan'

const API_BASE_URL = import.meta.env.PROD
  ? window.location.origin
  : 'http://localhost:8000'

export async function explainSql(request: ExplainRequest): Promise<ExplainResponse> {
  const response = await axios.post<ExplainResponse>(`${API_BASE_URL}/api/explain`, request)
  return response.data
}
