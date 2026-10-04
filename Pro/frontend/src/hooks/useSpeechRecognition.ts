import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null;
  onerror: ((ev: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal?: boolean }>;
};

function getRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function useSpeechRecognition(lang = "vi-VN") {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sttMs, setSttMs] = useState<number | undefined>();
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const startAt = useRef<number>(0);

  useEffect(() => {
    setSupported(Boolean(getRecognitionCtor()));
  }, []);

  const stop = useCallback(() => {
    recRef.current?.stop();
    setListening(false);
  }, []);

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      setError("Trình duyệt không hỗ trợ Web Speech API.");
      return;
    }
    setError(null);
    setTranscript("");
    setInterim("");
    const rec = new Ctor();
    rec.lang = lang;
    rec.interimResults = true;
    rec.continuous = false;
    startAt.current = performance.now();
    rec.onresult = (ev) => {
      let finalText = "";
      let interimText = "";
      for (let i = 0; i < ev.results.length; i++) {
        const r = ev.results[i];
        const t = r[0]?.transcript || "";
        if ((r as { isFinal?: boolean }).isFinal) finalText += t;
        else interimText += t;
      }
      if (finalText) {
        setTranscript(finalText.trim());
        setSttMs(performance.now() - startAt.current);
      }
      setInterim(interimText.trim());
    };
    rec.onerror = (ev) => {
      if (ev.error === "not-allowed") {
        setError("Bạn đã từ chối quyền micro. Có thể hỏi bằng văn bản.");
      } else if (ev.error !== "aborted") {
        setError(`Lỗi nhận dạng giọng nói: ${ev.error}`);
      }
      setListening(false);
    };
    rec.onend = () => setListening(false);
    recRef.current = rec;
    try {
      rec.start();
      setListening(true);
    } catch {
      setError("Không thể bắt đầu nhận dạng giọng nói.");
    }
  }, [lang]);

  return {
    supported,
    listening,
    transcript,
    interim,
    error,
    sttMs,
    start,
    stop,
    clearTranscript: () => setTranscript(""),
  };
}
