import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from auth import get_current_user, hash_password, verify_password
from common import CORPUS_DIR, add_document_to_index, get_collection, get_embedder
from pdf_to_markdown import looks_like_scanned_pdf, pdf_to_markdown_text
from rag import answer_question

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB — generous for a text-based PDF, not for scanned-image ones
UPLOAD_SUBDIR = "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once at startup, not per request — the embedding model and Chroma
    # client are expensive to construct.
    get_embedder()
    get_collection()
    db.init_db()
    yield


app = FastAPI(title="Docs RAG Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    grounded: bool
    conversation_id: str


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[str]
    isError: bool


class ConversationDetail(BaseModel):
    id: str
    title: str | None
    messages: list[MessageOut]


class UploadResponse(BaseModel):
    filename: str
    source_file: str
    chunks_indexed: int
    warning: str | None = None


def _safe_stem(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(filename).stem).strip("-")
    return (stem or "document")[:80]


def _history_from_messages(messages: list[dict]) -> list[dict]:
    """Pair up consecutive user/assistant messages into the {question, answer}
    shape rag.py expects — mirrors the frontend's old buildHistory(), now done
    server-side since the DB is the source of truth."""
    history = []
    for i in range(len(messages) - 1):
        turn, nxt = messages[i], messages[i + 1]
        if turn["role"] == "user" and nxt["role"] == "assistant" and not nxt["isError"]:
            history.append({"question": turn["content"], "answer": nxt["content"]})
    return history


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Auth ----------


@app.post("/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    email = req.email.strip().lower()
    if "@" not in email or len(email) < 3:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = db.create_user(email, hash_password(req.password))
    token = db.create_token(user["id"])
    return AuthResponse(token=token, email=email)


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    email = req.email.strip().lower()
    user = db.get_user_by_email(email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = db.create_token(user["id"])
    return AuthResponse(token=token, email=user["email"])


@app.post("/auth/logout")
def logout(authorization: str | None = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        db.delete_token(authorization.removeprefix("Bearer "))
    return {"ok": True}


@app.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"email": user["email"]}


# ---------- Conversations ----------


@app.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(user: dict = Depends(get_current_user)):
    return db.list_conversations(user["id"])


@app.delete("/conversations/{conversation_id}")
def remove_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    db.delete_conversation(conversation_id, user["id"])
    return {"ok": True}


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = db.get_conversation(conversation_id, user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(id=conv["id"], title=conv["title"], messages=db.list_messages(conversation_id))


# ---------- Chat ----------


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")

    if req.conversation_id:
        conv = db.get_conversation(req.conversation_id, user["id"])
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = conv["id"]
    else:
        conversation_id = db.create_conversation(user["id"])["id"]

    history = _history_from_messages(db.list_messages(conversation_id))
    db.add_message(conversation_id, "user", question)

    try:
        answer, sources, _hits, grounded = answer_question(question, history=history)
    except RuntimeError as e:
        db.add_message(conversation_id, "assistant", str(e), is_error=True)
        raise HTTPException(status_code=500, detail=str(e))

    db.add_message(conversation_id, "assistant", answer, sources=sources)
    db.touch_conversation(conversation_id, title=question)

    return ChatResponse(answer=answer, sources=sources, grounded=grounded, conversation_id=conversation_id)


# ---------- Upload ----------


@app.post("/upload", response_model=UploadResponse)
def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Sync read (not `await file.read()`) — this route is a plain `def`, so
    # FastAPI runs the whole thing in its threadpool instead of the asyncio
    # event loop. PDF extraction + embedding take real seconds; doing that
    # inside `async def` would stall every other request for that long.
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    upload_dir = CORPUS_DIR / UPLOAD_SUBDIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    # A short random suffix avoids one upload silently overwriting another's
    # chunks just because two files share a name — there's no per-user
    # namespacing here, this is a shared corpus.
    stem = f"{_safe_stem(file.filename)}-{uuid.uuid4().hex[:6]}"
    pdf_path = upload_dir / f"{stem}.pdf"
    pdf_path.write_bytes(content)

    try:
        md_text = pdf_to_markdown_text(str(pdf_path))
    except Exception as e:
        # Log the real error (may contain a server-side file path) but never
        # forward that to the client — same allow-list-not-deny-list logging
        # principle as everywhere else in this app.
        print(f"[upload] failed to extract {file.filename!r}: {e}")
        raise HTTPException(status_code=422, detail="Could not read this file as a PDF.")

    warning = None
    if looks_like_scanned_pdf(md_text):
        warning = (
            "Almost no text could be extracted — this looks like a scanned/image-only "
            "PDF, which isn't supported yet."
        )

    md_path = upload_dir / f"{stem}.md"
    md_path.write_text(md_text, encoding="utf-8")
    rel_path = str(md_path.relative_to(CORPUS_DIR))

    chunks_indexed = add_document_to_index(rel_path, md_text)
    print(f"[upload] {user['email']} uploaded {file.filename!r} -> {rel_path} ({chunks_indexed} chunks)")

    return UploadResponse(
        filename=file.filename,
        source_file=rel_path,
        chunks_indexed=chunks_indexed,
        warning=warning,
    )
