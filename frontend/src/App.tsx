import { useCallback, useRef, useState } from "react";
import { postChat } from "./api/client";
import { Avatar3D } from "./components/Avatar3D";
import { ChatPanel } from "./components/ChatPanel";
import { useSpeechRecognition } from "./hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "./hooks/useSpeechSynthesis";
import { loadDocuments, localAnswer } from "./lib/retrieval";
import { nfc } from "./lib/text";
import type { AvatarState, ChatMessage, DocChunk } from "./types";

let msgId = 0;
const nextId = () => String(++msgId);

export default function App() {
  const [avatarState, setAvatarState] = useState<AvatarState>("Chờ");
  const [mouthInfo, setMouthInfo] = useState("");
  const [indexStatus, setIndexStatus] = useState(
    "Đang dùng chỉ mục tuyển sinh trên máy chủ. Tài liệu bạn tải lên chỉ được xử lý trong phiên trình duyệt này.",
  );
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: nextId(),
      role: "bot",
      text: "Xin chào! Bạn có thể hỏi trên dữ liệu tuyển sinh đã lập chỉ mục ở máy chủ hoặc tải tài liệu lên để hỏi trong phiên trình duyệt này.",
    },
  ]);
  const [topK, setTopK] = useState(5);
  const [minScore, setMinScore] = useState(0.35);
  const [rate, setRate] = useState(1);

  const chunksRef = useRef<DocChunk[]>([]);
  const dfRef = useRef<Record<string, number>>({});
  const avgRef = useRef(1);
  const topKRef = useRef(topK);
  const minScoreRef = useRef(minScore);
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
      if (!q) return;
      add({ role: "user", text: q });
      setAvatarState("Nghĩ");
      void (async () => {
        try {
          if (chunksRef.current.length) {
            const a = localAnswer(
              q,
              chunksRef.current,
              dfRef.current,
              avgRef.current,
              topKRef.current,
              minScoreRef.current,
            );
            add({
              role: "bot",
              text: `${a.text}\n(retrieval: ${a.ms.toFixed(1)} ms · chỉ mục trình duyệt)`,
              sources: a.src,
            });
            speak(a.text);
            return;
          }
          const a = await postChat(q, topKRef.current, minScoreRef.current);
          const lat = a.latency || {};
          add({
            role: "bot",
            text: `${a.answer}\n(retrieval ${lat.retrieval} ms · LLM ${lat.llm} ms)`,
            sources: (a.sources || []).map((s) => ({
              doc: s.doc_title,
              section: s.section,
              date: s.date,
            })),
          });
          speak(a.answer);
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          add({ role: "bot", text: `Không thể xử lý câu hỏi: ${message}` });
          setAvatarState("Chờ");
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

  const onFiles = async (files: FileList) => {
    setIndexStatus("Đang đọc tài liệu…");
    try {
      const { chunks, df, avg, names } = await loadDocuments(files);
      chunksRef.current = chunks;
      dfRef.current = df;
      avgRef.current = avg;
      if (!chunks.length) {
        setIndexStatus("Không tìm thấy văn bản có thể lập chỉ mục trong các tài liệu đã chọn.");
        return;
      }
      setIndexStatus(
        `Đã lập chỉ mục cục bộ ${chunks.length} đoạn từ ${names.length} tài liệu: ${names.join("; ")}. Tài liệu chỉ được giữ trong phiên trình duyệt này.`,
      );
      add({ role: "bot", text: "Mình đã nạp tài liệu trong trình duyệt. Các câu hỏi tiếp theo sẽ chỉ dùng bộ tài liệu này." });
    } catch (err) {
      setIndexStatus("Lỗi đọc tài liệu: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  return (
    <main>
      <section className="card">
        <h1>Trợ lý tuyển sinh UIT</h1>
        <div className="mu">Nhân vật 3D · lip-sync theo viseme tiếng Việt</div>
        <Avatar3D
          state={avatarState}
          playingRef={playingRef}
          timelineRef={timelineRef}
          clock0Ref={clock0Ref}
          onMouthInfo={setMouthInfo}
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
        <div className="mu" style={{ marginTop: 6 }}>
          {mouthInfo}
        </div>
      </section>
      <ChatPanel
        indexStatus={indexStatus}
        messages={messages}
        listening={listening}
        topK={topK}
        minScore={minScore}
        rate={rate}
        onFiles={onFiles}
        onAsk={ask}
        onMic={toggle}
        onTopK={setTopK}
        onMinScore={setMinScore}
        onRate={setRate}
      />
    </main>
  );
}
