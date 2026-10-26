import { useCallback, useEffect, useRef, useState } from "react";
import type { AvatarState, VisemeFrame } from "../types";
import { buildTimeline } from "../lib/viseme";

type Options = {
  rate: number;
  onState: (s: AvatarState) => void;
};

export function useSpeechSynthesis({ rate, onState }: Options) {
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(false);
  const timelineRef = useRef<VisemeFrame[]>([]);
  const clock0Ref = useRef(0);
  const curText = useRef("");
  const fallbackTimer = useRef(0);
  const genRef = useRef(0);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const rateRef = useRef(rate);
  const onStateRef = useRef(onState);
  rateRef.current = rate;
  onStateRef.current = onState;

  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const pick = () => {
      const vs = speechSynthesis.getVoices();
      voiceRef.current =
        vs.find((v) => /vi[-_]VN/i.test(v.lang)) || vs.find((v) => /^vi/i.test(v.lang)) || null;
    };
    pick();
    speechSynthesis.onvoiceschanged = pick;
    return () => {
      speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  const markPlaying = (value: boolean) => {
    playingRef.current = value;
    setPlaying(value);
  };

  const stop = useCallback(() => {
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    window.clearTimeout(fallbackTimer.current);
    markPlaying(false);
    onStateRef.current("Chờ");
  }, []);

  const begin = (tl: VisemeFrame[]) => {
    timelineRef.current = tl;
    clock0Ref.current = performance.now();
    markPlaying(true);
    onStateRef.current("Nói");
  };

  const speak = useCallback(
    (text: string) => {
      const gen = ++genRef.current;
      stop();
      curText.current = text;
      const r = rateRef.current || 1;
      const clean = text.replace(/\[[^\]]*\]/g, "").replace(/\s+/g, " ").trim();
      const tl = buildTimeline(clean, r);
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = "vi-VN";
      u.rate = r;
      if (voiceRef.current) u.voice = voiceRef.current;
      u.onstart = () => {
        if (gen !== genRef.current) return;
        begin(tl);
      };
      u.onboundary = (ev) => {
        if (gen !== genRef.current) return;
        const s = tl.find((x) => x.ci >= ev.charIndex);
        if (s) clock0Ref.current = performance.now() - s.t0 * 1000;
      };
      const done = () => {
        if (gen !== genRef.current) return;
        markPlaying(false);
        onStateRef.current("Chờ");
      };
      u.onend = done;
      u.onerror = done;
      const start = () => {
        if (gen !== genRef.current) return;
        if (!("speechSynthesis" in window) || !voiceRef.current) {
          begin(tl);
          const total = tl.length ? tl[tl.length - 1].t1 : 1;
          fallbackTimer.current = window.setTimeout(done, total * 1000 + 300);
          if ("speechSynthesis" in window && !voiceRef.current) speechSynthesis.speak(u);
          return;
        }
        speechSynthesis.speak(u);
      };
      window.setTimeout(start, 0);
    },
    [stop],
  );

  const replay = useCallback(() => {
    if (curText.current) speak(curText.current);
  }, [speak]);

  return { speak, stop, replay, playing, playingRef, timelineRef, clock0Ref };
}
