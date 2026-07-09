---
name: drive-sync
description: Sincroniza el espejo local con Google Drive y procesa los cambios — corre el pipeline, redacta los mensajes de commit, actualiza resúmenes e índices, clasifica importancia y avisa a Daiana. Usar en el cron diario de sync y cuando Daiana pida "actualizá la documentación".
---

# Sincronización Drive → conocimiento (§3.5 del diseño)

Rutas fijas: ecosistema `C:\clawhub\ecosystem`, conocimiento `C:\clawhub\knowledge`.
Python del pipeline: `C:\clawhub\ecosystem\.venv\Scripts\python.exe`, siempre con
cwd `C:\clawhub\ecosystem`. Todos los comandos devuelven JSON.

## Paso 1 — Correr el pipeline (determinista)

```
python -m pipeline run
```

Si `ok: false`:
- `guardrail: true` → alguien le puso remoto al repo conocimiento. NO seguir;
  explicarle a Daiana que la protección de privacidad frenó el sync y avisar a Cristian.
- error de credenciales → decirle a Daiana en lenguaje simple que hay que
  volver a autorizar Google y correr `python -m pipeline init` (abre el navegador).

## Paso 2 — Redactar y commitear (criterio, por cada pendiente)

Por cada elemento de `pendientes_de_commit`:

1. Ver el cambio: `git -C C:\clawhub\knowledge diff -- "<path>"` (si `action` es
   `nuevo`, leer el archivo directamente; si es un Sheet, mirar el diff de los CSV).
2. Redactar la primera línea del commit en los términos de Daiana, estilo:
   `sync(ventas): reporte-ventas — Nick actualizó los números del 8-jul`
3. `python -m pipeline commit <drive_id> --summary "<línea>"`

Si algo impide analizar un diff, saltearlo: la próxima corrida lo commitea con
mensaje genérico (el sync nunca se bloquea por esto).

## Paso 3 — Mantener el conocimiento (DD-07)

- Si el contenido cambió sustancialmente: actualizar `resumen` (y `related` si
  aparecieron referencias cruzadas) en el frontmatter, y la fila del documento en
  el `_index.md` del área (columnas: qué es, quién actualiza, último cambio).
- Documentos **nuevos** (RF-21): proponer ubicación en el esqueleto. Si el destino
  correcto no es donde cayó: `python -m pipeline move <drive_id> <contexto>/<area>`.
  Completar frontmatter (`tipo`, `importancia`, `resumen`), dejar `estado:
  pendiente-validacion` y agregar la fila en el `_index.md` marcada `⏳ pendiente
  de validación`. Se menciona en el próximo digest; no interrumpir a Daiana.
- Documentos largos: publicar su TOC (headings) en la columna "Qué es" del
  `_index.md` (`§TOC: precios, descuentos, reembolsos`) para lectura por sección.

## Paso 4 — Clasificar y avisar (§6, DD-09)

Leer `importancia` del frontmatter de cada documento cambiado:

- `critico` → avisar YA por Telegram.
- `rutinario` → nada ahora; entra al digest semanal.
- `normal` → juicio propio sobre el diff: ¿cambió una regla, un monto, una
  responsabilidad? → aviso inmediato; si no, al digest.

Formato del aviso: *qué documento, quién, cuándo, resumen del cambio en 2-3
líneas, ruta local y link al original en Drive*. Sin jerga git (RNF-02).

Si Daiana ajusta el criterio conversando ("los cambios de X avisámelos siempre"),
editar el frontmatter del documento o `_meta/config.yml` (sección `importancia`).

## Paso 5 — Datos

Correr `python -m pipeline check`; si hay hallazgos con `nivel: alerta`, seguir
la skill **alertas-datos**.

## Errores del manifest

Los `eventos` con `action: error` (`export-limit`, `acceso`, `formato-no-soportado`)
no se avisan al toque salvo que afecten un documento crítico: se mencionan en el
digest semanal (PA-07).

## Reglas

- Nunca editar el cuerpo de los `.md` espejados (solo frontmatter e índices).
- Los números se calculan con pandas sobre los CSV, jamás leyendo tablas.
- Con Daiana: español, cero conceptos técnicos.
