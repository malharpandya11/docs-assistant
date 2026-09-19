"""Convert a PDF into Markdown so it can be dropped into corpus/ and picked up
by ingest.py completely unchanged — chunking.py already splits on Markdown
headings, so the only missing piece was getting a PDF into that shape.

Heading structure (#, ##, ###) is inferred from font size/weight in the PDF,
not guaranteed — quality depends entirely on how consistently the source PDF
uses distinct heading styles. Always skim the output before indexing it.

Does NOT handle scanned/image-only PDFs (no OCR) — this is text extraction,
not image recognition. If `python pdf_to_markdown.py` produces an empty or
near-empty file, the PDF is probably scanned images and needs an OCR step
first (pytesseract + pdf2image), not covered here.

Usage:
    python pdf_to_markdown.py path/to/document.pdf corpus/some-folder/document.md
"""

import sys
from pathlib import Path

import pymupdf4llm

MIN_EXTRACTED_CHARS = 200


def pdf_to_markdown_text(pdf_path: str) -> str:
    """Extract Markdown from a PDF on disk. Shared by the CLI below and the
    /upload endpoint in main.py — one extraction implementation, two callers."""
    return pymupdf4llm.to_markdown(pdf_path)


def looks_like_scanned_pdf(md_text: str) -> bool:
    return len(md_text.strip()) < MIN_EXTRACTED_CHARS


def main():
    if len(sys.argv) != 3:
        print("Usage: python pdf_to_markdown.py <input.pdf> <output.md>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"No such file: {input_path}")
        sys.exit(1)

    print(f"Extracting {input_path} ...")
    md_text = pdf_to_markdown_text(str(input_path))

    if looks_like_scanned_pdf(md_text):
        print(
            "Warning: extracted almost no text. This PDF is likely scanned "
            "images rather than real text, which needs OCR — not handled here."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_text, encoding="utf-8")

    heading_count = sum(1 for line in md_text.splitlines() if line.startswith("#"))
    print(f"Wrote {output_path} ({len(md_text):,} chars, {heading_count} headings detected)")
    print("Skim the file before indexing — heading detection is heuristic, not exact.")


if __name__ == "__main__":
    main()
