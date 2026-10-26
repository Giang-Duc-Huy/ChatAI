import type { VisemeFrame, VisemeName } from "../types";

export const VIS: Record<VisemeName, { o: number; w: number }> = {
  aa: { o: 0.9, w: 1 },
  ee: { o: 0.45, w: 1.3 },
  ih: { o: 0.25, w: 1.45 },
  oh: { o: 0.6, w: 0.7 },
  ou: { o: 0.3, w: 0.5 },
};

const MAP: Record<string, VisemeName> = {
  a: "aa",
  ă: "aa",
  â: "aa",
  e: "ee",
  ê: "ee",
  i: "ih",
  y: "ih",
  o: "oh",
  ô: "oh",
  ơ: "oh",
  u: "ou",
  ư: "ou",
};

function stripTone(w: string) {
  return w
    .normalize("NFD")
    .replace(/[\u0300\u0301\u0303\u0309\u0323]/g, "")
    .normalize("NFC")
    .toLowerCase();
}

function syllable(word: string): { v: VisemeName | null; lip: boolean } | null {
  const w = stripTone(word).replace(/[^a-zăâêôơưđ]/g, "");
  if (!w) return null;
  const lip = /^[bmp]/.test(w);
  const s = w.replace(/^qu/, "q").replace(/^gi(?=[aăâeêoôơuưy])/, "g");
  const vs = [...s].filter((c) => MAP[c]);
  if (!vs.length) return { v: null, lip };
  const main = vs.find((c) => "aăâơôoeê".includes(c)) || vs[0];
  return { v: MAP[main], lip };
}

export function buildTimeline(text: string, rate: number): VisemeFrame[] {
  const words: { ci: number; sy: { v: VisemeName | null; lip: boolean } | null; end: boolean; comma: boolean }[] = [];
  const re = /\S+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    words.push({
      ci: m.index,
      sy: syllable(m[0]),
      end: /[.!?;:]$/.test(m[0]),
      comma: /,$/.test(m[0]),
    });
  }
  const tl: VisemeFrame[] = [];
  let t = 0;
  const d = 0.24 / rate;
  for (const w of words) {
    tl.push({ t0: t, t1: t + d, ci: w.ci, ...(w.sy || { v: null, lip: false }) });
    t += d;
    if (w.end) t += 0.35 / rate;
    else if (w.comma) t += 0.15 / rate;
  }
  return tl;
}

export function visemeAt(tl: VisemeFrame[], t: number) {
  for (const s of tl) {
    if (t >= s.t0 && t < s.t1) {
      const p = (t - s.t0) / (s.t1 - s.t0);
      if (!s.v && !s.lip) return null;
      const env = Math.sin(Math.PI * Math.min(1, p));
      const amp = 0.75 + 0.25 * Math.sin(t * 19) * Math.sin(t * 7.3);
      if (s.lip && p < 0.18) return { o: 0.04, w: 1, name: "đóng" };
      const V = VIS[s.v || "aa"];
      return { o: V.o * env * amp, w: V.w, name: s.v || "aa" };
    }
  }
  return null;
}
