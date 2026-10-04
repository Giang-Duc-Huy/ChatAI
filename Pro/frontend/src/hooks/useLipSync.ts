import { useEffect, useRef } from "react";
import type { MutableRefObject } from "react";
import type { VRM } from "@pixiv/three-vrm";

const MOUTH_KEYS = ["aa", "ih", "ou", "ee", "oh"] as const;

function rmsInSpeechBand(analyser: AnalyserNode): number {
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(data);
  const sampleRate = analyser.context.sampleRate;
  const binSize = sampleRate / analyser.fftSize;
  // Speech band ~300–3400 Hz
  const start = Math.floor(300 / binSize);
  const end = Math.min(data.length - 1, Math.floor(3400 / binSize));
  let sum = 0;
  let n = 0;
  for (let i = start; i <= end; i++) {
    const v = data[i] / 255;
    sum += v * v;
    n++;
  }
  return n ? Math.sqrt(sum / n) : 0;
}

export function useLipSync(
  vrmRef: MutableRefObject<VRM | null>,
  analyserRef: MutableRefObject<AnalyserNode | null>,
  enabled: boolean,
  playing: boolean
) {
  const smooth = useRef(0);
  const cycle = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let raf = 0;
    const tick = () => {
      const vrm = vrmRef.current;
      const analyser = analyserRef.current;
      if (vrm?.expressionManager) {
        let target = 0;
        if (playing && analyser) {
          const energy = rmsInSpeechBand(analyser);
          target = Math.min(1, Math.max(0, (energy - 0.04) * 3.2));
        }
        smooth.current = smooth.current * 0.65 + target * 0.35;
        const w = smooth.current;
        const expr = vrm.expressionManager;
        // Reset mouths
        for (const k of MOUTH_KEYS) expr.setValue(k, 0);
        if (w > 0.02) {
          cycle.current += 0.08;
          const idx = Math.floor(cycle.current) % MOUTH_KEYS.length;
          const primary = MOUTH_KEYS[0];
          const secondary = MOUTH_KEYS[idx];
          expr.setValue(primary, w);
          if (secondary !== primary) expr.setValue(secondary, w * 0.35);
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [analyserRef, enabled, playing, vrmRef]);
}
