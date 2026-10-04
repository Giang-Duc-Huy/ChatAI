import type { SourceItem } from "../types";
import { useState } from "react";

interface Props {
  sources: SourceItem[];
}

export function SourceList({ sources }: Props) {
  const [openId, setOpenId] = useState<string | null>(null);
  if (!sources?.length) return null;

  return (
    <div className="sources">
      <div className="sources-label">Nguồn tham chiếu</div>
      <ul>
        {sources.map((s, i) => {
          const key = `${s.doc_id}-${i}`;
          const open = openId === key;
          return (
            <li key={key}>
              <button type="button" className="source-btn" onClick={() => setOpenId(open ? null : key)}>
                <span className="source-title">{s.title || s.doc_id}</span>
                <span className="source-meta">
                  {s.year ? ` · ${s.year}` : ""}
                  {s.page ? ` · tr.${s.page}` : ""}
                  {` · ${(s.score * 100).toFixed(0)}%`}
                </span>
              </button>
              {open && <p className="source-snippet">{s.snippet}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
