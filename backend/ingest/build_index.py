"""Chạy: python -m ingest.build_index  (từ thư mục backend/)"""
import unicodedata
from collections import defaultdict
from app.config import DATA_RAW, EMBEDDING_MODEL, INDEX_DIR
from .load import load_catalog, read_file
from .clean import clean
from .chunk import chunk

def main():
    rows = load_catalog()
    # tài liệu cùng group: bản có effective_date mới nhất giữ lại, bản cũ -> superseded
    groups = defaultdict(list)
    for r in rows:
        groups[r["group"] or r["file"]].append(r)
    for g in groups.values():
        newest = max(g, key=lambda r: r["effective_date"] or r["date"] or "")
        for r in g:
            r["superseded"] = 0 if r is newest else 1

    ids, docs, metas = [], [], []
    for r in rows:
        text = clean(read_file(DATA_RAW / r["file"]))
        for n, (section, piece) in enumerate(chunk(text)):
            ids.append(f"{r['file']}::{n}")
            docs.append(piece)
            metas.append({"chunk_id": ids[-1], "doc_title": r["doc_title"], "source": r["source"],
                          "version": r["version"], "date": r["date"], "effective_date": r["effective_date"],
                          "section": section, "superseded": r["superseded"]})
    print(f"{len(rows)} tài liệu -> {len(docs)} đoạn")
    if not docs:
        print("Không có dữ liệu trong data/raw/"); return

    import chromadb
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    try:
        client.delete_collection("tuyensinh")
    except Exception:
        pass
    col = client.create_collection("tuyensinh", metadata={"hnsw:space": "cosine"})
    for i in range(0, len(docs), 32):
        emb = model.encode(docs[i:i + 32], normalize_embeddings=True).tolist()
        col.add(ids=ids[i:i + 32], documents=docs[i:i + 32], metadatas=metas[i:i + 32], embeddings=emb)
    print("Đã lập chỉ mục xong.")

if __name__ == "__main__":
    main()
