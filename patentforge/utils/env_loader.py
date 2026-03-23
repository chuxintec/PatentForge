from __future__ import annotations

import os
from pathlib import Path

from patentforge.utils.prompt_loader import repo_root


def _parse_env_line(line: str) -> tuple[str, str] | None:
    content = line.strip()
    if not content or content.startswith("#"):
        return None

    if content.startswith("export "):
        content = content[7:].lstrip()

    if "=" not in content:
        return None

    key, value = content.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]

    return key, value


def load_env_file(path: str | Path, override: bool = False) -> dict[str, str]:
    env_path = Path(path).expanduser().resolve()
    if not env_path.exists() or not env_path.is_file():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if not parsed:
            continue

        key, value = parsed
        if not override and key in os.environ:
            continue

        os.environ[key] = value
        loaded[key] = value

    return loaded


def project_env_paths() -> list[Path]:
    candidates = [Path.cwd() / ".env", repo_root() / ".env"]
    paths: list[Path] = []
    seen: set[Path] = set()

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        paths.append(resolved)

    return paths


def load_project_env(override: bool = False) -> dict[str, str]:
    loaded: dict[str, str] = {}
    for env_path in project_env_paths():
        loaded.update(load_env_file(env_path, override=override))
    return loaded
