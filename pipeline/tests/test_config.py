from pipeline.config import importancia_default

CFG = {
    "importancia": {
        "default": "normal",
        "por_tipo": {"politica": "critico"},
        "por_ruta": {"cleanora/ventas/*.data/*": "rutinario"},
    }
}


def test_por_ruta_gana():
    assert importancia_default("cleanora/ventas/reporte.data/daily.csv", "politica", CFG) == "rutinario"


def test_por_tipo():
    assert importancia_default("cleanora/operaciones/manual.md", "politica", CFG) == "critico"


def test_default():
    assert importancia_default("home-alliance/reportes/x.md", "otro", CFG) == "normal"
    assert importancia_default("x.md", None, {}) == "normal"
