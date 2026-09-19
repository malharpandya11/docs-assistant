"""Shared config, embedding model, and Chroma client — loaded once, reused everywhere."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = Path(os.getenv("CORPUS_DIR", BASE_DIR / "corpus"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "docs")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
TOP_K = int(os.getenv("TOP_K", "8"))

# Cosine distance above which the best retrieved chunk is treated as "no
# relevant document found" rather than weak-but-usable context. Calibrated
# empirically on this corpus: genuine matches (even loose ones) land under
# ~0.85; clearly unrelated questions (different topic entirely) land at
# ~1.05-1.15. This only catches the obvious misses — anything in between is
# left to the model's own judgment of the actual retrieved text, since a
# single number can't tell "adjacent but not covered" from "off-topic" as
# reliably as reading the content can.
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.95"))

# bge-* models want this prefix on queries (not on indexed documents) to get
# asymmetric search working — see the model card on the Hub.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_embedder = None
_chroma_client = None
_collection = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedder


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_chroma_client().get_or_create_collection(COLLECTION_NAME)
    return _collection


def reset_collection():
    """Drop and recreate the collection so a re-index starts from a fresh HNSW
    segment, instead of delete-then-readd into the same one. Repeated
    delete/readd cycles into a live collection degrade its approximate nearest-
    neighbor graph — same stored documents, silently worse search quality."""
    from chromadb.errors import NotFoundError

    global _collection
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except NotFoundError:
        pass  # nothing to drop on a first run
    _collection = client.create_collection(COLLECTION_NAME)
    return _collection


def add_document_to_index(rel_path: str, text: str) -> int:
    """Chunk, embed, and add one document to the live collection — an
    incremental add, not a rebuild. Safe to call repeatedly: existing chunks
    for the same rel_path are deleted first (scoped delete, not the
    whole-collection churn reset_collection() exists to avoid), so
    re-uploading a file replaces it instead of duplicating it. Returns the
    number of chunks added."""
    from chunking import build_chunk_records

    collection = get_collection()
    collection.delete(where={"source_file": rel_path})

    ids, documents, metadatas = build_chunk_records(rel_path, text)
    if not documents:
        return 0

    embeddings = embed_documents(documents)
    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    return len(documents)


def embed_documents(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def embed_query(text: str) -> list[float]:
    model = get_embedder()
    vec = model.encode([QUERY_INSTRUCTION + text], normalize_embeddings=True, show_progress_bar=False)
    return vec[0].tolist()
