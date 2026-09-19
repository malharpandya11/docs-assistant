"""Markdown heading-based chunking — no character-count splitting.

Each chunk is prefixed with its heading path, e.g.
"Configuration > Environment Variables > DATABASE_URL", so the embedding
carries section context even when the chunk text alone wouldn't.
"""

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# mkdocs-material heading-id syntax: "## Title { #some-anchor }"
HEADING_ANCHOR_RE = re.compile(r"\s*\{\s*#[\w-]+\s*\}\s*$")
FENCE_RE = re.compile(r"^(```|~~~)")

MIN_CHUNK_CHARS = 20


@dataclass
class Chunk:
    heading_path: str
    text: str


def split_markdown(text: str) -> list[Chunk]:
    lines = text.splitlines()
    stack: list[str] = []
    chunks: list[Chunk] = []
    buffer: list[str] = []

    def flush():
        content = "\n".join(buffer).strip()
        buffer.clear()
        if not content:
            return
        heading_path = " > ".join(h for h in stack if h)
        full_text = f"{heading_path}\n\n{content}" if heading_path else content
        chunks.append(Chunk(heading_path=heading_path, text=full_text))

    in_code_fence = False
    for line in lines:
        if FENCE_RE.match(line.strip()):
            in_code_fence = not in_code_fence
            buffer.append(line)
            continue

        match = None if in_code_fence else HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            title = HEADING_ANCHOR_RE.sub("", match.group(2).strip()).strip()
            stack = stack[: level - 1]
            while len(stack) < level - 1:
                stack.append("")
            stack.append(title)
        else:
            buffer.append(line)
    flush()
    return chunks


def build_chunk_records(rel_path: str, text: str) -> tuple[list[str], list[str], list[dict]]:
    """Chunk one file's text into (ids, documents, metadatas) ready for
    collection.add(). Shared by ingest.py (whole corpus) and the /upload
    endpoint (one file at a time) — one place that decides what a chunk's id
    and metadata look like."""
    ids, documents, metadatas = [], [], []
    for i, chunk in enumerate(split_markdown(text)):
        if len(chunk.text) < MIN_CHUNK_CHARS:
            continue
        ids.append(f"{rel_path}::{i}")
        documents.append(chunk.text)
        metadatas.append({"source_file": rel_path, "heading_path": chunk.heading_path})
    return ids, documents, metadatas
