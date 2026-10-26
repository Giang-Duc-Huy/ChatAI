import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = 1e9;
  }, [messages]);

  return (
    <div id="log" ref={logRef}>
      {messages.map((m) => (
        <div key={m.id} className={`m ${m.role === "user" ? "u" : "b"}`}>
          {m.text}
          {m.sources && m.sources.length > 0 && (
            <div className="src">
              Nguồn: {m.sources.map((c) => `[${c.doc} – ${c.section} – ${c.date}]`).join("  ")}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
