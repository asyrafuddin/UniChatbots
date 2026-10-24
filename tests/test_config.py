"""Config overrides (config.space.yaml) and the Space upload list."""

from src.config import load_config, merge


def test_merge_overrides_nested_keys_only():
    base = {"retrieval": {"device": "auto", "top_k": 30}, "llm": {"model": "x"}}
    merged = merge(base, {"retrieval": {"device": "cpu"}})
    assert merged == {"retrieval": {"device": "cpu", "top_k": 30}, "llm": {"model": "x"}}
    assert base["retrieval"]["device"] == "auto"  # original untouched


def test_space_overrides_applied_from_env(monkeypatch):
    monkeypatch.setenv("APP_CONFIG_OVERRIDES", "config.space.yaml")
    cfg = load_config()
    assert cfg["retrieval"]["device"] == "cpu"
    assert cfg["reranker"]["model"] == "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    assert cfg["reranker"]["top_n"] == 5  # everything else still comes from config.yaml


def test_space_upload_has_code_but_no_secrets_or_data():
    from space.deploy import files_to_upload

    files = files_to_upload()
    assert {"Dockerfile", "README.md", "requirements.txt", "config.yaml", "src/api/main.py"} <= set(files)
    assert not any(name.startswith(("data/", "web/", "eval/")) or ".env" in name for name in files)
