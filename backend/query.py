"""CLI retrieval smoke-test — no LLM involved. Run after ingest.py.

    python query.py "how do I add a path parameter?"
"""

import sys

from common import TOP_K, embed_query, get_collection


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    collection = get_collection()
    query_embedding = embed_query(question)
    print(
        f"[query] embedded question -> {len(query_embedding)} dims, "
        f"first 5 = {[round(v, 4) for v in query_embedding[:5]]}"
    )
    result = collection.query(query_embeddings=[query_embedding], n_results=k)

    hits = []
    for doc, meta, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append(
            {
                "text": doc,
                "source_file": meta["source_file"],
                "heading_path": meta.get("heading_path", ""),
                "distance": distance,
            }
        )
    return hits


def main():
    question = " ".join(sys.argv[1:]) or "How do I add a path parameter?"
    hits = retrieve(question)

    print(f"Q: {question}\n")
    for i, hit in enumerate(hits, 1):
        snippet = hit["text"][:300].replace("\n", " ")
        print(f"[{i}] {hit['source_file']}  (distance={hit['distance']:.4f})")
        print(f"    {hit['heading_path']}")
        print(f"    {snippet}...\n")


if __name__ == "__main__":
    main()
