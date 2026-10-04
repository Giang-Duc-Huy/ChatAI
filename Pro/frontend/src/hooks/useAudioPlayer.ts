import { useCallback, useEffect, useRef, useState } from "react";

export function useAudioPlayer() {
  const [playing, setPlaying] = useState(false);
  const [audioReadyMs, setAudioReadyMs] = useState<number | undefined>();
  const ctxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const requestStartedAt = useRef<number>(0);

  const ensureCtx = useCallback(async () => {
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext();
    }
    if (ctxRef.current.state === "suspended") {
      await ctxRef.current.resume();
    }
    return ctxRef.current;
  }, []);

  const stop = useCallback(() => {
    try {
      sourceRef.current?.stop();
    } catch {
      /* already stopped */
    }
    sourceRef.current = null;
    setPlaying(false);
  }, []);

  const markRequestStart = useCallback(() => {
    requestStartedAt.current = performance.now();
  }, []);

  const playBase64Mp3 = useCallback(
    async (base64: string) => {
      stop();
      const ctx = await ensureCtx();
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const buffer = await ctx.decodeAudioData(bytes.buffer.slice(0));

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.75;
      analyserRef.current = analyser;

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(analyser);
      analyser.connect(ctx.destination);
      source.onended = () => setPlaying(false);
      sourceRef.current = source;

      setAudioReadyMs(performance.now() - requestStartedAt.current);
      source.start(0);
      setPlaying(true);
    },
    [ensureCtx, stop]
  );

  useEffect(() => () => stop(), [stop]);

  return {
    playing,
    audioReadyMs,
    analyserRef,
    markRequestStart,
    playBase64Mp3,
    stop,
  };
}
