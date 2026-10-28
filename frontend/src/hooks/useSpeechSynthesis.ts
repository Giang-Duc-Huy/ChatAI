import { useCallback, useEffect, useRef, useState } from "react";
import type { AvatarState, VisemeFrame } from "../types";
import { buildTimeline } from "../lib/viseme";
import { postTts } from "../api/client";

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
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef("");
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
    genRef.current++;
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    audioRef.current?.pause();
    audioRef.current = null;
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    audioUrlRef.current = "";
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
      stop();
      const gen = genRef.current;
      curText.current = text;
      const r = rateRef.current || 1;
      const clean = text.replace(/\[[^\]]*\]/g, "").replace(/\s+/g, " ").trim();
      const tl = buildTimeline(clean, r);
      let browserStarted = false;
      const done = () => {
        if (gen !== genRef.current) return;
        markPlaying(false);
        onStateRef.current("Chờ");
        if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = "";
        audioRef.current = null;
      };
      const speakInBrowser = () => {
        if (gen !== genRef.current || browserStarted) return;
        browserStarted = true;
        const u = new SpeechSynthesisUtterance(clean);
        u.lang = "vi-VN";
        u.rate = r;
        if (voiceRef.current) u.voice = voiceRef.current;
        u.onstart = () => {
          if (gen === genRef.current) begin(tl);
        };
        u.onboundary = (ev) => {
          if (gen !== genRef.current) return;
          const s = tl.find((x) => x.ci >= ev.charIndex);
          if (s) clock0Ref.current = performance.now() - s.t0 * 1000;
        };
        u.onend = done;
        u.onerror = done;
        if (!("speechSynthesis" in window) || !voiceRef.current) {
          begin(tl);
          const total = tl.length ? tl[tl.length - 1].t1 : 1;
          fallbackTimer.current = window.setTimeout(done, total * 1000 + 300);
          if ("speechSynthesis" in window && !voiceRef.current) speechSynthesis.speak(u);
          return;
        }
        speechSynthesis.speak(u);
      };

      void postTts(clean)
        .then((result) => {
          if (gen !== genRef.current) return;
          const binary = atob(result.audio_b64);
          const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
          const blob = new Blob([bytes], { type: result.mime });
          audioUrlRef.current = URL.createObjectURL(blob);
          const audio = new Audio(audioUrlRef.current);
          audioRef.current = audio;
          const serverTimeline: VisemeFrame[] = result.visemes.map((frame) => ({
            ...frame,
            v: frame.viseme,
            ci: 0,
          }));
          timelineRef.current = serverTimeline;
          audio.onplay = () => {
            clock0Ref.current = performance.now() - audio.currentTime * 1000;
            markPlaying(true);
            onStateRef.current("Nói");
          };
          audio.ontimeupdate = () => {
            clock0Ref.current = performance.now() - audio.currentTime * 1000;
          };
          audio.onended = done;
          audio.onerror = () => {
            if (gen !== genRef.current) return;
            audioRef.current = null;
            if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
            audioUrlRef.current = "";
            speakInBrowser();
          };
          void audio.play().catch(() => {
            if (gen !== genRef.current) return;
            audioRef.current = null;
            if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
            audioUrlRef.current = "";
            speakInBrowser();
          });
        })
        .catch(() => {
          speakInBrowser();
        });
    },
    [stop],
  );

  const replay = useCallback(() => {
    if (curText.current) speak(curText.current);
  }, [speak]);

  return { speak, stop, replay, playing, playingRef, timelineRef, clock0Ref };
}
