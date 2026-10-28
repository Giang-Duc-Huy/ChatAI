export type AvatarState = "Chờ" | "Nghe" | "Nghĩ" | "Nói";

export type SourceRef = {
  doc: string;
  section: string;
  date: string;
  url?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "bot";
  text: string;
  sources?: SourceRef[];
};

export type DocChunk = {
  doc: string;
  date: string;
  section: string;
  text: string;
  tf: Record<string, number>;
  toks: string[];
};

export type ChatResponse = {
  answer: string;
  sources: { doc_title: string; section: string; date: string; score: number; url?: string }[];
  latency: { retrieval?: number; llm?: number; total?: number };
};

export type VisemeName = "aa" | "ee" | "ih" | "oh" | "ou";

export type VisemeFrame = {
  t0: number;
  t1: number;
  ci: number;
  v: VisemeName | null;
  lip: boolean;
};
