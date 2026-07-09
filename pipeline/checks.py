"""Alertas sobre los datos tras cada sync (RF-33, §6).

Chequeos pandas simples sobre los CSV del espejo, definidos en _meta/config.yml
(clave `alertas`). Umbrales simples primero: ventas en cero, caída >X%, columna
sin datos. La interpretación y el aviso son de la skill alertas-datos.

Cada regla:
  - nombre: identificador
  - archivo: ruta o glob relativo al repo conocimiento
  - tipo: cero | caida | faltantes
  - columna: columna a chequear
  - umbral_pct: (caida) % de caída de la última fila vs el promedio previo
  - ventana: (caida) cuántas filas previas promediar (default 7)

Se asume que las filas se agregan en orden cronológico (reporte diario típico).
"""

from pathlib import Path

from . import config


def _findings_for(df, regla: dict) -> list[dict]:
    import pandas as pd

    col = regla.get("columna")
    nombre = regla.get("nombre", "sin-nombre")
    tipo = regla.get("tipo")
    if col not in df.columns:
        return [
            {
                "regla": nombre,
                "nivel": "config",
                "detalle": f"la columna '{col}' no existe (columnas: {', '.join(df.columns)})",
            }
        ]
    if df.empty:
        return []
    if tipo == "faltantes":
        ultimo = df[col].iloc[-1]
        if pd.isna(ultimo) or str(ultimo).strip() == "":
            return [
                {
                    "regla": nombre,
                    "nivel": "alerta",
                    "detalle": f"la última fila no tiene dato en '{col}'",
                }
            ]
        return []
    serie = pd.to_numeric(df[col], errors="coerce").dropna()
    if serie.empty:
        return []
    ultimo = serie.iloc[-1]
    if tipo == "cero":
        if ultimo == 0:
            return [
                {
                    "regla": nombre,
                    "nivel": "alerta",
                    "detalle": f"'{col}' está en cero en la última fila",
                }
            ]
        return []
    if tipo == "caida":
        ventana = int(regla.get("ventana", 7))
        previas = serie.iloc[:-1].tail(ventana)
        if len(previas) < 2 or previas.mean() == 0:
            return []
        caida_pct = (previas.mean() - ultimo) / previas.mean() * 100
        umbral = float(regla.get("umbral_pct", 30))
        if caida_pct > umbral:
            return [
                {
                    "regla": nombre,
                    "nivel": "alerta",
                    "detalle": (
                        f"'{col}' cayó {caida_pct:.0f}% contra el promedio de las "
                        f"últimas {len(previas)} filas ({previas.mean():.1f} → {ultimo})"
                    ),
                }
            ]
        return []
    return [{"regla": nombre, "nivel": "config", "detalle": f"tipo desconocido: {tipo}"}]


def run_checks(root: Path, cfg: dict) -> list[dict]:
    import pandas as pd

    findings: list[dict] = []
    for regla in cfg.get("alertas") or []:
        pattern = str(regla.get("archivo", "")).replace("\\", "/")
        matches = list(root.glob(pattern)) if pattern else []
        if not matches:
            findings.append(
                {
                    "regla": regla.get("nombre", "sin-nombre"),
                    "nivel": "config",
                    "detalle": f"no hay archivos que matcheen '{pattern}'",
                }
            )
            continue
        for csv_path in matches:
            try:
                df = pd.read_csv(csv_path)
            except Exception as err:
                findings.append(
                    {
                        "regla": regla.get("nombre", "sin-nombre"),
                        "nivel": "config",
                        "detalle": f"no pude leer {csv_path.name}: {err}",
                    }
                )
                continue
            for finding in _findings_for(df, regla):
                finding["archivo"] = str(csv_path.relative_to(root)).replace("\\", "/")
                findings.append(finding)
    return findings


def cmd_check(args) -> dict:
    root = config.knowledge_root()
    cfg = config.load_config()
    findings = run_checks(root, cfg)
    return {
        "ok": True,
        "reglas": len(cfg.get("alertas") or []),
        "hallazgos": findings,
    }
