"""Recall@5 baseline: how often the expected file shows up in retrieved chunks.

Run after backend/ingest.py, from anywhere:

    python eval/eval.py
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from query import retrieve  # noqa: E402

QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.json"


def main():
    questions = json.loads(QUESTIONS_PATH.read_text())

    answerable = [q for q in questions if q["expected_source_file"]]
    unanswerable = [q for q in questions if not q["expected_source_file"]]

    hits_count = 0
    print(f"Recall@5 over {len(answerable)} answerable questions\n")
    for q in answerable:
        hits = retrieve(q["question"], k=5)
        retrieved_files = {h["source_file"] for h in hits}
        found = q["expected_source_file"] in retrieved_files
        hits_count += found
        mark = "PASS" if found else "FAIL"
        print(f"[{mark}] {q['question']}")
        if not found:
            print(f"       expected: {q['expected_source_file']}")
            print(f"       got:      {sorted(retrieved_files)}")

    recall = hits_count / len(answerable) if answerable else 0.0
    print(f"\nRecall@5: {hits_count}/{len(answerable)} = {recall:.0%}")
    print(
        f"\n{len(unanswerable)} questions the corpus can't answer are not scored "
        "here — they're for a manual check against the live /chat endpoint: it "
        "should now fall back to Groq's general knowledge for these (clearly "
        "flagged as not from the documents, via the `grounded` field) rather "
        "than either refusing outright or guessing as if it were documented."
    )


if __name__ == "__main__":
    main()
