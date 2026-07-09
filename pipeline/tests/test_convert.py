"""Tests de la parte determinista de conversión (sin red ni APIs de Google)."""

from pipeline import convert

PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def test_slugify_basico():
    assert convert.slugify("Reporte de Ventas Á 2026") == "reporte-de-ventas-a-2026"
    assert convert.slugify("Manual de políticas.docx") == "manual-de-politicas"
    assert convert.slugify("   ") == "documento"
    assert convert.slugify("A" * 200).startswith("a")
    assert len(convert.slugify("A" * 200)) <= 60


def test_frontmatter_roundtrip():
    data = {
        "titulo": "Manual de políticas",
        "drive_id": "1AbC",
        "related": ["[[reporte-ventas]]"],
        "resumen": "Políticas operativas.",
    }
    text = convert.dump_frontmatter(data) + "\ncuerpo\n"
    parsed, body = convert.parse_frontmatter(text)
    assert parsed == data
    assert body.strip() == "cuerpo"


def test_frontmatter_sin_bloque():
    parsed, body = convert.parse_frontmatter("# solo cuerpo\n")
    assert parsed == {}
    assert body == "# solo cuerpo\n"


def test_merge_preserva_campos_del_agente():
    existing = {
        "resumen": "escrito por Claw",
        "estado": "validado",
        "importancia": "critico",
        "related": ["[[otro-doc]]"],
        "nota_extra": "custom",
        "modificado": "2026-01-01T00:00:00Z",
    }
    fresh = {
        "titulo": "Doc",
        "modificado": "2026-07-08T14:32:00Z",
        "estado": "pendiente-validacion",
        "importancia": "normal",
        "related": [],
        "resumen": "",
    }
    merged = convert.merge_frontmatter(existing, fresh)
    assert merged["resumen"] == "escrito por Claw"
    assert merged["estado"] == "validado"
    assert merged["importancia"] == "critico"
    assert merged["related"] == ["[[otro-doc]]"]
    assert merged["nota_extra"] == "custom"
    # la trazabilidad la pisa el pipeline
    assert merged["modificado"] == "2026-07-08T14:32:00Z"


def test_extract_images_inline_y_referencia(tmp_path):
    md = (
        f"Hola ![logo](data:image/png;base64,{PNG_B64}) mundo\n\n"
        "![][image1]\n\n"
        f"[image1]: <data:image/png;base64,{PNG_B64}>\n"
    )
    out = convert.extract_images(md, tmp_path, "doc")
    assert "base64" not in out
    assert "![logo](_assets/doc/img-1.png)" in out
    assert "[image1]: _assets/doc/img-2.png" in out
    assert (tmp_path / "_assets" / "doc" / "img-1.png").exists()
    assert (tmp_path / "_assets" / "doc" / "img-2.png").exists()


def test_rows_to_csv_normaliza_filas():
    csv_text = convert.rows_to_csv([["fecha", "total"], ["2026-07-08"], ["2026-07-09", 12, "extra"]])
    lines = csv_text.strip().split("\n")
    assert lines[0] == "fecha,total,"
    assert lines[1] == "2026-07-08,,"
    assert lines[2] == "2026-07-09,12,extra"


def test_sheet_ficha_body():
    body = convert.sheet_ficha_body(
        "Reporte Ventas",
        "reporte-ventas",
        {"daily": ("daily.csv", [["fecha", "total"], ["2026-07-08", 10]])},
    )
    assert "| daily | [daily.csv](reporte-ventas.data/daily.csv) | 1 | fecha, total |" in body
    assert "pandas" in body
