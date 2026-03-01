import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "http://localhost:8000",
});

export interface Dialect {
  id: number;
  code: string;
  label: string;
}

export async function listDialects(): Promise<Dialect[]> {
  const response = await http.get<Dialect[]>("/api/dialects");
  return response.data;
}
