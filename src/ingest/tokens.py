"""Count tokens with the embedding model's own tokenizer."""

from collections.abc import Callable
from functools import lru_cache


def make_token_counter(model_name: str) -> Callable[[str], int]:
    """Load the tokenizer of `model_name` from the HF Hub and return a cached token-counting function.

    Special tokens (<s>, </s>) are not counted; the model adds those itself.
    """
    from transformers import AutoTokenizer  # imported here so other modules don't pay the cost

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    @lru_cache(maxsize=200_000)
    def count_tokens(text: str) -> int:
        return len(tokenizer(text, add_special_tokens=False, verbose=False)["input_ids"])

    return count_tokens
