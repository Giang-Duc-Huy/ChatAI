import { useEffect, useState } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { getHealth } from "./api/client";
import type { HealthResponse } from "./types";

function sessionId() {
  const key = "admissions_session_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sid] = useState(sessionId);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div className="app-shell">
      <header className="hero-brand">
        <p className="brand">Đại học ABC</p>
        <h1>Trợ lý tư vấn tuyển sinh</h1>
        <p className="tagline">Hỏi về ngành, phương thức, học phí và chỉ tiêu — có nguồn dẫn.</p>
        {health && (
          <p className="health-line">
            {health.vector_db_ready
              ? `Sẵn sàng · ${health.chunk_count} đoạn tài liệu`
              : "Chưa có dữ liệu — chạy ingest trước"}
            {!health.llm_configured ? " · thiếu ANTHROPIC_API_KEY" : ""}
          </p>
        )}
      </header>
      <main>
        <ChatPanel sessionId={sid} />
      </main>
    </div>
  );
}
