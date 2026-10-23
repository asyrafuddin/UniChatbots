"""The FastAPI endpoints with fake services (no models, no HF or Supabase calls)."""

from fastapi.testclient import TestClient

from src.api.main import Services, create_app
from tests.test_generate import FakeLLM, FakeRetriever
from tests.test_supabase_store import FakeClient


def make_client(reply="Dorm applications open in January [1].", supabase=None):
    services = Services(retriever=FakeRetriever(), llm_client=FakeLLM(reply), supabase=supabase)
    return TestClient(create_app(services))


def test_health():
    with make_client() as client:
        assert client.get("/api/health").json()["status"] == "ok"


def test_chat_returns_answer_and_citations():
    with make_client() as client:
        res = client.post("/api/chat", json={"question": "When can I apply for the dorm?", "language": "en"})
    body = res.json()
    assert res.status_code == 200 and body["found"] is True
    assert body["citations"][0]["id"] == "c1"


def test_chat_is_saved_to_supabase():
    supabase = FakeClient()
    with make_client(supabase=supabase) as client:
        client.post("/api/chat", json={"question": "dorm?"})
    inserted = [args[0] for name, args in supabase.log if name == "insert"][0]
    assert inserted["question"] == "dorm?" and inserted["found"] is True and inserted["latency_ms"] >= 0


def test_empty_question_rejected():
    with make_client() as client:
        assert client.post("/api/chat", json={"question": ""}).status_code == 422


def test_cors_allows_the_vite_dev_server():
    with make_client() as client:
        res = client.options("/api/chat", headers={"Origin": "http://localhost:5173",
                                                   "Access-Control-Request-Method": "POST"})
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_rate_limit_returns_429(cfg):
    import copy

    small = copy.deepcopy(cfg)
    small["api"]["rate_limit_per_minute"] = 1
    services = Services(retriever=FakeRetriever(), llm_client=FakeLLM("ok [1]"), supabase=None)
    with TestClient(create_app(services, small)) as client:
        assert client.post("/api/chat", json={"question": "a"}).status_code == 200
        assert client.post("/api/chat", json={"question": "b"}).status_code == 429


def test_cors_allows_the_vercel_site():
    with make_client() as client:
        res = client.options("/api/chat", headers={"Origin": "https://uni-chatbots.vercel.app",
                                                   "Access-Control-Request-Method": "POST"})
    assert res.headers["access-control-allow-origin"] == "https://uni-chatbots.vercel.app"
