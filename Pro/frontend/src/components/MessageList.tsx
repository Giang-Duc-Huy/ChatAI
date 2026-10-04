import type { ChatMessage } from "../types";
import { SourceList } from "./SourceList";

interface Props {
  messages: ChatMessage[];
  onRetry?: (msg: ChatMessage) => void;
}

export function MessageList({ messages, onRetry }: Props) {
  if (!messages.length) {
    return (
      <div className="empty-hint">
        Hãy hỏi về ngành, phương thức xét tuyển, học phí hoặc chỉ tiêu tuyển sinh.
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((m) => (
        <div key={m.id} className={`msg msg-${m.role}${m.error ? " msg-error" : ""}`}>
          <div className="msg-role">{m.role === "user" ? "Bạn" : "Trợ lý"}</div>
          <div className="msg-body">{m.content}</div>
          {m.sources && <SourceList sources={m.sources} />}
          {m.error && onRetry && (
            <button type="button" className="retry-btn" onClick={() => onRetry(m)}>
              Thử lại
            </button>
          )}
          {m.timings_ms && !m.error && (
            <div className="msg-meta">
              {Math.round(m.timings_ms.total)} ms
              {m.answerable === false ? " · không đủ ngữ liệu" : ""}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
