export interface ModelConfig {
  id: number;
  name: string;
  provider: string;
  base_url: string;
  model_name: string;
  api_key_masked: string;
  extra: Record<string, unknown>;
}

export interface ModelConfigInput {
  name: string;
  provider: "openai_compat" | "gemini" | "replicate";
  base_url?: string;
  model_name: string;
  api_key?: string;
  extra?: Record<string, unknown>;
}

export interface Template {
  id: number;
  name: string;
  category: string;
  system_prompt: string;
  user_template: string;
  builtin: boolean;
}

export interface GenerateRequest {
  model_id: number;
  template_id?: number | null;
  system_prompt?: string | null;
  user_prompt?: string;
  user_input?: string;
  temperature?: number;
  render?: boolean;
}

export interface GenerateResponse {
  generated_code: string;
  svg: string | null;
  status: "success" | "code_only" | "error";
  error: string;
}

export interface GenerationRecord {
  id: number;
  model_id: number;
  template_id: number | null;
  user_input: string;
  generated_code: string;
  status: string;
  error: string;
  created_at: string;
}

const BASE = "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listModels: () => req<ModelConfig[]>("/api/models"),
  createModel: (body: ModelConfigInput) =>
    req<ModelConfig>("/api/models", { method: "POST", body: JSON.stringify(body) }),
  updateModel: (id: number, body: ModelConfigInput) =>
    req<ModelConfig>(`/api/models/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteModel: (id: number) => req<void>(`/api/models/${id}`, { method: "DELETE" }),

  listTemplates: () => req<Template[]>("/api/templates"),
  createTemplate: (body: Omit<Template, "id" | "builtin">) =>
    req<Template>("/api/templates", { method: "POST", body: JSON.stringify(body) }),
  updateTemplate: (id: number, body: Omit<Template, "id" | "builtin">) =>
    req<Template>(`/api/templates/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteTemplate: (id: number) => req<void>(`/api/templates/${id}`, { method: "DELETE" }),

  generate: (body: GenerateRequest) =>
    req<GenerateResponse>("/api/generate", { method: "POST", body: JSON.stringify(body) }),
  render: (code: string) =>
    req<GenerateResponse>("/api/generate/render", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  downloadFormat: (code: string, fmt: "png" | "pdf" | "svg") =>
    fetch("/api/generate/download?fmt=" + fmt, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    }),

  listHistory: (limit = 50) => req<GenerationRecord[]>(`/api/history?limit=${limit}`),
  clearHistory: () => req<void>("/api/history", { method: "DELETE" }),
  deleteHistory: (id: number) => req<void>(`/api/history/${id}`, { method: "DELETE" }),
};
