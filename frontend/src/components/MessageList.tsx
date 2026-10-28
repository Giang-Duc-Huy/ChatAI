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
              Nguồn:{" "}
              {m.sources.map((c, i) => (
                <span key={`${c.doc}-${c.section}-${i}`}>
                  {i > 0 ? "  " : ""}
                  [
                  {c.url && /^https?:\/\//i.test(c.url) ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer">
                      {c.doc}
                    </a>
                  ) : (
                    c.doc
                  )}
                  {" – "}
                  {c.section}
                  {" – "}
                  {c.date}]
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
