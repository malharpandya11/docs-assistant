"""Peek inside the Chroma collection — what's actually stored, in human-readable form.

    python inspect_db.py            # summary + a few sample records
    python inspect_db.py --source deployment/docker.md   # only records from one file
"""

import sys

from common import get_collection


def print_record(id_, document, metadata, embedding):
    print(f"id:        {id_}")
    print(f"source:    {metadata.get('source_file')}")
    print(f"heading:   {metadata.get('heading_path')}")
    print(f"vector:    {len(embedding)} dims, first 5 = {[round(v, 4) for v in embedding[:5]]}")
    print(f"text:      {document[:200].replace(chr(10), ' ')}...")
    print("-" * 80)


def main():
    collection = get_collection()
    total = collection.count()
    print(f"Collection '{collection.name}': {total} chunks total\n")

    if "--source" in sys.argv:
        source = sys.argv[sys.argv.index("--source") + 1]
        result = collection.get(
            where={"source_file": source}, include=["documents", "metadatas", "embeddings"]
        )
        print(f"{len(result['ids'])} chunks from '{source}':\n")
    else:
        result = collection.peek(limit=5)
        print("First 5 chunks in the collection (insertion order, not relevance):\n")

    for id_, document, metadata, embedding in zip(
        result["ids"], result["documents"], result["metadatas"], result["embeddings"]
    ):
        print_record(id_, document, metadata, embedding)


if __name__ == "__main__":
    main()
