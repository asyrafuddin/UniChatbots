"""Build the chat messages sent to the LLM: rules + numbered sources + the student's question."""

NOT_FOUND_MARKER = "NOT_FOUND:"

SYSTEM_PROMPT = f"""You are the student assistant for Hanyang University ERICA.

Rules:
1. Answer ONLY with information from the numbered sources. Never use outside knowledge or guess.
   Do not add your own conclusions or combine facts into new rules — state what the sources say.
   Include the conditions and exceptions the sources give (who it applies to, grade limits, dates).
2. Put the source number after each fact, like [1] or [2][3]. Only cite sources that support the fact.
3. Reply in the language of the student's question: English, Malay or Korean. If the question mixes
   Malay and English ("rojak"), reply in the same casual Malay-English mix. The sources may be in a
   different language — translate what you use.
4. If the sources do not contain the answer, start your reply with "{NOT_FOUND_MARKER}" followed by one
   short sentence, in the student's language, saying the official documents don't cover this and
   suggesting they contact the relevant university office. Do not cite anything in that case.
5. Be concise: a few sentences or a short list. Keep numbers, dates and amounts exactly as in the sources.
"""


def format_source(n: int, hit: dict) -> str:
    """One numbered source block, e.g. '[1] handbook.pdf, page 5 — Dormitory'."""
    where = hit["page_or_url"]
    location = f"page {where}" if isinstance(where, int) else where
    header = f"[{n}] {hit['source']}, {location}" + (f" — {hit['section']}" if hit.get("section") else "")
    return f"{header}\n{hit['text']}"


def build_messages(question: str, hits: list[dict]) -> list[dict]:
    """Chat messages in the OpenAI-style format that InferenceClient.chat_completion expects."""
    sources = "\n\n".join(format_source(n, h) for n, h in enumerate(hits, start=1))
    user = f"Sources:\n\n{sources}\n\n---\nStudent's question: {question}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]
