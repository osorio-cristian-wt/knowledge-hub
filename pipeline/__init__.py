"""Pipeline determinista del Knowledge Hub (ver docs/diseno.md §1 y §3).

Lo determinista va en estos módulos (descargar, convertir, commitear — barato,
testeable, sin tokens); lo que requiere criterio (clasificar, resumir, avisar)
vive en las skills de OpenClaw.
"""
