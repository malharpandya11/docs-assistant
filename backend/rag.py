"""Retrieval + generation. `generate()` is the one function to swap to change LLM providers."""

import os

from common import GROQ_MODEL, RELEVANCE_THRESHOLD, TOP_K
from query import retrieve

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a set of reference documents. "
    "Use the provided context to answer when it's relevant, and mention the "
    "source files you drew on. If the context doesn't fully address the "
    "question, answer the rest from your own knowledge and blend it in "
    "naturally, the way any knowledgeable assistant would — don't call out "
    "which parts came from where, and never say something wasn't found in "
    "the documents. The user has no visibility into what's indexed and "
    "shouldn't need any."
)

GENERAL_KNOWLEDGE_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant. Answer the user's question "
    "directly and naturally."
)

REWRITE_PROMPT = (
    "Conversation so far:\n{history}\n\n"
    "Follow-up question: {question}\n\n"
    "Rewrite the follow-up as a single standalone search query that includes "
    "any context it depends on. Reply with ONLY the rewritten query, no "
    "preamble, no quotes."
)

_client = None


def get_client():
    """Lazy so importing this module never requires GROQ_API_KEY to be set."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy backend/.env.example to backend/.env "
                "and add a key from https://console.groq.com/keys"
            )
        from groq import Groq

        _client = Groq(api_key=api_key)
    return _client


def generate(prompt: str, *, system: str = SYSTEM_PROMPT, temperature: float = 0.1) -> str:
    from groq import APIStatusError, RateLimitError

    client = get_client()
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
    except RateLimitError as e:
        raise RuntimeError(
            "Groq's free-tier rate limit was hit. Wait a moment and try again."
        ) from e
    except APIStatusError as e:
        raise RuntimeError(f"The LLM request failed ({e.status_code}): {e.message}") from e
    return completion.choices[0].message.content


def rewrite_standalone_query(question: str, history: list[dict]) -> str:
    """Turn a follow-up like "what about the async version?" into something
    retrieval can actually search on. No-op with no prior turns."""
    if not history:
        return question
    convo = "\n".join(f"Q: {turn['question']}\nA: {turn['answer']}" for turn in history[-3:])
    prompt = REWRITE_PROMPT.format(history=convo, question=question)
    rewritten = generate(prompt, system="You rewrite follow-up questions.", temperature=0.0)
    return rewritten.strip() or question


def build_prompt(question: str, hits: list[dict]) -> str:
    context = "\n\n---\n\n".join(f"Source: {h['source_file']}\n{h['text']}" for h in hits)
    return (
        f"Context excerpts:\n\n{context}\n\n---\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above."
    )


def answer_question(
    question: str, history: list[dict] | None = None, k: int = TOP_K
) -> tuple[str, list[str], list[dict], bool]:
    history = history or []
    search_query = rewrite_standalone_query(question, history)

    if search_query != question:
        print(f"[rag] question={question!r}")
        print(f"[rag] rewritten to={search_query!r} (history had {len(history)} turn(s))")

    hits = retrieve(search_query, k=k)
    print(f"[rag] retrieved {len(hits)} chunks for query={search_query!r}:")
    for h in hits:
        print(f"[rag]   dist={h['distance']:.4f}  {h['source_file']}  ({h['heading_path']})")

    best_distance = hits[0]["distance"] if hits else None
    relevant = best_distance is not None and best_distance <= RELEVANCE_THRESHOLD

    if relevant:
        prompt = build_prompt(question, hits)
        answer = generate(prompt)
        sources = sorted({h["source_file"] for h in hits})
    else:
        print(f"[rag] best distance {best_distance} exceeds threshold — no doc context sent")
        answer = generate(question, system=GENERAL_KNOWLEDGE_SYSTEM_PROMPT)
        sources = []

    return answer, sources, hits, relevant
