"""Alta, baja y reclasificación de la selección curada (§3.7, DD-17/DD-18).

La fuente de verdad es _meta/manifest.json. Dos vías de alta equivalentes:
link pegado por chat (espejo inmediato) y carpeta `Knowledge` en el Drive de
Daiana (los atajos se resuelven a su targetId en el sync).
"""

import re
import shutil
from pathlib import Path

from . import auth, config, convert
from .drive import AccessError, Drive
from .manifest import Manifest
from .sync import Abort, Sync, _commit_manifest, _pending_out, _setup

_DRIVE_URL_PATTERNS = [
    re.compile(r"/(?:document|spreadsheets|presentation|file)/d/([A-Za-z0-9_-]{10,})"),
    re.compile(r"/folders/([A-Za-z0-9_-]{10,})"),
    re.compile(r"[?&]id=([A-Za-z0-9_-]{10,})"),
]


def extract_drive_id(url_or_id: str) -> str | None:
    s = url_or_id.strip()
    for pattern in _DRIVE_URL_PATTERNS:
        match = pattern.search(s)
        if match:
            return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", s):
        return s
    return None


def _fail(msg: str):
    raise Abort({"ok": False, "error": msg})


def cmd_add(args) -> dict:
    root, manifest, cfg = _setup()
    fid = extract_drive_id(args.url)
    if not fid:
        _fail(f"No pude extraer un drive_id de: {args.url}")
    drive = Drive(auth.get_credentials(interactive=False))
    try:
        meta = drive.get_meta(fid)
    except AccessError:
        _fail("Sin acceso a ese archivo/carpeta de Drive (¿tiene permiso la cuenta de Daiana?).")
    if meta["mimeType"] == convert.GOOGLE_SHORTCUT:  # atajo → targetId real (DD-17)
        target_id = (meta.get("shortcutDetails") or {}).get("targetId")
        if not target_id:
            _fail("El atajo no tiene target resoluble.")
        meta = drive.get_meta(target_id)
    kind = "folder" if meta["mimeType"] == convert.GOOGLE_FOLDER else "file"
    dest = (getattr(args, "dest", None) or "_meta/inbox").strip("/").replace("\\", "/")
    entry = manifest.add_curated(
        meta["id"], kind, dest, getattr(args, "source", None) or "chat", meta["name"]
    )
    engine = Sync(drive, manifest, cfg, root)
    engine.walk_curated(entry)  # espejo al toque (DD-17)
    manifest.save()
    _commit_manifest(root)
    return {
        "ok": True,
        "curado": entry,
        "eventos": engine.events,
        "pendientes_de_commit": _pending_out(manifest),
    }


def cmd_remove(args) -> dict:
    """Baja: sale del manifest y el espejo se archiva; el historial git queda (DD-18)."""
    root, manifest, cfg = _setup()
    fid = extract_drive_id(args.url)
    if not fid:
        _fail(f"No pude extraer un drive_id de: {args.url}")
    entry = manifest.remove_curated(fid)
    engine = Sync(None, manifest, cfg, root)  # archivar no toca Drive
    afectados = [
        f
        for f in manifest.files.values()
        if (f.get("root") == fid or f.get("drive_id") == fid)
        and f.get("estado") != "archivado"
    ]
    if not entry and not afectados:
        _fail(
            "Ese id no está en la selección curada ni espejado. Si es un archivo dentro "
            "de una carpeta curada, la baja individual no existe: se daría de baja la carpeta."
        )
    for f in afectados:
        engine.archive(f, "dado de baja de la selección curada")
    manifest.save()
    _commit_manifest(root)
    return {
        "ok": True,
        "baja": entry,
        "archivados": [f.get("path") for f in afectados],
        "pendientes_de_commit": _pending_out(manifest),
    }


def cmd_move(args) -> dict:
    """Reclasificación en el esqueleto (RF-21): mueve md + sidecars y ajusta frontmatter."""
    root, manifest, _ = _setup()
    entry = manifest.files.get(args.drive_id)
    if not entry or not entry.get("path"):
        _fail(f"No hay archivo espejado con drive_id {args.drive_id}.")
    old_rel = entry["path"].replace("\\", "/")
    new_dest = args.dest.strip("/").replace("\\", "/")
    filename = Path(old_rel).name
    new_rel = f"{new_dest}/{filename}"
    if new_rel == old_rel:
        _fail("El destino es el mismo que la ubicación actual.")
    from .sync import _sidecars

    moves = [(old_rel, new_rel)]
    old_parent = str(Path(old_rel).parent).replace("\\", "/")
    for sidecar in _sidecars(old_rel):
        suffix = sidecar if old_parent == "." else sidecar[len(old_parent):].lstrip("/")
        moves.append((sidecar, f"{new_dest}/{suffix}"))
    paths: list[str] = []
    for src_rel, dst_rel in moves:
        src = root / src_rel
        if not src.exists():
            continue
        dst = root / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        paths += [src_rel, dst_rel]
    # contexto/area salen de la nueva ruta; el resto del frontmatter no se toca
    abs_new = root / new_rel
    if abs_new.suffix == ".md" and abs_new.exists():
        fm, body = convert.parse_frontmatter(abs_new.read_text(encoding="utf-8"))
        parts = new_rel.split("/")
        fm["contexto"] = parts[0] if parts[0] in config.CONTEXTOS else None
        fm["area"] = parts[1] if fm["contexto"] and len(parts) >= 3 else None
        abs_new.write_text(
            convert.dump_frontmatter(fm) + "\n" + body.rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
    entry["path"] = new_rel
    entry["pending_commit"] = {"action": "reclasificado", "paths": sorted(set(paths))}
    curated = manifest.curated_by_id().get(args.drive_id)
    if curated and curated["kind"] == "file":
        curated["dest"] = new_dest
    manifest.save()
    _commit_manifest(root)
    return {"ok": True, "de": old_rel, "a": new_rel, "pendientes_de_commit": _pending_out(manifest)}


def cmd_list(args) -> dict:
    manifest = Manifest.load(config.manifest_path())
    return {
        "ok": True,
        "curados": manifest.curated,
        "archivos": [
            {
                "drive_id": f["drive_id"],
                "titulo": f.get("name"),
                "path": f.get("path"),
                "estado": f.get("estado"),
                "error": f.get("error"),
            }
            for f in manifest.files.values()
        ],
    }
