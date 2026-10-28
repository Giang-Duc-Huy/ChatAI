import type { ChatResponse, VisemeName } from "../types";

export type TtsResponse = {
  audio_b64: string;
  mime: string;
  visemes: { t0: number; t1: number; viseme: VisemeName | null; lip: boolean }[];
};

export async function postChat(question: string, topK: number, minScore: number): Promise<ChatResponse> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: question, top_k: topK, min_score: minScore }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = typeof body.detail === "string" ? body.detail : r.statusText;
    throw new Error(detail || String(r.status));
  }
  return body as ChatResponse;
}

export async function postTts(text: string): Promise<TtsResponse> {
  const r = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = typeof body.detail === "string" ? body.detail : r.statusText;
    throw new Error(detail || String(r.status));
  }
  return body as TtsResponse;
}
