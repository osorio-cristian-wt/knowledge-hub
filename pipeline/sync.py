"""Motor de sincronización Drive → espejo local (diseño §3).

Separación determinista/criterio (§1): este módulo hace todo lo que NO requiere
juicio — detectar cambios, exportar, convertir, escribir el espejo y dejar los
commits listos. Resúmenes, clasificación fina y avisos son de las skills.

Commits en dos fases (§3.4, DD-16):
  1. `run`/`import` escriben el espejo y marcan cada archivo con `pending_commit`
     en el manifest (el diff queda visible en el working tree).
  2. La skill lee cada diff, redacta la primera línea del mensaje y llama
     `commit <drive_id> --summary "..."`. Si el agente no llega, la próxima
     corrida commitea lo pendiente con mensaje genérico ANTES de tocar el
     espejo: el sync nunca queda bloqueado por el LLM.

Si una corrida se corta a mitad, el page_token no avanza y la siguiente
reprocesa los mismos cambios; el skip por contenido (§3.8) lo hace idempotente.
"""

import json
import shutil
from pathlib import Path

from . import auth, config, convert, gitops
from .drive import AccessError, Drive, ExportLimitError
from .manifest import Manifest, now_utc

GENERIC_SUMMARIES = {
    "nuevo": "documento nuevo espejado desde Drive",
    "actualizado": "actualizado en Drive",
    "archivado": "archivado (baja o eliminación en Drive)",
    "reclasificado": "reclasificado en el esqueleto",
}


class Abort(Exception):
    """Corte controlado de un comando; el payload va como JSON a stdout."""

    def __init__(self, payload: dict):
        super().__init__(payload.get("error", ""))
        self.payload = payload


def _area_of(path_rel: str | None) -> str:
    parts = (path_rel or "").replace("\\", "/").split("/")
    if len(parts) >= 3:
        return parts[1]
    if len(parts) == 2:
        return parts[0]
    return "general"


def _slug_of(entry: dict) -> str:
    if entry.get("path"):
        return Path(entry["path"]).stem
    return convert.slugify(entry.get("name") or entry.get("drive_id", "documento"))


def _importancia_de(root: Path, entry: dict) -> str:
    path = entry.get("path")
    if path and (root / path).exists():
        fm, _ = convert.parse_frontmatter((root / path).read_text(encoding="utf-8"))
        if fm.get("importancia"):
            return fm["importancia"]
    return "normal"


def _sidecars(path_rel: str):
    """Rutas hermanas de un .md: datos de Sheet y assets de imágenes."""
    path_rel = path_rel.replace("\\", "/")
    stem = path_rel[:-3] if path_rel.endswith(".md") else path_rel
    parent = str(Path(path_rel).parent).replace("\\", "/")
    slug = Path(path_rel).stem
    yield f"{stem}.data"
    yield f"_assets/{slug}" if parent == "." else f"{parent}/_assets/{slug}"


class Sync:
    def __init__(self, drive: Drive | None, manifest: Manifest, cfg: dict, root: Path):
        self.drive = drive
        self.manifest = manifest
        self.cfg = cfg
        self.root = Path(root)
        self.events: list[dict] = []

    # ------------------------------------------------------------------ scope

    def scope_of(self, meta: dict):
        """Sube por la cadena de padres hasta una entrada curada (§3.2).

        Devuelve (entrada_curada, rel_parts) o None si el cambio queda fuera
        de la selección y se descarta.
        """
        curated = self.manifest.curated_by_id()
        if meta["id"] in curated:
            return curated[meta["id"]], ()
        parts: list[str] = []
        seen: set[str] = set()
        parent = (meta.get("parents") or [None])[0]
        while parent and parent not in seen:
            seen.add(parent)
            if parent in curated:
                return curated[parent], tuple(reversed(parts))
            info = self.manifest.folders.get(parent)
            if info is None:
                try:
                    pmeta = self.drive.get_meta(parent)
                except AccessError:
                    return None
                info = {"name": pmeta["name"], "parent": (pmeta.get("parents") or [None])[0]}
                self.manifest.folders[parent] = info
            parts.append(info["name"])
            parent = info.get("parent")
        return None

    # ------------------------------------------------------------ entrada

    def handle_change(self, change: dict) -> None:
        fid = change.get("fileId")
        entry = self.manifest.files.get(fid)
        if change.get("removed"):
            if entry and entry.get("estado") != "archivado":
                self.archive(entry, "eliminado en Drive")
            return
        meta = change.get("file")
        if meta:
            self.handle_meta(meta)

    def handle_meta(self, meta: dict, curated: dict | None = None, rel_parts=None) -> None:
        mime = meta["mimeType"]
        if mime == convert.GOOGLE_FOLDER:
            self.manifest.folders[meta["id"]] = {
                "name": meta["name"],
                "parent": (meta.get("parents") or [None])[0],
            }
            return
        entry = self.manifest.files.get(meta["id"])
        if meta.get("trashed"):
            if entry and entry.get("estado") != "archivado":
                self.archive(entry, "enviado a la papelera en Drive")
            return
        if curated is None:
            scope = self.scope_of(meta)
            if scope is None:
                return  # fuera de la selección curada: se descarta (§3.2)
            curated, rel_parts = scope
        if mime == convert.GOOGLE_SHORTCUT:
            self._handle_shortcut(meta, curated, rel_parts or ())
            return
        self.mirror(meta, curated, rel_parts or ())

    def _handle_shortcut(self, meta: dict, curated: dict, rel_parts) -> None:
        """Atajos en carpetas curadas → se registran por su targetId real (DD-17)."""
        target_id = (meta.get("shortcutDetails") or {}).get("targetId")
        if not target_id:
            return
        try:
            target = self.drive.get_meta(target_id)
        except AccessError:
            self._record_error(meta, "acceso")
            return
        dest = "/".join(
            [curated["dest"], *[convert.slugify(p) for p in rel_parts]]
        ).strip("/")
        kind = "folder" if target["mimeType"] == convert.GOOGLE_FOLDER else "file"
        entry = self.manifest.add_curated(target["id"], kind, dest, "shortcut", target["name"])
        self.walk_curated(entry)

    def walk_curated(self, curated: dict) -> None:
        """Import completo de una entrada curada (§3.8): archivo o carpeta recursiva."""
        try:
            if curated["kind"] == "file":
                meta = self.drive.get_meta(curated["drive_id"])
                self.handle_meta(meta, curated, ())
            else:
                for meta, rel in self.drive.iter_folder(curated["drive_id"]):
                    self.handle_meta(meta, curated, rel)
        except AccessError:
            self._record_error(
                {"id": curated["drive_id"], "name": curated.get("name")}, "acceso"
            )

    # ------------------------------------------------------------- espejo

    def mirror(self, meta: dict, curated: dict, rel_parts) -> None:
        fid = meta["id"]
        entry = self.manifest.files.get(fid)
        if entry and entry.get("estado") == "archivado":
            entry = None  # volvió a Drive: se re-espeja como nuevo (la copia archivada queda)
        # Skip por contenido (§3.8): renombres/movidas no re-exportan.
        if entry and not entry.get("pending_commit") and self._same_content(entry, meta):
            self._update_meta_only(entry, meta)
            return
        action = "actualizado" if entry and entry.get("path") else "nuevo"
        dest_dir = "/".join(
            [curated["dest"], *[convert.slugify(p) for p in rel_parts]]
        ).strip("/")
        mime = meta["mimeType"]
        try:
            if mime == convert.GOOGLE_DOC:
                path_rel, paths = self._mirror_doc(meta, entry, dest_dir)
            elif mime == convert.GOOGLE_SHEET:
                path_rel, paths = self._mirror_sheet(meta, entry, dest_dir)
            elif mime.startswith("application/vnd.google-apps."):
                self._record_error(meta, "formato-no-soportado")  # slides/forms: fase 1 no
                return
            else:
                path_rel, paths = self._mirror_binary(meta, entry, dest_dir)
        except ExportLimitError:
            self._record_error(meta, "export-limit")  # se menciona en el digest (§3.3)
            return
        except AccessError:
            self._record_error(meta, "acceso")  # PA-07
            return

        prev_pc = entry.get("pending_commit") if entry else None
        if prev_pc:
            if prev_pc.get("action") == "nuevo":
                action = "nuevo"
            paths = sorted(set(prev_pc.get("paths", [])) | set(paths))
        user = meta.get("lastModifyingUser") or {}
        new_entry = {
            "drive_id": fid,
            "name": meta["name"],
            "mime": mime,
            "path": path_rel,
            "root": curated["drive_id"],
            "modified_time": meta.get("modifiedTime"),
            "md5": meta.get("md5Checksum"),
            "version": meta.get("version"),
            "modified_by": {
                "name": user.get("displayName"),
                "email": user.get("emailAddress"),
            },
            "drive_url": meta.get("webViewLink"),
            "estado": "ok",
            "error": None,
            "pending_commit": {"action": action, "paths": list(paths)},
        }
        if entry and entry.get("last_commit"):
            new_entry["last_commit"] = entry["last_commit"]
        self.manifest.files[fid] = new_entry
        self.events.append(
            {
                "drive_id": fid,
                "action": action,
                "path": path_rel,
                "titulo": meta["name"],
                "autor": user.get("displayName"),
                "modificado": meta.get("modifiedTime"),
                "drive_url": meta.get("webViewLink"),
            }
        )

    def _same_content(self, entry: dict, meta: dict) -> bool:
        if meta.get("md5Checksum") or entry.get("md5"):
            return meta.get("md5Checksum") == entry.get("md5")
        return meta.get("modifiedTime") == entry.get("modified_time")

    def _update_meta_only(self, entry: dict, meta: dict) -> None:
        renamed = entry.get("name") != meta["name"]
        entry.update(
            {
                "name": meta["name"],
                "version": meta.get("version"),
                "drive_url": meta.get("webViewLink") or entry.get("drive_url"),
            }
        )
        if renamed:
            self.events.append(
                {
                    "drive_id": entry["drive_id"],
                    "action": "metadata",
                    "path": entry.get("path"),
                    "titulo": meta["name"],
                    "nota": "renombrado o movido en Drive; contenido sin cambios",
                }
            )

    # ---------------------------------------------------- espejo por tipo

    def _resolve_path(self, meta: dict, entry: dict | None, dest_dir: str) -> tuple[str, str]:
        """Ruta estable 1:1 (DD-11): una vez asignada, no cambia por renombres."""
        if entry and entry.get("path"):
            path_rel = entry["path"]
            return path_rel, Path(path_rel).stem
        slug = convert.slugify(meta["name"])
        candidate = f"{dest_dir}/{slug}.md" if dest_dir else f"{slug}.md"
        taken = {f.get("path") for f in self.manifest.files.values()}
        if candidate in taken or (self.root / candidate).exists():
            slug = f"{slug}-{meta['id'][:6].lower()}"
            candidate = f"{dest_dir}/{slug}.md" if dest_dir else f"{slug}.md"
        return candidate, slug

    def _frontmatter_for(self, meta: dict, path_rel: str) -> dict:
        abs_path = self.root / path_rel
        existing: dict = {}
        if abs_path.exists():
            existing, _ = convert.parse_frontmatter(abs_path.read_text(encoding="utf-8"))
        user = meta.get("lastModifyingUser") or {}
        parts = path_rel.replace("\\", "/").split("/")
        contexto = parts[0] if parts[0] in config.CONTEXTOS else None
        area = parts[1] if contexto and len(parts) >= 3 else None
        tipo = "otro"
        fresh = {
            "titulo": meta["name"],
            "drive_id": meta["id"],
            "drive_url": meta.get("webViewLink"),
            "modificado": meta.get("modifiedTime"),
            "modificado_por": user.get("displayName"),
            "contexto": contexto,
            "area": area,
            "tipo": tipo,
            "estado": "pendiente-validacion",  # hasta el OK de Daiana (RF-21)
            "importancia": config.importancia_default(path_rel, tipo, self.cfg),
            "related": [],
            "resumen": "",
        }
        return convert.merge_frontmatter(existing, fresh)

    def _write_md(self, path_rel: str, fm: dict, body: str) -> None:
        abs_path = self.root / path_rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        text = convert.dump_frontmatter(fm) + "\n" + body.lstrip("﻿").rstrip() + "\n"
        abs_path.write_text(text, encoding="utf-8", newline="\n")

    def _mirror_doc(self, meta: dict, entry: dict | None, dest_dir: str):
        body = self.drive.export_markdown(meta["id"])
        path_rel, slug = self._resolve_path(meta, entry, dest_dir)
        abs_dir = (self.root / path_rel).parent
        assets_rel = next(p for p in _sidecars(path_rel) if "_assets" in p)
        shutil.rmtree(self.root / assets_rel, ignore_errors=True)  # sin imágenes viejas
        body = convert.extract_images(body, abs_dir, slug)
        self._write_md(path_rel, self._frontmatter_for(meta, path_rel), body)
        return path_rel, [path_rel, assets_rel]

    def _mirror_sheet(self, meta: dict, entry: dict | None, dest_dir: str):
        data = self.drive.sheet_data(meta["id"])
        path_rel, slug = self._resolve_path(meta, entry, dest_dir)
        data_dir_rel = f"{path_rel[:-3]}.data"
        data_dir = self.root / data_dir_rel
        data_dir.mkdir(parents=True, exist_ok=True)
        hojas: dict[str, tuple[str, list[list]]] = {}
        used: dict[str, int] = {}
        current: set[str] = set()
        for title, rows in data.items():
            base = convert.slugify(title)
            n = used.get(base, 0) + 1
            used[base] = n
            csv_name = f"{base}.csv" if n == 1 else f"{base}-{n}.csv"
            current.add(csv_name)
            text = convert.rows_to_csv(rows)
            target = data_dir / csv_name
            previous = None
            if target.exists():
                with open(target, encoding="utf-8", newline="") as fh:
                    previous = fh.read()
            if previous != text:  # solo hojas cuyo contenido cambió (§3.8)
                target.write_text(text, encoding="utf-8", newline="")
            hojas[title] = (csv_name, rows)
        for old in data_dir.glob("*.csv"):
            if old.name not in current:
                old.unlink()  # hoja eliminada en Drive
        body = convert.sheet_ficha_body(meta["name"], slug, hojas)
        self._write_md(path_rel, self._frontmatter_for(meta, path_rel), body)
        return path_rel, [path_rel, data_dir_rel]

    def _mirror_binary(self, meta: dict, entry: dict | None, dest_dir: str):
        blob = self.drive.download(meta["id"])
        suffix = Path(meta["name"]).suffix or ".bin"
        tmp_dir = config.state_dir() / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp = tmp_dir / f"{meta['id']}{suffix}"
        tmp.write_bytes(blob)
        try:
            body = convert.markitdown_convert(tmp)
        finally:
            tmp.unlink(missing_ok=True)
        path_rel, _ = self._resolve_path(meta, entry, dest_dir)
        self._write_md(path_rel, self._frontmatter_for(meta, path_rel), body)
        return path_rel, [path_rel]

    # ------------------------------------------------------------- bajas

    def archive(self, entry: dict, motivo: str) -> None:
        """La baja archiva el espejo; el historial git no se borra (DD-18)."""
        old_rel = entry.get("path")
        if not old_rel:
            entry["estado"] = "archivado"
            return
        moves = [(old_rel, f"_meta/archivo/{old_rel}")]
        for sidecar in _sidecars(old_rel):
            moves.append((sidecar, f"_meta/archivo/{sidecar}"))
        paths: list[str] = []
        for src_rel, dst_rel in moves:
            src = self.root / src_rel
            if not src.exists():
                continue
            dst = self.root / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
            shutil.move(str(src), str(dst))
            paths += [src_rel, dst_rel]
        entry["estado"] = "archivado"
        entry["path_original"] = old_rel
        entry["path"] = f"_meta/archivo/{old_rel}"
        entry["pending_commit"] = {
            "action": "archivado",
            "paths": sorted(set(paths)),
            "motivo": motivo,
        }
        self.events.append(
            {
                "drive_id": entry["drive_id"],
                "action": "archivado",
                "path": entry["path"],
                "titulo": entry.get("name"),
                "nota": motivo,
            }
        )

    # ------------------------------------------------------------ errores

    def _record_error(self, meta: dict, code: str) -> None:
        fid = meta["id"]
        entry = self.manifest.files.get(fid) or {"drive_id": fid}
        entry["name"] = meta.get("name") or entry.get("name")
        entry["error"] = code
        entry["error_time"] = now_utc()
        self.manifest.files[fid] = entry
        self.events.append(
            {"drive_id": fid, "action": "error", "error": code, "titulo": entry.get("name")}
        )


# ---------------------------------------------------------------- commits

def commit_pending(root: Path, manifest: Manifest, drive_id: str, summary: str | None = None):
    """Commit de un pendiente. Mensaje según §3.4; genérico si no hay summary."""
    entry = manifest.files.get(drive_id)
    if not entry or not entry.get("pending_commit"):
        return None
    pc = entry["pending_commit"]
    slug = _slug_of(entry)
    who = (entry.get("modified_by") or {}).get("name") or "desconocido"
    if summary:
        first = summary.splitlines()[0].strip()
    else:
        generic = GENERIC_SUMMARIES.get(pc["action"], "sincronizado")
        sufijo = f" por {who}" if pc["action"] == "actualizado" and who != "desconocido" else ""
        first = f"sync({_area_of(entry.get('path'))}): {slug} — {generic}{sufijo}"
    lines = [
        first,
        "",
        f"Fuente: {entry.get('drive_url') or '—'}",
        f"Modificado en Drive: {entry.get('modified_time') or '—'} por {who}",
        f"Importancia: {_importancia_de(root, entry)}",
    ]
    sha = gitops.commit_paths(
        root,
        pc["paths"],
        "\n".join(lines),
        author_name=None if who == "desconocido" else who,
        author_email=(entry.get("modified_by") or {}).get("email"),
        author_date=entry.get("modified_time"),
    )
    entry.pop("pending_commit", None)
    if sha:
        entry["last_commit"] = sha
    return sha


def _commit_manifest(root: Path) -> None:
    """El estado del manifest queda versionado (RNF-05) en un commit propio."""
    gitops.commit_paths(root, ["_meta/manifest.json"], "chore(sync): estado del manifest")


def _pending_out(manifest: Manifest) -> list[dict]:
    out = []
    for entry in manifest.pending_commits():
        out.append(
            {
                "drive_id": entry["drive_id"],
                "path": entry.get("path"),
                "action": entry["pending_commit"]["action"],
                "titulo": entry.get("name"),
                "autor": (entry.get("modified_by") or {}).get("name"),
                "modificado": entry.get("modified_time"),
                "drive_url": entry.get("drive_url"),
            }
        )
    return out


# ---------------------------------------------------------------- comandos CLI

def _setup(require_manifest: bool = True):
    root = config.knowledge_root()
    if require_manifest and not config.manifest_path().exists():
        raise Abort(
            {"ok": False, "error": "No existe el manifest. Correr `python -m pipeline init` primero."}
        )
    gitops.assert_no_remote(root)  # guard-rail C-02, antes de todo
    manifest = Manifest.load(config.manifest_path())
    cfg = config.load_config()
    return root, manifest, cfg


def _commit_leftovers(root: Path, manifest: Manifest) -> list[dict]:
    """Pendientes de la corrida anterior → mensaje genérico (fallback §3.4)."""
    done = []
    for entry in list(manifest.pending_commits()):
        sha = commit_pending(root, manifest, entry["drive_id"])
        done.append({"drive_id": entry["drive_id"], "path": entry.get("path"), "commit": sha})
    return done


def cmd_init(args) -> dict:
    root = config.knowledge_root()
    template = config.ECOSYSTEM_ROOT / "templates" / "knowledge"
    creado = not (root / "INDEX.md").exists()
    if creado:
        shutil.copytree(template, root, dirs_exist_ok=True)
    gitops.init_repo(root)
    gitops.assert_no_remote(root)
    sha = gitops.commit_all(root, "chore: esqueleto inicial del repo conocimiento")
    creds = auth.get_credentials(interactive=not getattr(args, "no_browser", False))
    drive = Drive(creds)
    manifest = Manifest.load(config.manifest_path())
    if not manifest.page_token:
        manifest.page_token = drive.start_page_token()  # DD-01
    manifest.save()
    _commit_manifest(root)
    return {
        "ok": True,
        "knowledge_root": str(root),
        "esqueleto_creado": creado,
        "commit_inicial": sha,
        "oauth": "autorizado",
        "page_token": manifest.page_token,
    }


def cmd_run(args) -> dict:
    root, manifest, cfg = _setup()
    leftovers = _commit_leftovers(root, manifest)
    creds = auth.get_credentials(interactive=False)
    drive = Drive(creds)
    if not manifest.page_token:
        raise Abort({"ok": False, "error": "Manifest sin page_token. Correr `init`."})
    changes, new_token = drive.list_changes(manifest.page_token)
    engine = Sync(drive, manifest, cfg, root)
    for change in changes:
        engine.handle_change(change)
    manifest.page_token = new_token
    manifest.save()
    _commit_manifest(root)
    return {
        "ok": True,
        "cambios_en_drive": len(changes),
        "eventos": engine.events,
        "pendientes_de_commit": _pending_out(manifest),
        "commits_genericos_previos": leftovers,
    }


def cmd_import(args) -> dict:
    root, manifest, cfg = _setup()
    leftovers = _commit_leftovers(root, manifest)
    creds = auth.get_credentials(interactive=False)
    drive = Drive(creds)
    if not manifest.page_token:
        # Token ANTES de recorrer: los cambios durante el import no se pierden (§3.8).
        manifest.page_token = drive.start_page_token()
    engine = Sync(drive, manifest, cfg, root)
    only = getattr(args, "id", None)
    for curated in list(manifest.curated):
        if only and curated["drive_id"] != only:
            continue
        engine.walk_curated(curated)
    manifest.save()
    _commit_manifest(root)
    return {
        "ok": True,
        "eventos": engine.events,
        "pendientes_de_commit": _pending_out(manifest),
        "commits_genericos_previos": leftovers,
    }


def cmd_commit(args) -> dict:
    root, manifest, _ = _setup()
    results = []
    if getattr(args, "todos", False):
        for entry in list(manifest.pending_commits()):
            sha = commit_pending(root, manifest, entry["drive_id"])
            results.append({"drive_id": entry["drive_id"], "path": entry.get("path"), "commit": sha})
    else:
        if not args.drive_id:
            raise Abort({"ok": False, "error": "Falta drive_id (o usar --todos)."})
        sha = commit_pending(root, manifest, args.drive_id, getattr(args, "summary", None))
        results.append({"drive_id": args.drive_id, "commit": sha})
    manifest.save()
    return {"ok": True, "commits": results}


def cmd_status(args) -> dict:
    root = config.knowledge_root()
    manifest = Manifest.load(config.manifest_path())
    files = list(manifest.files.values())
    return {
        "ok": True,
        "knowledge_root": str(root),
        "page_token": manifest.page_token,
        "curados": len(manifest.curated),
        "archivos": len(files),
        "archivados": sum(1 for f in files if f.get("estado") == "archivado"),
        "errores": [
            {"drive_id": f["drive_id"], "titulo": f.get("name"), "error": f["error"]}
            for f in manifest.errores()
        ],
        "pendientes_de_commit": _pending_out(manifest),
    }
