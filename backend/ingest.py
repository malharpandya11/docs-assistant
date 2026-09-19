"""Walk the corpus, chunk on headings, embed, and (re)write the Chroma collection.

Re-run this any time the corpus, chunking, or embedding model changes —
re-indexing is the only way stale chunks leave the store.
"""

import sys

from chunking import build_chunk_records
from common import CORPUS_DIR, embed_documents, reset_collection


def find_files() -> list:
    return sorted(CORPUS_DIR.rglob("*.md"))


def build_chunks(files: list) -> tuple[list[str], list[str], list[dict]]:
    ids, documents, metadatas = [], [], []
    for path in files:
        rel = str(path.relative_to(CORPUS_DIR))
        text = path.read_text(encoding="utf-8", errors="ignore")
        file_ids, file_documents, file_metadatas = build_chunk_records(rel, text)
        ids += file_ids
        documents += file_documents
        metadatas += file_metadatas
    return ids, documents, metadatas


def main():
    files = find_files()
    if not files:
        print(f"No .md files found under {CORPUS_DIR}")
        sys.exit(1)

    ids, documents, metadatas = build_chunks(files)
    print(f"{len(files)} files -> {len(documents)} chunks")
    if not documents:
        print("No chunks survived filtering — check MIN_CHUNK_CHARS or the corpus.")
        sys.exit(1)

    # Drop and recreate rather than delete-then-readd into the same collection —
    # repeated churn on one HNSW segment degrades its search quality even
    # though the stored documents stay correct. See common.reset_collection().
    print("Dropping and recreating the collection for a clean re-index")
    collection = reset_collection()

    print("Embedding chunks (first run downloads the model)...")
    embeddings = embed_documents(documents)

    batch_size = 100
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"Indexed {len(documents)} chunks into collection '{collection.name}'")


if __name__ == "__main__":
    main()
