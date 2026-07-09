"""Conversión a markdown, imágenes, frontmatter y fichas de Sheets (§3.3, §5.1).

- Docs → markdown nativo del export (DD-02); imágenes base64 → _assets/ (DD-04).
- Sheets → ficha md + CSV por hoja (DD-14): los números viven en CSV y el agente
  calcula con código, no lee tablas en tokens.
- docx/xlsx/pdf subidos → markitdown (fallback).
"""

import base64
import csv
import io
import re
import unicodedata
from pathlib import Path

import yaml

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_FOLDER = "application/vnd.google-apps.folder"
GOOGLE_SHORTCUT = "application/vnd.google-apps.shortcut"

KNOWN_EXTENSIONS = (".docx", ".xlsx", ".pptx", ".doc", ".xls", ".pdf", ".txt", ".md", ".csv")


def slugify(name: str, max_len: int = 60) -> str:
    stem = name
    for ext in KNOWN_EXTENSIONS:
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    norm = unicodedata.normalize("NFKD", stem)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    norm = re.sub(r"-{2,}", "-", norm)
    return norm[:max_len].rstrip("-") or "documento"


# --- frontmatter (§5.1, DD-08) -------------------------------------------------

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)

FRONTMATTER_ORDER = [
    "titulo",
    "drive_id",
    "drive_url",
    "modificado",
    "modificado_por",
    "contexto",
    "area",
    "tipo",
    "estado",
    "importancia",
    "related",
    "resumen",
]

# Campos que mantiene el agente: el pipeline nunca los pisa en updates.
AGENT_FIELDS = ("contexto", "area", "tipo", "estado", "importancia", "related", "resumen")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = _FM_RE.match(text)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text
    if not isinstance(data, dict):
        return {}, text
    return data, text[match.end():]


def dump_frontmatter(data: dict) -> str:
    ordered = {k: data[k] for k in FRONTMATTER_ORDER if k in data}
    ordered.update({k: v for k, v in data.items() if k not in ordered})
    body = yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, width=88)
    return f"---\n{body}---\n"


def merge_frontmatter(existing: dict, fresh: dict) -> dict:
    """Trazabilidad la pisa el pipeline; lo del agente se preserva (§5.1)."""
    merged = dict(fresh)
    for key in AGENT_FIELDS:
        value = existing.get(key)
        if value not in (None, "", []):
            merged[key] = value
    for key, value in existing.items():
        if key not in merged:
            merged[key] = value
    return merged


# --- imágenes (DD-04) -----------------------------------------------------------

_IMG_REF_RE = re.compile(
    r"^\[([^\]]+)\]:\s*<?data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+?)>?\s*$",
    re.MULTILINE,
)
_IMG_INLINE_RE = re.compile(
    r"(!\[[^\]]*\]\()data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)(\))"
)


def extract_images(md: str, doc_dir: Path, slug: str) -> str:
    """Extrae imágenes base64 a _assets/<slug>/img-N.ext y deja links relativos."""
    assets_rel = f"_assets/{slug}"
    counter = 0

    def _save(fmt: str, b64: str) -> str:
        nonlocal counter
        counter += 1
        ext = {"jpeg": "jpg", "svg+xml": "svg"}.get(fmt, fmt)
        target_dir = doc_dir / "_assets" / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"img-{counter}.{ext}"
        (target_dir / filename).write_bytes(base64.b64decode(re.sub(r"\s+", "", b64)))
        return f"{assets_rel}/{filename}"

    md = _IMG_INLINE_RE.sub(
        lambda m: f"{m.group(1)}{_save(m.group(2), m.group(3))}{m.group(4)}", md
    )
    md = _IMG_REF_RE.sub(lambda m: f"[{m.group(1)}]: {_save(m.group(2), m.group(3))}", md)
    return md


# --- Sheets (DD-14) -----------------------------------------------------------

def rows_to_csv(rows: list[list]) -> str:
    width = max((len(r) for r in rows), default=0)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        row = list(row) + [""] * (width - len(row))
        writer.writerow(row)
    return buf.getvalue()


def sheet_ficha_body(titulo: str, slug: str, hojas: dict[str, tuple[str, list[list]]]) -> str:
    """Cuerpo de la ficha md de un Sheet: esquema por hoja, datos en CSV."""
    lines = [
        f"# {titulo}",
        "",
        f"> Ficha de Google Sheet. Los datos viven en `{slug}.data/` (un CSV por hoja).",
        "> Para números: ejecutar código (pandas) sobre los CSV — no leer tablas en tokens.",
        "",
        "## Hojas",
        "",
        "| Hoja | CSV | Filas de datos | Columnas |",
        "|---|---|---|---|",
    ]
    for title, (csv_name, rows) in hojas.items():
        cols = ", ".join(str(c) for c in rows[0]) if rows else "—"
        n = max(len(rows) - 1, 0)
        lines.append(f"| {title} | [{csv_name}]({slug}.data/{csv_name}) | {n} | {cols} |")
    lines.append("")
    return "\n".join(lines)


# --- fallback markitdown (DD-02) -------------------------------------------------

def markitdown_convert(path: Path) -> str:
    from markitdown import MarkItDown

    result = MarkItDown().convert(str(path))
    return result.text_content
