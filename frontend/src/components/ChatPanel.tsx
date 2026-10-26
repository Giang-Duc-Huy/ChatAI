import { useState } from "react";
import type { ChatMessage } from "../types";
import { MessageList } from "./MessageList";
import { MicButton } from "./MicButton";
import { SettingsBar } from "./SettingsBar";

type Props = {
  indexStatus: string;
  messages: ChatMessage[];
  listening: boolean;
  topK: number;
  minScore: number;
  rate: number;
  onFiles: (files: FileList) => void;
  onAsk: (q: string) => void;
  onMic: () => void;
  onTopK: (n: number) => void;
  onMinScore: (n: number) => void;
  onRate: (n: number) => void;
};

export function ChatPanel({
  indexStatus,
  messages,
  listening,
  topK,
  minScore,
  rate,
  onFiles,
  onAsk,
  onMic,
  onTopK,
  onMinScore,
  onRate,
}: Props) {
  const [q, setQ] = useState("");

  const send = () => {
    const text = q;
    setQ("");
    onAsk(text);
  };

  return (
    <section className="card">
      <div className="row" style={{ margin: "0 0 8px", alignItems: "center" }}>
        <label className="mu">
          Tài liệu riêng cho phiên này (PDF, HTML hoặc TXT):{" "}
          <input
            type="file"
            multiple
            accept=".pdf,.html,.htm,.txt"
            onChange={(e) => e.target.files && onFiles(e.target.files)}
          />
        </label>
      </div>
      <div className="mu">Tài liệu không được gửi lên máy chủ; khi tải tài liệu, câu hỏi chỉ dùng bộ tài liệu này.</div>
      <div className="mu">{indexStatus}</div>
      <MessageList messages={messages} />
      <div className="row">
        <input
          id="q"
          placeholder="Hỏi về tuyển sinh…"
          autoComplete="off"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
        />
        <button className="p" onClick={send}>
          Gửi
        </button>
        <MicButton listening={listening} onClick={onMic} />
      </div>
      <SettingsBar
        topK={topK}
        minScore={minScore}
        rate={rate}
        onTopK={onTopK}
        onMinScore={onMinScore}
        onRate={onRate}
      />
    </section>
  );
}
