import json
import os
from pathlib import Path
from typing import Any, Dict


CONFIG_PATH = Path("/root/.fullauto/config.json")
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _find_repo_root() -> Path:
    """Return the repo root by walking up until .git is found; fallback to parent of src/."""
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".git").is_dir():
            return path
        path = path.parent
    return Path(__file__).resolve().parent.parent


def _default_config() -> Dict[str, Any]:
    return {"REPO_PATH": str(_find_repo_root())}


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        cfg = _default_config()
        save_config(cfg)
        return cfg
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        cfg = _default_config()
        save_config(cfg)
        return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_repo_path() -> str:
    cfg = load_config()
    repo = cfg.get("REPO_PATH")
    if repo and os.path.isabs(repo) and os.path.isdir(repo):
        return repo
    repo_root = str(_find_repo_root())
    cfg["REPO_PATH"] = repo_root
    save_config(cfg)
    return repo_root


def set_repo_path(path: str) -> None:
    cfg = load_config()
    cfg["REPO_PATH"] = path
    save_config(cfg)
