"""CLI del pipeline. Todos los comandos imprimen JSON (los consumen las skills).

Uso: python -m pipeline <comando> [args]   (desde C:\\clawhub\\ecosystem)
"""

import argparse
import json
import sys

from . import checks, curate, sync
from .gitops import GuardRailError
from .sync import Abort


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline",
        description="Pipeline determinista del Knowledge Hub (ver docs/diseno.md).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="crea el repo conocimiento, autoriza Drive y fija el pageToken")
    p.add_argument("--no-browser", action="store_true", help="falla si no hay token (sin flujo OAuth)")
    p.set_defaults(fn=sync.cmd_init)

    p = sub.add_parser("run", help="corrida de sync: cambios → espejo → pendientes de commit")
    p.set_defaults(fn=sync.cmd_run)

    p = sub.add_parser("import", help="import completo de la selección curada")
    p.add_argument("--id", help="solo esta entrada curada (drive_id)")
    p.set_defaults(fn=sync.cmd_import)

    p = sub.add_parser("commit", help="commit de pendientes (la skill pasa el resumen)")
    p.add_argument("drive_id", nargs="?", help="archivo pendiente a commitear")
    p.add_argument("--summary", help="primera línea del mensaje, redactada por Claw")
    p.add_argument("--todos", action="store_true", help="todos los pendientes, mensaje genérico")
    p.set_defaults(fn=sync.cmd_commit)

    p = sub.add_parser("add", help="alta curada (URL o id de Drive) + espejo inmediato")
    p.add_argument("url")
    p.add_argument("--dest", help="carpeta destino en el esqueleto (default _meta/inbox)")
    p.add_argument("--source", choices=["chat", "knowledge-folder", "onboarding"])
    p.set_defaults(fn=curate.cmd_add)

    p = sub.add_parser("remove", help="baja curada: archiva el espejo, conserva historial")
    p.add_argument("url")
    p.set_defaults(fn=curate.cmd_remove)

    p = sub.add_parser("move", help="reclasifica un documento en el esqueleto (RF-21)")
    p.add_argument("drive_id")
    p.add_argument("dest", help="nueva carpeta, ej. cleanora/operaciones")
    p.set_defaults(fn=curate.cmd_move)

    p = sub.add_parser("list", help="selección curada y archivos espejados")
    p.set_defaults(fn=curate.cmd_list)

    p = sub.add_parser("status", help="estado del manifest: errores, pendientes, conteos")
    p.set_defaults(fn=sync.cmd_status)

    p = sub.add_parser("check", help="alertas sobre los CSV según _meta/config.yml (RF-33)")
    p.set_defaults(fn=checks.cmd_check)

    return parser


def main(argv=None) -> int:
    # La consola de Windows suele ser cp1252: forzar UTF-8 para que títulos de
    # documentos (o el propio help) con caracteres fuera de cp1252 no revienten.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        out = args.fn(args)
    except Abort as err:
        print(json.dumps(err.payload, ensure_ascii=False))
        return 1
    except GuardRailError as err:
        print(json.dumps({"ok": False, "guardrail": True, "error": str(err)}, ensure_ascii=False))
        return 2
    except Exception as err:  # el JSON de error es el contrato con las skills
        print(json.dumps({"ok": False, "error": f"{type(err).__name__}: {err}"}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
