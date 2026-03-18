import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Chat
export const chatApi = {
  send: (message: string, conversationId?: string) =>
    api.post<{ reply: string; conversation_id: string }>("/chat", {
      message,
      conversation_id: conversationId,
    }),

  stream: (message: string, conversationId?: string) =>
    fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    }),
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

  deleteCollection: (id: string) => api.delete(`/rag/collections/${id}`),
};

// Text-to-SQL
export const sqlApi = {
  generate: (question: string, schemaId?: string) =>
    api.post<{ sql: string; explanation: string }>("/text2sql/generate", {
      question,
      schema_id: schemaId,
    }),

  execute: (sql: string) =>
    api.post("/text2sql/execute", { sql, confirmed: true }),

  registerSchema: (schemaId: string, tables: unknown[], description?: string) =>
    api.post("/text2sql/schema", { schema_id: schemaId, tables, description }),

  listSchemas: () => api.get("/text2sql/schemas"),
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

// Health — endpoint is at root /health, not under /api
export const healthApi = {
  check: () =>
    axios.get<{ status: string; mode: string; model: string }>("/health"),
};

export default api;
