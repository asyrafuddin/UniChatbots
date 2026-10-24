---
title: ERICA Assistant API
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: RAG backend for a Hanyang ERICA student chatbot
---

# ERICA Assistant API

Backend for an unofficial student chatbot about Hanyang University ERICA. It answers in English, Malay
and Korean, only from official documents, with citations.

Question → `BAAI/bge-m3` embedding → Supabase pgvector search (top 30) → `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
re-ranker (top 5) → `Qwen/Qwen3.8-27B` (via `huggingface_hub.InferenceClient`) → answer with [1], [2] citations.

- `GET /api/health`: status
- `POST /api/chat` `{"question": "..."}`: answer + citations (rate limited)
- `/docs`: interactive API docs

Secrets (Space settings): `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `CEREBRAS_API_KEY`.
