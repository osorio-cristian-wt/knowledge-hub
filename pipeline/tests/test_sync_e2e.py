"""E2E offline del motor de sync con un Drive falso: espejo → commit → update → baja."""

from pipeline import convert, gitops
from pipeline.manifest import Manifest
from pipeline.sync import Sync, commit_pending

DOC_META = {
    "id": "DOC1xxxxxxxxxxx",
    "name": "Manual de Políticas",
    "mimeType": convert.GOOGLE_DOC,
    "parents": ["FOLDER1xxxxxxxx"],
    "modifiedTime": "2026-07-08T14:32:00Z",
    "lastModifyingUser": {"displayName": "Nick R.", "emailAddress": "nick@example.com"},
    "webViewLink": "https://docs.google.com/document/d/DOC1xxxxxxxxxxx",
}

SHEET_META = {
    "id": "SHEET1xxxxxxxxx",
    "name": "Reporte Ventas",
    "mimeType": convert.GOOGLE_SHEET,
    "parents": ["FOLDER1xxxxxxxx"],
    "modifiedTime": "2026-07-08T15:00:00Z",
    "lastModifyingUser": {"displayName": "Nick R.", "emailAddress": "nick@example.com"},
    "webViewLink": "https://docs.google.com/spreadsheets/d/SHEET1xxxxxxxxx",
}


class FakeDrive:
    def __init__(self):
        self.doc_body = "# Manual\n\nContenido inicial."

    def iter_folder(self, folder_id):
        assert folder_id == "FOLDER1xxxxxxxx"
        yield dict(DOC_META), ()
        yield dict(SHEET_META), ()

    def get_meta(self, file_id):
        return {"DOC1xxxxxxxxxxx": dict(DOC_META), "SHEET1xxxxxxxxx": dict(SHEET_META)}[file_id]

    def export_markdown(self, file_id):
        return self.doc_body

    def sheet_data(self, spreadsheet_id):
        return {"daily": [["fecha", "total"], ["2026-07-08", 10]]}


def _setup(tmp_path):
    root = tmp_path / "knowledge"
    gitops.init_repo(root)
    manifest = Manifest.load(root / "_meta" / "manifest.json")
    curated = manifest.add_curated("FOLDER1xxxxxxxx", "folder", "cleanora/ventas", "chat", "Ventas")
    drive = FakeDrive()
    engine = Sync(drive, manifest, {}, root)
    return root, manifest, curated, drive, engine


def test_flujo_completo(tmp_path):
    root, manifest, curated, drive, engine = _setup(tmp_path)

    # --- import inicial -------------------------------------------------
    engine.walk_curated(curated)
    doc = manifest.files["DOC1xxxxxxxxxxx"]
    assert doc["path"] == "cleanora/ventas/manual-de-politicas.md"
    assert doc["pending_commit"]["action"] == "nuevo"
    text = (root / doc["path"]).read_text(encoding="utf-8")
    fm, body = convert.parse_frontmatter(text)
    assert fm["estado"] == "pendiente-validacion"
    assert fm["contexto"] == "cleanora" and fm["area"] == "ventas"
    assert "Contenido inicial" in body

    sheet = manifest.files["SHEET1xxxxxxxxx"]
    csv_path = root / "cleanora/ventas/reporte-ventas.data/daily.csv"
    assert csv_path.exists()
    assert "fecha,total" in csv_path.read_text(encoding="utf-8")

    # --- commit con resumen redactado por el agente -----------------------
    sha = commit_pending(root, manifest, "DOC1xxxxxxxxxxx", "sync(ventas): manual — alta inicial")
    assert sha and "pending_commit" not in manifest.files["DOC1xxxxxxxxxxx"]
    log = gitops.git(["log", "-1", "--format=%an|%s|%b"], root).stdout
    assert "Nick R." in log and "alta inicial" in log and "Fuente:" in log
    commit_pending(root, manifest, "SHEET1xxxxxxxxx")  # genérico

    # --- cambio sin re-export: mismo modifiedTime → solo metadata ----------
    engine.handle_meta(dict(DOC_META, name="Manual renombrado"))
    assert "pending_commit" not in manifest.files["DOC1xxxxxxxxxxx"]
    assert manifest.files["DOC1xxxxxxxxxxx"]["name"] == "Manual renombrado"

    # --- el agente escribe resumen; un update NO lo pisa ------------------
    fm, body = convert.parse_frontmatter((root / doc["path"]).read_text(encoding="utf-8"))
    fm["resumen"] = "Resumen escrito por Claw."
    fm["estado"] = "validado"
    (root / doc["path"]).write_text(
        convert.dump_frontmatter(fm) + "\n" + body, encoding="utf-8", newline="\n"
    )
    drive.doc_body = "# Manual\n\nContenido NUEVO."
    meta2 = dict(DOC_META, modifiedTime="2026-07-09T10:00:00Z")
    engine.handle_change({"fileId": DOC_META["id"], "file": meta2})
    doc = manifest.files["DOC1xxxxxxxxxxx"]
    assert doc["pending_commit"]["action"] == "actualizado"
    fm2, body2 = convert.parse_frontmatter((root / doc["path"]).read_text(encoding="utf-8"))
    assert fm2["resumen"] == "Resumen escrito por Claw."
    assert fm2["estado"] == "validado"
    assert fm2["modificado"] == "2026-07-09T10:00:00Z"
    assert "NUEVO" in body2
    sha2 = commit_pending(root, manifest, "DOC1xxxxxxxxxxx")
    assert "actualizado en Drive por Nick R." in gitops.git(
        ["log", "-1", "--format=%s"], root
    ).stdout

    # --- baja: se archiva, el historial queda ------------------------------
    engine.handle_change({"fileId": DOC_META["id"], "removed": True})
    doc = manifest.files["DOC1xxxxxxxxxxx"]
    assert doc["estado"] == "archivado"
    archived = root / "_meta/archivo/cleanora/ventas/manual-de-politicas.md"
    assert archived.exists()
    assert not (root / "cleanora/ventas/manual-de-politicas.md").exists()
    assert commit_pending(root, manifest, "DOC1xxxxxxxxxxx")

    # fuera de la selección curada → se descarta sin tocar nada
    engine.handle_change(
        {
            "fileId": "OTRO",
            "file": {
                "id": "OTRO",
                "name": "ajeno",
                "mimeType": convert.GOOGLE_DOC,
                "parents": [],
            },
        }
    )
    assert "OTRO" not in manifest.files
