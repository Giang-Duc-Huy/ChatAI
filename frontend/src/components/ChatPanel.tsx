import { useState } from "react";
import type { ChatMessage } from "../types";
import { MessageList } from "./MessageList";
import { MicButton } from "./MicButton";
import { SettingsBar } from "./SettingsBar";

type Props = {
  messages: ChatMessage[];
  isThinking: boolean;
  listening: boolean;
  topK: number;
  minScore: number;
  rate: number;
  onAsk: (q: string) => void;
  onMic: () => void;
  onTopK: (n: number) => void;
  onMinScore: (n: number) => void;
  onRate: (n: number) => void;
};

export function ChatPanel({
  messages,
  isThinking,
  listening,
  topK,
  minScore,
  rate,
  onAsk,
  onMic,
  onTopK,
  onMinScore,
  onRate,
}: Props) {
  const [q, setQ] = useState("");

  const send = () => {
    const text = q.trim();
    if (!text || isThinking) return;
    setQ("");
    onAsk(text);
  };

  return (
    <section className="card">
      <MessageList messages={messages} isThinking={isThinking} />
      <div className="row">
        <input
          id="q"
          placeholder="Hỏi về tuyển sinh…"
          autoComplete="off"
          maxLength={1000}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="p" onClick={send} disabled={isThinking || !q.trim()}>
          Gửi
        </button>
        <MicButton listening={listening} disabled={isThinking} onClick={onMic} />
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
