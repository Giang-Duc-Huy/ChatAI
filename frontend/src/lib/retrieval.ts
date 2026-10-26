import type { DocChunk, SourceRef } from "../types";
import { nfc, REFUSAL } from "./text";

const STOP = new Set(
  "là và của có cho các một những được trong với này khi thì để không như về từ tại theo bao nhiêu gì nào ạ mình bạn cần".split(
    " ",
  ),
);

export function tokenize(s: string): string[] {
  const w = nfc(s)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter((x) => x && !STOP.has(x));
  const o = [...w];
  for (let i = 0; i < w.length - 1; i++) o.push(`${w[i]}_${w[i + 1]}`);
  return o;
}

function clean(t: string) {
  return nfc(t)
    .replace(/[ \t\u00a0]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function chunkDoc(doc: { title: string; date: string }, text: string) {
  const out: Omit<DocChunk, "tf" | "toks">[] = [];
  const parts = text.split(/\n(?=\s*(?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG)\s+\d+)/);
  for (const part of parts) {
    const sec = (part.match(/^\s*((?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG)\s+\d+[^\n]{0,60})/) || [])[1] || "";
    const p = part.replace(/\s+/g, " ").trim();
    if (p.length < 20) continue;
    for (let i = 0; i < p.length; i += 1000 - 150) {
      out.push({
        doc: doc.title,
        date: doc.date,
        section: sec.trim() || "Nội dung",
        text: p.slice(i, i + 1000),
      });
      if (i + 1000 >= p.length) break;
    }
  }
  return out;
}

function getDate(t: string) {
  const m = t.match(/(\d{1,2})[\/\-.](\d{1,2})[\/\-.](20\d{2})/);
  return m ? `${m[1]}/${m[2]}/${m[3]}` : "không rõ ngày";
}

type PdfItem = { str?: string; transform?: number[] };

async function readFile(file: File): Promise<{ title: string; date: string; text: string }> {
  let name = file.name;
  let text = "";
  if (/\.pdf$/i.test(file.name)) {
    const pdfjsLib = await import("pdfjs-dist");
    const { default: pdfWorker } = await import("pdfjs-dist/build/pdf.worker.min.mjs?url");
    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;
    const pdf = await pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise;
    const pages: string[] = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const content = await (await pdf.getPage(i)).getTextContent();
      let line = "";
      let y: number | null = null;
      for (const it of content.items as PdfItem[]) {
        const ty = it.transform?.[5];
        if (y !== null && ty !== undefined && Math.abs(ty - y) > 3) line += "\n";
        line += (it.str || "") + " ";
        if (ty !== undefined) y = ty;
      }
      pages.push(line);
    }
    const cnt: Record<string, number> = {};
    pages.forEach((p) =>
      new Set(p.split("\n").map((s) => s.trim())).forEach((s) => {
        if (s) cnt[s] = (cnt[s] || 0) + 1;
      }),
    );
    text = pages
      .map((p) =>
        p
          .split("\n")
          .filter((s) => !(pdf.numPages > 2 && cnt[s.trim()] > pdf.numPages / 2))
          .join("\n"),
      )
      .join("\n");
  } else if (/\.html?$/i.test(file.name)) {
    const d = new DOMParser().parseFromString(await file.text(), "text/html");
    d.querySelectorAll("script,style,nav,header,footer,noscript").forEach((e) => e.remove());
    const h = d.querySelector("title")?.textContent;
    if (h) name = h.trim();
    text = [...d.body.querySelectorAll("h1,h2,h3,h4,p,li,td,th")]
      .map((e) => e.textContent?.trim() || "")
      .filter(Boolean)
      .join("\n");
  } else {
    text = await file.text();
  }
  text = clean(text);
  return { title: name, date: getDate(text), text };
}

export function indexChunks(raw: Omit<DocChunk, "tf" | "toks">[]): {
  chunks: DocChunk[];
  df: Record<string, number>;
  avg: number;
} {
  const df: Record<string, number> = {};
  let tot = 0;
  const chunks: DocChunk[] = raw.map((c) => {
    const toks = tokenize(c.text);
    const tf: Record<string, number> = {};
    toks.forEach((t) => {
      tf[t] = (tf[t] || 0) + 1;
    });
    Object.keys(tf).forEach((t) => {
      df[t] = (df[t] || 0) + 1;
    });
    tot += toks.length;
    return { ...c, tf, toks };
  });
  return { chunks, df, avg: tot / Math.max(1, chunks.length) };
}

export async function loadDocuments(files: FileList | File[]) {
  const names: string[] = [];
  const raw: Omit<DocChunk, "tf" | "toks">[] = [];
  for (const f of Array.from(files)) {
    const d = await readFile(f);
    names.push(d.title);
    raw.push(...chunkDoc(d, d.text));
  }
  const indexed = indexChunks(raw);
  return { ...indexed, names };
}

export function searchChunks(
  question: string,
  chunks: DocChunk[],
  df: Record<string, number>,
  avg: number,
  k: number,
) {
  const qt = [...new Set(tokenize(question))];
  const n = chunks.length;
  return chunks
    .map((c) => {
      let s = 0;
      for (const t of qt) {
        const f = c.tf[t];
        if (!f) continue;
        const idf = Math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5));
        s += (idf * f * 2.2) / (f + 1.2 * (0.25 + 0.75 * (c.toks.length / avg)));
      }
      return { c, s };
    })
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, k);
}

export function localAnswer(
  question: string,
  chunks: DocChunk[],
  df: Record<string, number>,
  avg: number,
  k: number,
  minScore: number,
): { text: string; src: SourceRef[]; ms: number } {
  if (!chunks.length) {
    return { text: "Chưa có dữ liệu. Bạn hãy nạp tài liệu tuyển sinh trước nhé.", src: [], ms: 0 };
  }
  const t0 = performance.now();
  const hits = searchChunks(question, chunks, df, avg, k);
  const ms = performance.now() - t0;
  if (!hits.length || hits[0].s < minScore) return { text: REFUSAL, src: [], ms };
  const qt = new Set(tokenize(question));
  const sents: { s: string; ov: number; h: (typeof hits)[0] }[] = [];
  hits.slice(0, 3).forEach((h) =>
    h.c.text.split(/(?<=[.;:!?])\s+/).forEach((s) => {
      if (s.length < 15) return;
      const ov = tokenize(s).filter((t) => qt.has(t)).length;
      sents.push({ s: s.trim(), ov, h });
    }),
  );
  sents.sort((a, b) => b.ov - a.ov);
  const pick = sents.slice(0, 2).filter((x) => x.ov > 0);
  if (!pick.length) return { text: REFUSAL, src: [], ms };
  const src = [...new Map(pick.map((p) => [p.h.c.doc + p.h.c.section, p.h.c])).values()].map((c) => ({
    doc: c.doc,
    section: c.section,
    date: c.date,
  }));
  return { text: pick.map((p) => p.s).join(" "), src, ms };
}
