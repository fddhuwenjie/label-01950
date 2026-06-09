/**
 * HTTP API client for SQL Explain endpoint.
 */
import axios from 'axios'
import type { ExplainRequest, ExplainResponse } from '@/types/explain'

const apiClient = axios.create({
  baseURL: import.meta.env.PROD ? '' : 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function fetchExplainPlan(request: ExplainRequest): Promise<ExplainResponse> {
  const response = await apiClient.post<ExplainResponse>('/api/explain', request)
  return response.data
}
