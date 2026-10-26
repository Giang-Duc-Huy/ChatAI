import type { ChatResponse } from "../types";

export async function postChat(question: string, topK: number, minScore: number): Promise<ChatResponse> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK, min_score: minScore }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = typeof body.detail === "string" ? body.detail : r.statusText;
    throw new Error(detail || String(r.status));
  }
  return body as ChatResponse;
}
