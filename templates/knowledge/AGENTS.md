# AGENTS.md — Guía del consultor de conocimiento

Este repo es el espejo local del conocimiento de Cleanora / Home Alliance.
La fuente de verdad de los documentos es Google Drive; acá se consulta, no se edita.

## Regla de oro (anti-tokens)

**Nunca escanear el corpus.** Entrar siempre por [INDEX.md](INDEX.md) →
`_index.md` del área → documento. Si el documento es largo y su fila en el
`_index.md` lista un TOC, buscar el heading (grep) y leer solo esa sección.
Seguir wikilinks (`[[slug]]` o `[[area/slug]]`) solo cuando la consulta cruza áreas.

Presupuesto típico por consulta: INDEX (~150 tokens) + `_index.md` (~300) +
la sección objetivo. Nada más.

## Números

Siempre código sobre los CSV. Los datos de cada Sheet viven en
`<slug>.data/<hoja>.csv` junto a su ficha `<slug>.md` (la ficha describe hojas y
columnas). Ejecutar pandas para calcular; **nunca** aritmética mental sobre
tablas markdown ni leer CSVs completos en contexto.

## Escritura

- El espejo (`cleanora/`, `home-alliance/`) es de **solo lectura**, salvo:
  frontmatter (resumen, related, tipo, estado, importancia), los `_index.md`
  e `INDEX.md`. El cuerpo de los documentos jamás se toca (la fuente es Drive).
- Todo lo que Claw genera (reportes, presentaciones, análisis) va a
  [entregables/](entregables/), versionado en este mismo git.
- `_meta/manifest.json` lo mantiene el pipeline: no editarlo a mano.

## Historial

"¿Qué cambió esta semana en ventas?" se responde con `git log` / `git diff`
de este repo, traducido a lenguaje natural: fecha, autor y resumen. A Daiana
nunca se le muestra jerga git (RNF-02): para ella son "cambios con fecha y autor".

## Idioma

Chat con Daiana: español. Entregables: en el idioma que pida cada vez (D-19).
El corpus es bilingüe (español/inglés); citar en el idioma del original.

## Citas

Al responder, citar siempre el documento fuente con su wikilink o ruta
(y la URL de Drive del frontmatter si Daiana quiere abrir el original).
