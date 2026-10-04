export type Role = "user" | "assistant";

export interface SourceItem {
  doc_id: string;
  title: string;
  year?: number | null;
  page?: number | null;
  snippet: string;
  score: number;
}

export interface TimingsMs {
  retrieval: number;
  llm: number;
  tts?: number;
  total: number;
}

export interface ChatResponse {
  answer: string;
  sources: SourceItem[];
  answerable: boolean;
  timings_ms: TimingsMs;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  sources?: SourceItem[];
  answerable?: boolean;
  timings_ms?: TimingsMs;
  error?: boolean;
  latency?: {
    stt_ms?: number;
    request_ms?: number;
    audio_ready_ms?: number;
    to_first_audio_ms?: number;
  };
}

export interface HealthResponse {
  status: string;
  vector_db_ready: boolean;
  chunk_count: number;
  embedding_loaded: boolean;
  llm_configured: boolean;
  tts_configured: boolean;
  features: Record<string, boolean>;
}
