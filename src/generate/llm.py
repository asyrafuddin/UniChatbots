"""Call an open LLM on the Hugging Face Hub through Inference Providers (huggingface_hub.InferenceClient).

The model runs on Hugging Face's partner servers, not on this Mac — an 8 GB laptop can't hold a
27B-parameter model next to the embedder and re-ranker. With api_key_env: HF_TOKEN the calls are
billed to your HF credits; with a provider's own key (e.g. CEREBRAS_API_KEY) InferenceClient sends
the request straight to that provider and its free tier applies. The code is the same either way.
"""

import re

from src.config import require_env


def make_llm_client(cfg: dict):
    """An InferenceClient for llm.model on llm.provider, using the key named by llm.api_key_env in .env."""
    from huggingface_hub import InferenceClient

    llm = cfg["llm"]
    return InferenceClient(model=llm["model"], provider=llm["provider"], api_key=require_env(llm["api_key_env"]),
                           timeout=llm["timeout_s"])


def strip_thinking(text: str) -> str:
    """Remove <think>…</think> reasoning that some models (e.g. Qwen) put before the real answer."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def chat(client, messages: list[dict], cfg: dict) -> str:
    """Send the messages and return the model's reply text (raises if the model produced no answer)."""
    llm = cfg["llm"]
    response = client.chat_completion(messages, max_tokens=llm["max_tokens"], temperature=llm["temperature"],
                                      extra_body={"reasoning_effort": llm["reasoning_effort"]})
    choice = response.choices[0]
    text = strip_thinking(choice.message.content or "")
    if not text:  # e.g. all max_tokens were spent on thinking (finish_reason "length")
        raise RuntimeError(f"The LLM returned no answer (finish_reason={choice.finish_reason})")
    return text
