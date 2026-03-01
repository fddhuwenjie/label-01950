import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "http://localhost:8000",
});

export interface CompletionItem {
  id: number;
  category: string;
  value: string;
  dialect: string;
  workspace_id: number | null;
}

export async function listCompletions(params: {
  dialect: string;
  workspace_id?: number | null;
}): Promise<CompletionItem[]> {
  const response = await http.get<CompletionItem[]>("/api/completions", { params });
  return response.data;
}

export async function createCompletion(payload: {
  category: string;
  value: string;
  dialect: string;
  workspace_id?: number | null;
}): Promise<CompletionItem> {
  const response = await http.post<CompletionItem>("/api/completions", payload);
  return response.data;
}
