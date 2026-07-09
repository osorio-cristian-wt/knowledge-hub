---
name: analisis-ventas
description: Análisis en profundidad de ventas sobre los CSV del espejo — tendencias, comparativas por canal/lead source, diagnóstico de caídas. Usar cuando Daiana pregunte por números de ventas más allá de un dato puntual ("¿por qué cayeron las ventas?", "compará este mes con el anterior").
---

# Análisis de ventas (RF-27, ejemplo de RF-41)

## Método (obligatorio, RNF-03)

1. Entrar por el índice: `INDEX.md` → `cleanora/ventas/_index.md` → ficha del
   Sheet relevante (`<slug>.md`). La ficha lista hojas y columnas: leer eso,
   **no** los CSV.
2. Calcular con pandas sobre `cleanora/ventas/<slug>.data/*.csv`. Nunca leer un
   CSV entero en contexto ni hacer aritmética mental sobre tablas.
3. Si el diagnóstico cruza áreas (marketing, finanzas, reportes de gerencia),
   seguir los wikilinks `related` del frontmatter — de ahí sale "este número
   alimenta tal reporte".

## Diagnóstico típico ("se cayeron las ventas")

- Confirmar la caída: último período vs promedio previo (misma ventana que usa
  `pipeline check`, default 7 filas) y vs mismo período anterior si hay historia.
- Desglosar por dimensión disponible (canal, lead source, servicio, zona) y
  encontrar qué segmento explica la diferencia.
- Mirar si es dato o negocio: filas incompletas, día sin carga, cambio de
  formato de la hoja → decirlo explícitamente.
- Responder en 3-6 líneas: el hallazgo primero, el desglose después, y el
  documento fuente citado con wikilink + link a Drive.

## Entregables

Si Daiana pide el análisis "para mandar" o "en un documento": generarlo en
`entregables/AAAA-MM-DD-<tema>.md` (o el formato que pida), en el idioma que
pida esa vez (D-19), y avisarle dónde quedó. En fase 1 no se sube a Drive: lo
sube ella si corresponde.
