from __future__ import annotations

from pathlib import Path


CODE_TYPE_ALIASES = {
    "ts": "typescript",
    "typescript": "typescript",
    "go": "golang",
    "golang": "golang",
}

CODE_TYPE_LABELS = {
    "typescript": "TypeScript",
    "golang": "Golang",
}

CODE_TYPE_EXTENSIONS = {
    "typescript": "ts",
    "golang": "go",
}


def normalize_code_type(code_type: str | None) -> str:
    value = (code_type or "typescript").strip().lower()
    normalized = CODE_TYPE_ALIASES.get(value)
    if normalized:
        return normalized
    raise ValueError(f"Unsupported code type: {code_type!r}")


def code_type_label(code_type: str | None) -> str:
    return CODE_TYPE_LABELS[normalize_code_type(code_type)]


def code_extension(code_type: str | None) -> str:
    return CODE_TYPE_EXTENSIONS[normalize_code_type(code_type)]


def build_output_filename(base_name: str | None, code_type: str | None) -> str:
    raw_name = (base_name or "sheji").strip() or "sheji"
    candidate = Path(raw_name)
    stem = candidate.stem if candidate.suffix else candidate.name
    stem = stem.strip() or "sheji"
    return f"{stem}.{code_extension(code_type)}"


def default_output_name(design_file: Path | None) -> str:
    if design_file is None:
        return "sheji"
    stem = design_file.stem.strip()
    return stem or "sheji"
