"""Shared RAG logic for the Gmail RAG Assistant.

The CLI scripts (Extract_emails.py, Query_Ollama.py, FakeDemo.py) each built their
own ChromaDB client and embedding model. This module holds that logic in one place
so the web app and the scripts behave identically:

    ingest -> embed -> store with user_id metadata -> filtered retrieval -> Ollama

Nothing here talks to the network except the Ollama call and (optionally) Gmail.
"""

import json
import os
import threading
import time

import chromadb
import requests
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "gmail_emails"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
DEMO_DATA_FILE = "fake_emails.json"

# Keep the model resident between queries. Loading an 8B model costs several
# seconds, which would otherwise be paid on every single question.
OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "10m")

# Layers to offload to the GPU. Unset lets Ollama decide; 0 forces CPU-only.
OLLAMA_NUM_GPU = os.environ.get("OLLAMA_NUM_GPU")

# Set to 0 after a GPU allocation failure so the rest of the session skips the GPU.
_num_gpu_fallback = None

_model = None
_model_lock = threading.Lock()
_client = None


def get_embedding_model():
    """Load the embedding model once, on first use (it takes a few seconds)."""
    global _model
    with _model_lock:
        if _model is None:
            _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection():
    return get_client().get_or_create_collection(COLLECTION_NAME)


def chunk_text(text, chunk_size=500):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def store_chunks(chunks, metadata, user_id):
    """Embed chunks and store them tagged with user_id (the isolation key)."""
    chunks = [c for c in chunks if c and c.strip()]
    if not chunks:
        return 0

    collection = get_collection()
    embeddings = get_embedding_model().encode(chunks).tolist()

    for i, chunk in enumerate(chunks):
        meta = dict(metadata)
        meta["user_id"] = user_id
        collection.add(
            documents=[chunk],
            embeddings=[embeddings[i]],
            metadatas=[meta],
            ids=[f"{user_id}_{metadata.get('subject', 'untitled')}_{i}"],
        )
    return len(chunks)


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------

def list_users():
    """Every user_id that currently has data in the collection."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    records = collection.get(include=["metadatas"])
    users = {m.get("user_id") for m in records["metadatas"] if m.get("user_id")}
    return sorted(users)


def user_stats(user_id):
    """Chunk and subject counts for one user."""
    collection = get_collection()
    records = collection.get(where={"user_id": user_id}, include=["metadatas"])
    metadatas = records["metadatas"]
    subjects = {m.get("subject") for m in metadatas if m.get("subject")}
    return {"chunks": len(metadatas), "documents": len(subjects)}


# --------------------------------------------------------------------------
# Ingestion
# --------------------------------------------------------------------------

def ingest_demo_data(reset=True):
    """Load fake_emails.json so the app is usable without Gmail credentials."""
    if reset:
        try:
            get_client().delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    with open(DEMO_DATA_FILE, "r", encoding="utf-8") as f:
        emails = json.load(f)

    stored = 0
    for email in emails:
        stored += store_chunks(
            [email["body"]],
            {
                "subject": email["subject"],
                "from": email.get("sender"),
                "date": email.get("timestamp"),
                "source": "demo",
            },
            email["user_id"],
        )

    return {"emails": len(emails), "chunks": stored, "users": list_users()}


def ingest_gmail(max_results=50, progress=None):
    """Fetch real Gmail messages for the authenticated user and index them.

    Requires credentials.json in the project folder; opens a browser for OAuth
    on first run. Imported lazily so the web app starts without Google libs
    configured.
    """
    from Extract_emails import (
        get_gmail_service,
        get_user_email,
        list_messages,
        get_message_content,
    )

    def report(message):
        if progress:
            progress(message)

    report("Authenticating with Google...")
    service = get_gmail_service()
    user_id = get_user_email(service)

    report(f"Authenticated as {user_id}. Listing messages...")
    messages = list_messages(service, max_results=max_results)

    report(f"Fetched {len(messages)} messages. Embedding...")
    stored = 0
    for index, msg in enumerate(messages, start=1):
        email = get_message_content(service, msg["id"])
        stored += store_chunks(
            chunk_text(email["body"]),
            {
                "from": email["from"],
                "subject": email["subject"],
                "date": email["date"],
                "source": "gmail",
            },
            user_id,
        )
        if index % 10 == 0 or index == len(messages):
            report(f"Indexed {index}/{len(messages)} messages...")

    return {"user_id": user_id, "emails": len(messages), "chunks": stored}


# --------------------------------------------------------------------------
# Retrieval + generation
# --------------------------------------------------------------------------

PROMPT_TEMPLATE = """You are an assistant.
Answer the user's question using ONLY the following email context.
If the answer is not present, say "I don't know".

Email context:
{context}

User question:
{question}
"""


def retrieve(question, user_id, n_results=5):
    """Embed the question and search, hard-filtered to one user's data."""
    embedding = get_embedding_model().encode(question).tolist()

    start = time.time()
    results = get_collection().query(
        query_embeddings=[embedding],
        n_results=n_results,
        where={"user_id": user_id},  # Enforce user isolation
    )
    elapsed = time.time() - start

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results.get("distances") else []

    sources = []
    for i, meta in enumerate(metadatas):
        sources.append({
            "subject": meta.get("subject"),
            "from": meta.get("from"),
            "date": meta.get("date"),
            "source": meta.get("source"),
            "user_id": meta.get("user_id"),
            "excerpt": documents[i][:400] if i < len(documents) else "",
            "score": round(1 - distances[i], 3) if i < len(distances) else None,
        })

    return {
        "documents": documents,
        "sources": sources,
        "retrieval_seconds": round(elapsed, 3),
    }


def build_prompt(documents, question):
    context = "\n\n---\n\n".join(documents)
    return PROMPT_TEMPLATE.format(context=context, question=question)


def ollama_status():
    """Is Ollama reachable, and is the configured model pulled?"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        return {
            "available": True,
            "models": models,
            "model": OLLAMA_MODEL,
            "model_pulled": any(m.split(":")[0] == OLLAMA_MODEL.split(":")[0] for m in models),
        }
    except Exception as exc:
        return {"available": False, "models": [], "model": OLLAMA_MODEL,
                "model_pulled": False, "error": str(exc)}


def _raise_for_ollama_error(response):
    """Surface Ollama's own error text, which explains far more than the status code.

    A model too large for available VRAM, for example, reports
    "unable to allocate CUDA0 buffer" here but only a bare 500 in the status.
    """
    if response.ok:
        return
    try:
        detail = response.json().get("error", "")
    except ValueError:
        detail = response.text[:300]
    raise RuntimeError(detail or f"Ollama returned HTTP {response.status_code}")


_MEMORY_ERROR_HINTS = (
    "cudamalloc",
    "out of memory",
    "unable to allocate",
    "failed to allocate",
)


def _is_memory_error(message):
    lowered = str(message).lower()
    return any(hint in lowered for hint in _MEMORY_ERROR_HINTS)


def _request_body(prompt, stream):
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }

    num_gpu = _num_gpu_fallback if _num_gpu_fallback is not None else OLLAMA_NUM_GPU
    if num_gpu is not None:
        body["options"] = {"num_gpu": int(num_gpu)}

    return body


def _use_cpu_from_now_on():
    """A model too large for the available VRAM fails to allocate every time.

    Rather than surface that to the user on each question, drop to CPU for the
    remainder of the session. Slower, but it always completes.
    """
    global _num_gpu_fallback
    if _num_gpu_fallback == 0:
        return False
    _num_gpu_fallback = 0
    print("Ollama could not allocate GPU memory. Falling back to CPU for this session.")
    return True


def generate(prompt):
    """Single-shot generation, retrying on CPU if the GPU cannot fit the model."""
    for _ in range(2):
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=_request_body(prompt, stream=False),
            timeout=600,
        )
        try:
            _raise_for_ollama_error(response)
        except RuntimeError as exc:
            if _is_memory_error(exc) and _use_cpu_from_now_on():
                continue
            raise
        return response.json().get("response", "")


def generate_stream(prompt):
    """Yield tokens as Ollama produces them, retrying on CPU if the GPU is too small."""
    for attempt in range(2):
        try:
            yield from _stream_once(prompt)
            return
        except RuntimeError as exc:
            # Only safe to retry before any token has been emitted, which is the
            # case here because the allocation failure happens at model load.
            if attempt == 0 and _is_memory_error(exc) and _use_cpu_from_now_on():
                continue
            raise


def _stream_once(prompt):
    with requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=_request_body(prompt, stream=True),
        stream=True,
        timeout=600,
    ) as response:
        _raise_for_ollama_error(response)
        for line in response.iter_lines():
            if not line:
                continue
            payload = json.loads(line)
            token = payload.get("response", "")
            if token:
                yield token
            if payload.get("done"):
                break


def answer(question, user_id, n_results=5):
    """Full non-streaming pipeline, used by /api/query and the isolation test."""
    retrieved = retrieve(question, user_id, n_results)

    if not retrieved["documents"]:
        return {
            "answer": "I don't know — no emails matched for this user.",
            "sources": [],
            "retrieval_seconds": retrieved["retrieval_seconds"],
            "generation_seconds": 0.0,
            "grounded": False,
        }

    start = time.time()
    output = generate(build_prompt(retrieved["documents"], question))
    return {
        "answer": output.strip(),
        "sources": retrieved["sources"],
        "retrieval_seconds": retrieved["retrieval_seconds"],
        "generation_seconds": round(time.time() - start, 3),
        "grounded": True,
    }
