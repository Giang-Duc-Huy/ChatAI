import type { ChatMessage, ChatResponse, HealthResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Không kết nối được máy chủ");
  return res.json();
}

export async function postChat(
  question: string,
  sessionId: string,
  history: ChatMessage[],
  signal?: AbortSignal
): Promise<ChatResponse> {
  const payload = {
    question,
    session_id: sessionId,
    history: history
      .filter((m) => !m.error)
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content })),
  };
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Lỗi chat (${res.status})`);
  }
  return res.json();
}

export async function postTts(text: string, signal?: AbortSignal): Promise<{
  audioBase64: string;
  timings_ms: { tts: number; total: number };
  cached: boolean;
}> {
  const res = await fetch(`${API_BASE}/api/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Lỗi TTS (${res.status})`);
  }
  const data = await res.json();
  return {
    audioBase64: data.audio_content,
    timings_ms: data.timings_ms,
    cached: data.cached,
  };
}
