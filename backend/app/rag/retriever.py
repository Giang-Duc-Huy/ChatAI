import unicodedata
import math
import re
from threading import Lock
from ..config import EMBEDDING_MODEL, INDEX_DIR, TOP_K, MIN_SCORE

_model = _col = None
_load_lock = Lock()
_BM25_WEIGHT = 0.6
RETRIEVAL_PROFILE = (
    f"hybrid_bm25_{int(_BM25_WEIGHT * 100)}_dense_{int((1 - _BM25_WEIGHT) * 100)}_intent_rerank"
)
_STOP_WORDS = set(
    "là và của có cho các một những được trong với này khi thì để không như về từ tại theo bao nhiêu gì nào ạ mình bạn cần ngành năm tuyển sinh uit".split()
)
_INTENT_PHRASES = (
    "chỉ tiêu", "điểm chuẩn", "điểm trúng tuyển", "điều kiện", "học phí",
    "phương thức", "tổ hợp", "lệ phí", "hồ sơ", "thời gian", "cách thức",
    "nguyện vọng",
)

def _load():
    global _model, _col
    if _col is None:
        with _load_lock:
            if _col is None:
                import chromadb
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(EMBEDDING_MODEL)
                col = chromadb.PersistentClient(path=str(INDEX_DIR)).get_collection("tuyensinh")
                _model, _col = model, col
    return _model, _col

def warm():
    _load()

def _tokens(text: str):
    words = [
        word for word in re.findall(
            r"[^\W_]+", unicodedata.normalize("NFC", text).casefold(), re.UNICODE
        )
        if word not in _STOP_WORDS
    ]
    return words + [f"{left}_{right}" for left, right in zip(words, words[1:])]

def _rerank_for_intent(question: str, ranked: list):
    normalized_question = unicodedata.normalize("NFC", question).casefold()
    intents = [phrase for phrase in _INTENT_PHRASES if phrase in normalized_question]
    if not intents:
        return ranked

    focused = [
        item for item in ranked
        if any(
            phrase in unicodedata.normalize("NFC", item[0]["text"]).casefold()
            for phrase in intents
        )
    ]
    if not focused:
        return ranked

    intent_words = {word for phrase in intents for word in phrase.split()}
    subject_words = [
        word for word in re.findall(r"[^\W_]+", normalized_question, re.UNICODE)
        if word not in _STOP_WORDS and word not in intent_words and not word.isdigit()
    ]
    if subject_words:
        matching_subject = [
            item for item in focused
            if all(word in _tokens(item[0]["text"]) for word in subject_words)
        ]
        if matching_subject:
            return matching_subject
    return focused

def retrieve(question: str, k: int = TOP_K, min_score: float = MIN_SCORE, year: int | None = None):
    model, col = _load()
    q = unicodedata.normalize("NFC", question)
    emb = model.encode([q], normalize_embeddings=True).tolist()
    count = col.count()
    if not count:
        return [], False
    where = {"version": str(year)} if year is not None else {"superseded": 0}
    r = col.query(query_embeddings=emb, n_results=count, where=where)
    documents = r["documents"][0]
    metadatas = r["metadatas"][0]
    similarities = [1 - distance for distance in r["distances"][0]]
    query_tokens = set(_tokens(q))
    document_tokens = [_tokens(doc) for doc in documents]
    document_frequency = {}
    for tokens in document_tokens:
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    average_length = sum(map(len, document_tokens)) / max(1, len(document_tokens))
    bm25_scores = []
    for tokens in document_tokens:
        frequencies = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        score = 0.0
        for token in query_tokens:
            frequency = frequencies.get(token, 0)
            if not frequency:
                continue
            doc_freq = document_frequency[token]
            inverse_frequency = math.log(1 + (len(documents) - doc_freq + 0.5) / (doc_freq + 0.5))
            normalization = frequency + 1.2 * (0.25 + 0.75 * len(tokens) / max(1, average_length))
            score += inverse_frequency * frequency * 2.2 / normalization
        bm25_scores.append(score)

    max_bm25 = max(bm25_scores, default=0.0)
    min_similarity = min(similarities, default=0.0)
    max_similarity = max(similarities, default=0.0)
    similarity_range = max_similarity - min_similarity
    ranked = []
    for doc, meta, similarity, bm25 in zip(documents, metadatas, similarities, bm25_scores):
        lexical_score = bm25 / max_bm25 if max_bm25 else 0.0
        dense_score = ((similarity - min_similarity) / similarity_range) if similarity_range else 0.0
        combined_score = _BM25_WEIGHT * lexical_score + (1 - _BM25_WEIGHT) * dense_score
        ranked.append(({**meta, "text": doc, "score": round(similarity, 4)}, combined_score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    ranked = _rerank_for_intent(q, ranked)
    out = [item[0] for item in ranked[:k]]
    sufficient = bool(out) and out[0]["score"] >= min_score
    return out, sufficient
