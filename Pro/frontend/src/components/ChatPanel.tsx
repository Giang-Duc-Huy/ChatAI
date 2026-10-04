import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { postChat, postTts } from "../api/client";
import type { ChatMessage } from "../types";
import { MessageList } from "./MessageList";
import { MicButton } from "./MicButton";
import { SettingsBar } from "./SettingsBar";
import { Avatar3D } from "./Avatar3D";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { useAudioPlayer } from "../hooks/useAudioPlayer";

const SAMPLE_QUESTIONS = [
  "Học phí ngành Công nghệ thông tin năm 2025?",
  "Các phương thức xét tuyển gồm những gì?",
  "Chỉ tiêu ngành Kinh tế là bao nhiêu?",
];

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface Props {
  sessionId: string;
}

export function ChatPanel({ sessionId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [avatarEnabled, setAvatarEnabled] = useState(true);
  const [privacyOpen, setPrivacyOpen] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const speech = useSpeechRecognition("vi-VN");
  const audio = useAudioPlayer();

  const mood = useMemo(() => {
    if (speech.listening) return "listen" as const;
    if (loading) return "think" as const;
    if (audio.playing) return "speak" as const;
    return "idle" as const;
  }, [speech.listening, loading, audio.playing]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const lastVoiceAsk = useRef("");

  async function ask(question: string, sttMs?: number) {
    const q = question.trim();
    if (!q || loading) return;

    const userMsg: ChatMessage = { id: uid(), role: "user", content: q, latency: { stt_ms: sttMs } };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    const t0 = performance.now();
    try {
      const resp = await postChat(q, sessionId, messages, ac.signal);
      const requestMs = performance.now() - t0;
      const assistant: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: resp.answer,
        sources: resp.sources,
        answerable: resp.answerable,
        timings_ms: resp.timings_ms,
        latency: { stt_ms: sttMs, request_ms: requestMs },
      };
      setMessages((prev) => [...prev, assistant]);

      if (voiceEnabled) {
        try {
          audio.markRequestStart();
          const ttsStarted = performance.now();
          const tts = await postTts(resp.answer, ac.signal);
          await audio.playBase64Mp3(tts.audioBase64);
          const audioReady = audio.audioReadyMs ?? performance.now() - ttsStarted;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistant.id
                ? {
                    ...m,
                    latency: {
                      ...m.latency,
                      audio_ready_ms: audioReady,
                      to_first_audio_ms: performance.now() - t0,
                    },
                  }
                : m
            )
          );
        } catch {
          // Fall back to text-only silently with a soft note
          setMessages((prev) => [
            ...prev,
            {
              id: uid(),
              role: "assistant",
              content: "Không phát được giọng nói — đang dùng chế độ chỉ văn bản.",
              error: false,
            },
          ]);
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Lỗi không xác định";
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: `Không nhận được câu trả lời: ${msg}`,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void ask(input, speech.sttMs);
  }

  function onMicToggle() {
    if (speech.listening) speech.stop();
    else speech.start();
  }

  useEffect(() => {
    if (speech.listening && speech.interim) {
      setInput(speech.interim);
    }
  }, [speech.listening, speech.interim]);

  useEffect(() => {
    if (speech.listening || !speech.transcript) return;
    if (speech.transcript === lastVoiceAsk.current) return;
    lastVoiceAsk.current = speech.transcript;
    const q = speech.transcript;
    speech.clearTranscript();
    void ask(q, speech.sttMs);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speech.listening, speech.transcript]);

  return (
    <div className={`chat-layout${avatarEnabled ? " with-avatar" : ""}`}>
      {avatarEnabled && (
        <aside className="avatar-pane">
          <Avatar3D analyserRef={audio.analyserRef} playing={audio.playing} mood={mood} />
        </aside>
      )}

      <section className="chat-pane">
        <SettingsBar
          voiceEnabled={voiceEnabled}
          avatarEnabled={avatarEnabled}
          ttsPlaying={audio.playing}
          onVoiceChange={setVoiceEnabled}
          onAvatarChange={setAvatarEnabled}
          onStopAudio={audio.stop}
        />

        {privacyOpen && voiceEnabled && (
          <div className="privacy-banner">
            <p>
              Giọng nói được xử lý bởi dịch vụ nhận dạng của trình duyệt (Web Speech API). Hệ thống
              không lưu âm thanh của bạn.
            </p>
            <button type="button" onClick={() => setPrivacyOpen(false)}>
              Đã hiểu
            </button>
          </div>
        )}

        {messages.length === 0 && (
          <div className="samples">
            {SAMPLE_QUESTIONS.map((q) => (
              <button key={q} type="button" className="sample-btn" onClick={() => void ask(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        <div className="messages-scroll" ref={listRef}>
          <MessageList
            messages={messages}
            onRetry={(m) => {
              const idx = messages.findIndex((x) => x.id === m.id);
              const prevUser = [...messages].slice(0, idx).reverse().find((x) => x.role === "user");
              if (prevUser) void ask(prevUser.content);
            }}
          />
          {loading && <div className="typing">Đang trả lời…</div>}
        </div>

        {(speech.interim || speech.error) && (
          <div className="speech-status">
            {speech.error || `Đang nghe: ${speech.interim}`}
          </div>
        )}

        <form className="composer" onSubmit={onSubmit}>
          <MicButton
            supported={speech.supported}
            listening={speech.listening}
            disabled={loading}
            onToggle={onMicToggle}
          />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Hỏi về tuyển sinh…"
            maxLength={500}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Gửi
          </button>
        </form>
      </section>
    </div>
  );
}
