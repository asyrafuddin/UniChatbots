"""FastAPI backend: the website sends a question here and gets an answer with citations.

Every question and answer is saved to the Supabase `chats` table.

Run (from the project root, with the .venv active):
    uvicorn src.api.main:app --port 8000
Then open http://localhost:8000/docs to try the API in your browser.
"""

import logging
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.api.ratelimit import RateLimiter, client_id
from src.config import load_config
from src.generate.answer import answer_question

log = logging.getLogger("uvicorn.error")
CFG = load_config()


@dataclass
class Services:
    """Everything a request needs, loaded once at startup (loading the models takes ~20 s)."""

    retriever: object
    llm_client: object
    supabase: object | None


def load_services(cfg: dict) -> Services:
    """Load the embedder + re-ranker, connect to Supabase and create the LLM client."""
    from src.generate.llm import make_llm_client
    from src.retrieve.build import build_retrievers, with_reranking
    from src.retrieve.supabase_store import get_supabase

    supabase, llm_client = get_supabase(), make_llm_client(cfg)  # fail fast on missing keys, before the models load
    kind = cfg["api"]["retriever"]
    retriever = next(iter(with_reranking(cfg, build_retrievers(cfg, (kind,))).values()))
    return Services(retriever=retriever, llm_client=llm_client, supabase=supabase)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=CFG["api"]["max_question_chars"])
    language: str | None = Field(default=None, description="en / ms / ko / mixed (the website's guess)")


class Citation(BaseModel):
    id: str
    source: str
    page_or_url: int | str
    section: str


class ChatResponse(BaseModel):
    id: str | None = Field(description="row id in the Supabase chats table (null if saving failed)")
    answer: str
    citations: list[Citation]
    found: bool


def save_chat(supabase, cfg: dict, request: ChatRequest, result: dict, latency_ms: int) -> str | None:
    """Insert the exchange into the chats table; a failure is logged but doesn't break the answer."""
    if supabase is None:
        return None
    row = {"question": request.question, "language": request.language, "answer": result["answer"],
           "citations": result["citations"], "found": result["found"], "model": result["model"],
           "latency_ms": latency_ms}
    try:
        return supabase.table(cfg["supabase"]["chats_table"]).insert(row).execute().data[0]["id"]
    except Exception:
        log.exception("Could not save the chat to Supabase")
        return None


def create_app(services: Services | None = None, cfg: dict = CFG) -> FastAPI:
    """Build the app. Tests pass fake services; normally they're loaded at startup."""
    lock = threading.Lock()  # one question at a time: the models share one GPU and 8 GB of RAM
    limiter = RateLimiter(cfg["api"]["rate_limit_per_minute"], cfg["api"]["rate_limit_per_day"])

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services or load_services(cfg)
        log.info("Models loaded — ready for questions")
        yield

    app = FastAPI(title="University Assistant API", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=cfg["api"]["cors_origins"],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.get("/")
    def root() -> dict:
        """What visitors see when they open the Space page."""
        return {"service": "ERICA Assistant API", "health": "/api/health", "docs": "/docs"}

    @app.get("/api/health")
    def health() -> dict:
        """Lets the website show whether the backend is up."""
        return {"status": "ok", "retriever": cfg["api"]["retriever"] + "+rerank", "llm": cfg["llm"]["model"]}

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest, http: Request) -> ChatResponse:
        """Answer one question from the documents (blocking work runs in FastAPI's thread pool)."""
        refused = limiter.check(client_id(http.headers, http.client.host if http.client else "unknown"))
        if refused:
            raise HTTPException(status_code=429, detail=f"Rate limited: {refused}")
        s: Services = app.state.services
        start = time.perf_counter()
        try:
            with lock:
                result = answer_question(request.question, s.retriever, s.llm_client, cfg)
        except Exception as e:
            log.exception("Answering failed")
            raise HTTPException(status_code=502, detail=f"Answering failed: {type(e).__name__}") from e
        latency_ms = round(1000 * (time.perf_counter() - start))
        chat_id = save_chat(s.supabase, cfg, request, result, latency_ms)
        return ChatResponse(id=chat_id, answer=result["answer"], citations=result["citations"],
                            found=result["found"])

    return app


app = create_app()
