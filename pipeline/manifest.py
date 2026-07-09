"""Manifest: fuente de verdad de la selección curada y del estado del espejo (§3.7).

Vive en _meta/manifest.json del repo conocimiento. Nadie lo edita a mano (RNF-02);
se alimenta por las dos vías de curaduría (DD-17) y lo mantiene el pipeline.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Manifest:
    def __init__(self, path: Path, data: dict | None = None):
        self.path = Path(path)
        self.data = data or {
            "schema": SCHEMA,
            "page_token": None,  # changes.getStartPageToken persistido (DD-01)
            "curated": [],       # selección curada: drive_id, kind, dest, source, name
            "files": {},         # drive_id -> estado de cada archivo espejado
            "folders": {},       # cache drive_id -> {name, parent} para resolver ancestros
        }

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        path = Path(path)
        if path.exists():
            return cls(path, json.loads(path.read_text(encoding="utf-8")))
        return cls(path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # --- selección curada ---------------------------------------------------

    @property
    def curated(self) -> list[dict]:
        return self.data["curated"]

    def curated_by_id(self) -> dict[str, dict]:
        return {c["drive_id"]: c for c in self.curated}

    def add_curated(self, drive_id: str, kind: str, dest: str, source: str, name: str) -> dict:
        existing = self.curated_by_id().get(drive_id)
        if existing:
            return existing
        entry = {
            "drive_id": drive_id,
            "kind": kind,          # "folder" | "file"
            "dest": dest.strip("/").replace("\\", "/"),
            "source": source,      # "chat" | "knowledge-folder" | "shortcut" | "onboarding"
            "name": name,
            "added": now_utc(),
        }
        self.curated.append(entry)
        return entry

    def remove_curated(self, drive_id: str) -> dict | None:
        entry = self.curated_by_id().get(drive_id)
        if entry:
            self.curated.remove(entry)
        return entry

    # --- archivos espejados ---------------------------------------------------

    @property
    def files(self) -> dict[str, dict]:
        return self.data["files"]

    @property
    def folders(self) -> dict[str, dict]:
        return self.data["folders"]

    @property
    def page_token(self):
        return self.data.get("page_token")

    @page_token.setter
    def page_token(self, value) -> None:
        self.data["page_token"] = value

    def pending_commits(self) -> list[dict]:
        return [f for f in self.files.values() if f.get("pending_commit")]

    def errores(self) -> list[dict]:
        return [f for f in self.files.values() if f.get("error")]
