import { useCallback, useRef, useState } from "react";
import { postChat } from "./api/client";
import { Avatar3D } from "./components/Avatar3D";
import { ChatPanel } from "./components/ChatPanel";
import { useSpeechRecognition } from "./hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "./hooks/useSpeechSynthesis";
import { nfc } from "./lib/text";
import type { AvatarState, ChatMessage } from "./types";

let msgId = 0;
const nextId = () => String(++msgId);

export default function App() {
  const [avatarState, setAvatarState] = useState<AvatarState>("Chờ");
  const [isThinking, setIsThinking] = useState(false);
  const [modelStatus, setModelStatus] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: nextId(),
      role: "bot",
      text: "Xin chào! Bạn có thể hỏi mình về thông tin tuyển sinh UIT.",
    },
  ]);
  const [topK, setTopK] = useState(5);
  const [minScore, setMinScore] = useState(0.35);
  const [rate, setRate] = useState(1);

  const topKRef = useRef(topK);
  const minScoreRef = useRef(minScore);
  const isThinkingRef = useRef(false);
  topKRef.current = topK;
  minScoreRef.current = minScore;

  const { speak, stop, replay, playingRef, timelineRef, clock0Ref } = useSpeechSynthesis({
    rate,
    onState: setAvatarState,
  });

  const add = useCallback((msg: Omit<ChatMessage, "id">) => {
    setMessages((prev) => [...prev, { ...msg, id: nextId() }]);
  }, []);

  const ask = useCallback(
    (raw: string) => {
      const q = nfc(raw).trim();
      if (!q || isThinkingRef.current) return;
      isThinkingRef.current = true;
      setIsThinking(true);
      add({ role: "user", text: q });
      setAvatarState("Nghĩ");
      void (async () => {
        try {
          const a = await postChat(q, topKRef.current, minScoreRef.current);
          const lat = a.latency || {};
          const meta = [
            lat.retrieval != null ? `Tra cứu ${Math.round(lat.retrieval)} ms` : undefined,
            lat.llm != null ? `AI ${Math.round(lat.llm)} ms` : undefined,
          ]
            .filter((value) => value !== undefined)
            .join(" · ");
          add({
            role: "bot",
            text: a.answer,
            meta: meta || undefined,
            sources: (a.sources || []).map((s) => ({
              doc: s.doc_title,
              section: s.section,
              date: s.date,
              url: s.url,
            })),
          });
          speak(a.answer);
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          add({ role: "bot", text: `Không thể xử lý câu hỏi: ${message}` });
          setAvatarState("Chờ");
        } finally {
          isThinkingRef.current = false;
          setIsThinking(false);
        }
      })();
    },
    [add, speak],
  );

  const { listening, toggle } = useSpeechRecognition({
    onTranscript: ask,
    onMessage: (text) => add({ role: "bot", text }),
    onState: setAvatarState,
    stopSpeak: stop,
  });

  return (
    <main>
      <section className="card">
        <h1>Trợ lý tuyển sinh UIT</h1>
        <Avatar3D
          state={avatarState}
          playingRef={playingRef}
          timelineRef={timelineRef}
          clock0Ref={clock0Ref}
          onModelStatus={setModelStatus}
        />
        <span className="status-pill">{avatarState}</span>
        <div className="row">
          <button onClick={stop}>Dừng</button>
          <button onClick={replay}>Phát lại</button>
          <button
            onClick={() =>
              speak("Xin chào, mình là trợ lý tuyển sinh. Bạn muốn hỏi về ngành học, chỉ tiêu hay học phí?")
            }
          >
            Nghe thử khẩu hình
          </button>
        </div>
        {modelStatus && <div className="mu" style={{ marginTop: 6 }}>{modelStatus}</div>}
      </section>
      <ChatPanel
        messages={messages}
        isThinking={isThinking}
        listening={listening}
        topK={topK}
        minScore={minScore}
        rate={rate}
        onAsk={ask}
        onMic={toggle}
        onTopK={setTopK}
        onMinScore={setMinScore}
        onRate={setRate}
      />
    </main>
  );
}
