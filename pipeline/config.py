"""Rutas y configuración del sistema (diseño §2, §9).

Defaults pensados para la PC de Daiana (C:\\clawhub); overrideables por entorno
para desarrollo y tests: CLAWHUB_HOME, CLAWHUB_KNOWLEDGE, CLAWHUB_STATE.
"""

import os
from fnmatch import fnmatch
from pathlib import Path

ECOSYSTEM_ROOT = Path(__file__).resolve().parent.parent

CONTEXTOS = ("cleanora", "home-alliance")


def clawhub_home() -> Path:
    return Path(os.environ.get("CLAWHUB_HOME", r"C:\clawhub"))


def knowledge_root() -> Path:
    override = os.environ.get("CLAWHUB_KNOWLEDGE")
    return Path(override) if override else clawhub_home() / "knowledge"


def state_dir() -> Path:
    """Estado y credenciales, fuera de ambos repos (DD-15)."""
    override = os.environ.get("CLAWHUB_STATE")
    if override:
        path = Path(override)
    else:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(local) / "clawhub"
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest_path() -> Path:
    return knowledge_root() / "_meta" / "manifest.json"


def load_config() -> dict:
    """Lee _meta/config.yml del repo conocimiento (cadencias, importancia, alertas)."""
    import yaml

    path = knowledge_root() / "_meta" / "config.yml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def importancia_default(ruta_rel: str, tipo: str | None, cfg: dict) -> str:
    """Etapa 1 de la clasificación de cambios: default por carpeta/tipo (§6, DD-09)."""
    reglas = cfg.get("importancia") or {}
    ruta = str(ruta_rel).replace("\\", "/")
    for patron, valor in (reglas.get("por_ruta") or {}).items():
        if fnmatch(ruta, patron):
            return valor
    por_tipo = reglas.get("por_tipo") or {}
    if tipo and tipo in por_tipo:
        return por_tipo[tipo]
    return reglas.get("default", "normal")
