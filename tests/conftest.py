"""Shared test fixtures: config, the real tokenizer, and a fake corpus on disk."""

import copy

import pytest

from src.config import load_config
from src.ingest.fake_data import make_fake_corpus
from src.ingest.tokens import make_token_counter


@pytest.fixture(scope="session")
def cfg():
    """The project's config.yaml (tests copy it before changing anything)."""
    return load_config()


@pytest.fixture(scope="session")
def count(cfg):
    """Token counter using the real embedding tokenizer (downloaded once, then cached)."""
    return make_token_counter(cfg["embedding"]["model"])


@pytest.fixture(scope="session")
def fake_raw_dir(tmp_path_factory):
    """A temporary raw/ folder with the fake PDF and web pages."""
    return make_fake_corpus(tmp_path_factory.mktemp("raw"))


@pytest.fixture
def small_cfg(cfg):
    """Config with a tiny chunk size so the splitting and overlap code gets exercised."""
    small = copy.deepcopy(cfg)
    small["chunking"]["max_tokens"] = 60
    return small
