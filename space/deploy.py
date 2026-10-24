"""Create/update the Hugging Face Space that runs the backend, and copy its secrets from .env.

Needs an HF_TOKEN with write access to your repos. HF then builds the Docker image (~10 min the first time).

Usage (from the project root, with the .venv active):
    python -m space.deploy
"""

from pathlib import Path

from src.config import PROJECT_ROOT, load_config, require_env

SPACE_DIR = PROJECT_ROOT / "space"


def files_to_upload() -> dict[str, Path]:
    """{path in the Space repo: local file}: the Docker setup, config and the Python package (no data, no secrets)."""
    files = {name: SPACE_DIR / name for name in ("Dockerfile", "README.md", "requirements.txt")}
    files |= {name: PROJECT_ROOT / name for name in ("config.yaml", "config.space.yaml")}
    for path in sorted((PROJECT_ROOT / "src").rglob("*.py")):
        files[path.relative_to(PROJECT_ROOT).as_posix()] = path
    return files


def main() -> None:
    """Command-line entry point."""
    from huggingface_hub import CommitOperationAdd, HfApi

    cfg = load_config()
    repo_id, secrets = cfg["space"]["repo_id"], cfg["space"]["secrets"]
    api = HfApi(token=require_env("HF_TOKEN"))

    api.create_repo(repo_id, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
    for name in secrets:
        api.add_space_secret(repo_id, name, require_env(name))
    print(f"Space {repo_id}: secrets set ({', '.join(secrets)})")

    files = files_to_upload()
    operations = [CommitOperationAdd(path_in_repo=dest, path_or_fileobj=str(src)) for dest, src in files.items()]
    api.create_commit(repo_id, repo_type="space", operations=operations, commit_message="Deploy backend")
    owner, name = repo_id.split("/")
    print(f"Uploaded {len(files)} files. Build logs: https://huggingface.co/spaces/{repo_id}")
    print(f"API (once built): https://{owner.lower()}-{name.lower()}.hf.space/api/health")


if __name__ == "__main__":
    main()
