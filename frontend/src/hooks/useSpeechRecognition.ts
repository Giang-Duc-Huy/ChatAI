import { useCallback, useRef, useState } from "react";
import type { AvatarState } from "../types";

type Options = {
  onTranscript: (text: string) => void;
  onMessage: (text: string) => void;
  onState: (s: AvatarState) => void;
  stopSpeak: () => void;
};

export function useSpeechRecognition({ onTranscript, onMessage, onState, stopSpeak }: Options) {
  const [listening, setListening] = useState(false);
  const recRef = useRef<SpeechRecognition | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  const onMessageRef = useRef(onMessage);
  const onStateRef = useRef(onState);
  onTranscriptRef.current = onTranscript;
  onMessageRef.current = onMessage;
  onStateRef.current = onState;

  const toggle = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      onMessageRef.current("Trình duyệt này không hỗ trợ nhận dạng giọng nói. Bạn hãy nhập văn bản nhé.");
      return;
    }
    if (recRef.current) {
      recRef.current.stop();
      return;
    }
    stopSpeak();
    const rec = new SR();
    rec.lang = "vi-VN";
    rec.interimResults = false;
    let gotResult = false;
    setListening(true);
    onStateRef.current("Nghe");
    rec.onresult = (e) => {
      gotResult = true;
      onTranscriptRef.current(e.results[0][0].transcript);
    };
    rec.onerror = (e) =>
      onMessageRef.current(
        e.error === "not-allowed"
          ? "Mic bị từ chối. Bạn có thể nhập văn bản thay thế."
          : "Mình không nghe rõ, bạn thử lại hoặc nhập văn bản nhé.",
      );
    rec.onend = () => {
      recRef.current = null;
      setListening(false);
      if (!gotResult) onStateRef.current("Chờ");
    };
    recRef.current = rec;
    rec.start();
  }, [stopSpeak]);

  return { listening, toggle };
}
