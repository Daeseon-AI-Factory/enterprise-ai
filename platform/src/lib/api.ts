import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// Auth API
export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string; username: string }>("/auth/login", { username, password }),
};

// Chat
export const chatApi = {
  send: (message: string, conversationId?: string) =>
    api.post<{ reply: string; conversation_id: string }>("/chat", {
      message,
      conversation_id: conversationId,
    }),

  stream: (message: string, conversationId?: string) => {
    const token = localStorage.getItem("auth_token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
  },

  listConversations: () =>
    api.get<Array<{ id: string; preview: string; message_count: number; modified: number }>>(
      "/chat/conversations"
    ),

  getConversation: (id: string) =>
    api.get<Array<{ role: string; content: string }>>(`/chat/conversations/${id}`),

  deleteConversation: (id: string) =>
    api.delete(`/chat/conversations/${id}`),
};

// RAG
export const ragApi = {
  upload: (file: File, collection: string = "default") => {
    const form = new FormData();
    form.append("file", file);
    form.append("collection", collection);
    return api.post("/rag/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  query: (query: string, collection: string = "default", topK: number = 5) =>
    api.post<{ answer: string; sources: Array<{ filename: string; score: number }> }>(
      "/rag/query",
      { query, collection, top_k: topK }
    ),

  listCollections: () =>
    api.get<Array<{ name: string; count: number }>>("/rag/collections"),

  listDocuments: (collection: string) =>
    api.get<Array<{ filename: string; doc_id: string; chunks: number }>>(
      `/rag/collections/${collection}/documents`
    ),

  getDocumentChunks: (collection: string, docId: string) =>
    api.get<Array<{ chunk_index: number; content: string }>>(
      `/rag/collections/${collection}/documents/${docId}/chunks`
    ),

  deleteDocument: (collection: string, docId: string) =>
    api.delete(`/rag/collections/${collection}/documents/${docId}`),

  deleteCollection: (id: string) => api.delete(`/rag/collections/${id}`),
};

// Text-to-SQL
export const sqlApi = {
  generate: (question: string, schemaId?: string) =>
    api.post<{ sql: string; explanation: string }>("/text2sql/generate", {
      question,
      schema_id: schemaId,
    }),

  execute: (sql: string, connection?: Record<string, unknown>) =>
    api.post("/text2sql/execute", { sql, confirmed: true, connection }),

  registerSchema: (schemaId: string, tables: unknown[], description?: string) =>
    api.post("/text2sql/schema", { schema_id: schemaId, tables, description }),

  listSchemas: () =>
    api.get<Array<{ schema_id: string; table_count: number; description?: string }>>("/text2sql/schemas"),

  deleteSchema: (schemaId: string) =>
    api.delete(`/text2sql/schemas/${schemaId}`),

  testConnection: (params: { db_type: string; host: string; port: number; name: string; user: string; password: string }) =>
    api.post<{ ok: boolean; error?: string }>("/text2sql/connection/test", params),

  discoverSchema: (params: { schema_id: string; db_type: string; host: string; port: number; name: string; user: string; password: string; owner?: string; description?: string }) =>
    api.post<{ schema_id: string; tables: number; status: string }>("/text2sql/schema/discover", params),
};

// Codegen
export const codegenApi = {
  generate: (prompt: string, language: string = "python", framework?: string, projectId?: string) =>
    api.post<{ code: string; language: string; explanation: string }>("/codegen/generate", {
      prompt,
      language,
      framework,
      project_id: projectId,
    }),

  listTemplates: () => api.get("/codegen/templates"),
};

// Confluence
export const confluenceApi = {
  sync: (params: {
    base_url: string;
    username: string;
    api_token: string;
    space_key: string;
    collection?: string;
    labels?: string[];
    full_sync?: boolean;
  }) =>
    api.post<{
      status: string;
      space_key: string;
      collection: string;
      synced: number;
      total_chunks: number;
    }>("/confluence/sync", params),

  listSpaces: (params: { base_url: string; username: string; api_token: string }) =>
    api.post<Array<{ key: string; name: string; type: string }>>("/confluence/spaces", params),

  registerPage: (params: {
    page_url: string;
    base_url: string;
    username: string;
    api_token: string;
    collection?: string;
  }) =>
    api.post<{ status: string; title?: string; chunks?: number; message?: string }>(
      "/confluence/register-page",
      params
    ),
};

// Review (Code Review + Edge Case)
export const reviewApi = {
  codeReview: (code: string, language?: string, context?: string) =>
    api.post<{ review: string; language: string }>("/review/code", {
      code,
      language,
      context,
    }),

  edgeCases: (code: string, language?: string, context?: string) =>
    api.post<{ analysis: string; language: string }>("/review/edge-cases", {
      code,
      language,
      context,
    }),
};

// Build & Deploy
export const buildApi = {
  run: (projectPath: string, command: string = "npm run build", name?: string) =>
    api.post("/build/run", {
      project_path: projectPath,
      command,
      name,
    }),

  deploy: (projectPath: string, command: string, name?: string) =>
    api.post("/build/deploy", {
      project_path: projectPath,
      command,
      name,
    }),

  history: (limit: number = 20) =>
    api.get<Array<{
      build_id: string;
      name: string;
      status: string;
      command: string;
      started_at: string;
      finished_at: string;
      return_code: number;
    }>>(`/build/history?limit=${limit}`),

  detail: (buildId: string) => api.get(`/build/history/${buildId}`),
};

// Settings (persistent config)
export const settingsApi = {
  get: (key: string) => api.get<{ key: string; data: unknown }>(`/settings/${key}`),
  save: (key: string, data: unknown) => api.put("/settings", { key, data }),
  delete: (key: string) => api.delete(`/settings/${key}`),
  list: () => api.get<{ keys: string[] }>("/settings"),
};

// Health
export const healthApi = {
  check: () =>
    api.get<{ status: string; mode: string; model: string }>("/../health"),
};

// Stats (dashboard)
export const statsApi = {
  get: () =>
    api.get<{
      status: string; mode: string; model: string;
      collections: Array<{ name: string; count: number }>;
      conversations: number;
      schemas: number;
    }>("/stats"),
};

// Analyze (RAG + DB combined)
export const analyzeApi = {
  query: (params: {
    question: string;
    schema_id?: string;
    collections?: string[];
    run_sql?: boolean;
  }) => api.post<{
    answer: string;
    rag_sources: Array<{ collection: string; filename: string; score: number }>;
    db_sql: string;
    db_rows: Record<string, unknown>[];
    db_row_count: number;
  }>("/analyze", params),
};

// Git RAG
export const gitApi = {
  indexRepo: (params: { repo_path: string; repo_url?: string; collection?: string }) =>
    api.post<{ job_id: string; status: string }>("/git/index", params),
  indexStatus: (jobId: string) =>
    api.get<{ job_id: string; status: string; files_indexed: number; chunks_indexed: number; message: string }>(
      `/git/index/${jobId}`
    ),
  listCollections: () =>
    api.get<Array<{ name: string; count: number }>>("/git/collections"),
};

export default api;
