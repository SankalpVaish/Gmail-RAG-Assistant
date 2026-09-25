"""FastAPI backend for the Gmail RAG Assistant.

Run with:
    uvicorn app:app --reload

Then open http://localhost:8000
"""

import json
import os
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import rag_core

app = FastAPI(title="Gmail RAG Assistant", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Progress state for the long-running Gmail ingestion job.
_ingest_job = {"running": False, "message": "", "result": None, "error": None}
_ingest_lock = threading.Lock()


class QueryRequest(BaseModel):
    question: str
    user_id: str
    n_results: int = 5


class IsolationRequest(BaseModel):
    question: str
    owner_id: str
    intruder_id: str


class GmailIngestRequest(BaseModel):
    max_results: int = 50


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/status")
def status():
    """Everything the UI needs to render its header on load."""
    users = rag_core.list_users()
    return {
        "users": users,
        "user_stats": {user: rag_core.user_stats(user) for user in users},
        "total_chunks": rag_core.get_collection().count(),
        "ollama": rag_core.ollama_status(),
        "gmail_credentials_present": os.path.exists("credentials.json"),
        "demo_data_available": os.path.exists(rag_core.DEMO_DATA_FILE),
    }


@app.get("/api/demo/preview")
def preview_demo():
    """Return the demo dataset for preview before ingestion."""
    if not os.path.exists(rag_core.DEMO_DATA_FILE):
        raise HTTPException(404, f"{rag_core.DEMO_DATA_FILE} not found")
    with open(rag_core.DEMO_DATA_FILE, "r", encoding="utf-8") as f:
        emails = json.load(f)

    # Group by user and summarize
    by_user = {}
    for email in emails:
        user = email["user_id"]
        if user not in by_user:
            by_user[user] = []
        by_user[user].append({
            "subject": email["subject"],
            "from": email["sender"],
            "date": email["timestamp"],
            "preview": email["body"][:200] + "..." if len(email["body"]) > 200 else email["body"]
        })

    return {
        "total_emails": len(emails),
        "users": list(by_user.keys()),
        "by_user": by_user
    }


@app.post("/api/ingest/demo")
def ingest_demo():
    """Load the synthetic dataset — lets anyone try the app without Gmail."""
    if not os.path.exists(rag_core.DEMO_DATA_FILE):
        raise HTTPException(404, f"{rag_core.DEMO_DATA_FILE} not found")
    return rag_core.ingest_demo_data(reset=True)


@app.post("/api/ingest/gmail")
def ingest_gmail(request: GmailIngestRequest):
    """Kick off real Gmail ingestion in a background thread.

    OAuth opens a browser window on the machine running this server, so this is
    a local-first flow by design.
    """
    if not os.path.exists("credentials.json"):
        raise HTTPException(
            400,
            "credentials.json not found. Add your Google OAuth desktop "
            "credentials to the project folder, or use demo mode.",
        )

    with _ingest_lock:
        if _ingest_job["running"]:
            raise HTTPException(409, "An ingestion job is already running.")
        _ingest_job.update(running=True, message="Starting...", result=None, error=None)

    def run():
        try:
            result = rag_core.ingest_gmail(
                max_results=request.max_results,
                progress=lambda m: _ingest_job.update(message=m),
            )
            _ingest_job.update(result=result, message="Done.")
        except Exception as exc:
            _ingest_job.update(error=str(exc), message="Failed.")
        finally:
            _ingest_job.update(running=False)

    threading.Thread(target=run, daemon=True).start()
    return {"started": True}


@app.get("/api/ingest/status")
def ingest_status():
    return dict(_ingest_job)


@app.post("/api/query")
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question is empty.")
    try:
        return rag_core.answer(request.question, request.user_id, request.n_results)
    except Exception as exc:
        raise HTTPException(502, f"Ollama call failed: {exc}")


@app.get("/api/query/stream")
def query_stream(question: str, user_id: str, n_results: int = 5):
    """Server-sent events: sources first, then tokens, then timings."""

    def events():
        def send(event, data):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            retrieved = rag_core.retrieve(question, user_id, n_results)
            yield send("sources", {
                "sources": retrieved["sources"],
                "retrieval_seconds": retrieved["retrieval_seconds"],
            })

            if not retrieved["documents"]:
                yield send("token", {"text": "I don't know — no emails matched for this user."})
                yield send("done", {"generation_seconds": 0.0, "grounded": False})
                return

            prompt = rag_core.build_prompt(retrieved["documents"], question)
            start = time.time()
            for token in rag_core.generate_stream(prompt):
                yield send("token", {"text": token})
            yield send("done", {
                "generation_seconds": round(time.time() - start, 3),
                "grounded": True,
            })
        except Exception as exc:
            yield send("error", {"message": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/isolation-test")
def isolation_test(request: IsolationRequest):
    """Run the same question as the data owner and as another user.

    Note on what counts as a pass: vector search returns the nearest neighbours
    *within* the metadata filter and applies no similarity threshold, so a user
    who has any data at all will always get their own top-k chunks back. An
    empty result is therefore the wrong thing to assert on. The real test is
    whether any chunk handed to the other user belongs to the owner.
    """
    owner = rag_core.retrieve(request.question, request.owner_id)
    intruder = rag_core.retrieve(request.question, request.intruder_id)

    leaked = [s for s in intruder["sources"] if s["user_id"] == request.owner_id]

    return {
        "question": request.question,
        "owner": {
            "user_id": request.owner_id,
            "chunks_retrieved": len(owner["documents"]),
            "subjects": [s["subject"] for s in owner["sources"]],
        },
        "intruder": {
            "user_id": request.intruder_id,
            "chunks_retrieved": len(intruder["documents"]),
            "subjects": [s["subject"] for s in intruder["sources"]],
            "owner_chunks_retrieved": len(leaked),
        },
        "leaked_subjects": [s["subject"] for s in leaked],
        "isolation_held": len(leaked) == 0,
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Gmail RAG Assistant")
    print("=" * 60)
    print("Server starting at: http://127.0.0.1:8100")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8100, log_level="info")
