import unicodedata
from ..config import EMBEDDING_MODEL, INDEX_DIR, TOP_K, MIN_SCORE

_model = _col = None

def _load():
    global _model, _col
    if _col is None:
        import chromadb
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
        _col = chromadb.PersistentClient(path=str(INDEX_DIR)).get_collection("tuyensinh")
    return _model, _col

def retrieve(question: str, k: int = TOP_K, min_score: float = MIN_SCORE):
    model, col = _load()
    q = unicodedata.normalize("NFC", question)
    emb = model.encode([q], normalize_embeddings=True).tolist()
    r = col.query(query_embeddings=emb, n_results=k, where={"superseded": 0})
    out = []
    for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
        out.append({**meta, "text": doc, "score": round(1 - dist, 4)})
    sufficient = bool(out) and out[0]["score"] >= min_score
    return out, sufficient
