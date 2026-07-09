---
name: digest-semanal
description: Resumen semanal de todo lo que cambió en la documentación, agrupado por área, con pendientes y errores. Usar en el cron de los lunes 08:00 o cuando Daiana pida "qué cambió esta semana".
---

# Digest semanal (RF-31, §3.6)

Insumos (cwd `C:\clawhub\ecosystem`, python del venv):

1. Commits de la semana:
   `git -C C:\clawhub\knowledge log --since="7 days ago" --date=short --pretty=format:"%ad|%an|%s"`
   Ignorar los `chore(sync): …`. El área sale del prefijo `sync(<area>): …`.
2. Estado del sistema: `python -m pipeline status` → errores (`export-limit`,
   `acceso`, `formato-no-soportado`) y pendientes.
3. Documentos aún `estado: pendiente-validacion` (grep en frontmatter del repo
   conocimiento) → sección "esperan tu OK".

## Formato del mensaje (Telegram, español, sin jerga git)

- Título: "Resumen de la semana — documentación".
- Una sección por área con cambios, cada uno en una línea: documento, quién,
  cuándo, qué cambió (usar la primera línea del commit; si es genérica, mirar
  el diff y redactar algo mejor).
- Sección "Documentos nuevos esperando tu OK" con la ubicación propuesta.
- Sección "Problemas" solo si hay: archivos sin acceso (¿pedís permiso?),
  documentos que superan el límite de export, formatos no soportados.
- Cierre de una línea: total de cambios y próximos recordatorios (RF-32,
  `_meta/config.yml` → `recordatorios`).

Si no hubo cambios: mensaje de una línea diciéndolo. Corto siempre: es un
resumen gerencial, no un log.
