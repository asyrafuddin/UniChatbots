# Docker image for the backend on a Hugging Face Space (CPU). Built by HF from the files space/deploy.py uploads.
FROM python:3.12-slim

# HF Spaces run the container as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 APP_CONFIG_OVERRIDES=config.space.yaml
WORKDIR /home/user/app

# CPU-only PyTorch (the default Linux wheel bundles ~2 GB of unused GPU libraries)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Download the embedder + re-ranker from the HF Hub at build time, so the Space starts fast
COPY --chown=user config.yaml config.space.yaml ./
COPY --chown=user src/__init__.py src/config.py src/
RUN python -c "from src.config import load_config; from sentence_transformers import SentenceTransformer, CrossEncoder; \
c = load_config(); SentenceTransformer(c['embedding']['model']); CrossEncoder(c['reranker']['model'])"

COPY --chown=user src/ src/
EXPOSE 7860
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
