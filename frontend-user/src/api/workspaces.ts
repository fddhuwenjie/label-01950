import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "http://localhost:8000",
});

export interface Workspace {
  id: number;
  name: string;
  dialect: string;
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const response = await http.get<Workspace[]>("/api/workspaces");
  return response.data;
}

export async function createWorkspace(payload: { name: string; dialect: string }): Promise<Workspace> {
  const response = await http.post<Workspace>("/api/workspaces", payload);
  return response.data;
}

export async function updateWorkspace(
  id: number,
  payload: { name: string; dialect: string }
): Promise<Workspace> {
  const response = await http.put<Workspace>(`/api/workspaces/${id}`, payload);
  return response.data;
}

export async function deleteWorkspace(id: number): Promise<void> {
  await http.delete(`/api/workspaces/${id}`);
}
