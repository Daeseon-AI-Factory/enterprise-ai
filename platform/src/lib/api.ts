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

// Health
export const healthApi = {
  check: () => api.get<{ status: string; mode: string; model: string }>("/health"),
};

export default api;
