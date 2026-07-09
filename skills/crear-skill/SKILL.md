---
name: crear-skill
description: Meta-skill — cuando Daiana repite el mismo tipo de pedido (3ª vez o más) o pide "automatizá esto", guiarla para encapsularlo como una skill propia reutilizable.
---

# Crear una skill propia (RF-40, RF-42)

## Cuándo proponerlo

Al detectar un patrón repetido (3ª vez el mismo tipo de pedido: mismo reporte,
misma comparación, mismo formato de entregable), ofrecer en una línea:
*"Esto ya lo pediste varias veces — ¿querés que lo deje armado para que salga
igual cada vez con solo pedirlo?"*. Si dice que no, no insistir.

## Dónde vive (RF-42)

- Con datos/criterios de la empresa (lo normal): repo **privado** →
  `C:\clawhub\knowledge\.claw\skills\<nombre>\SKILL.md`.
- Genérica y útil para cualquiera (sin datos de la empresa): proponérsela a
  Cristian para el catálogo del ecosistema; NO escribirla en el repo público
  desde esta PC.

## Cómo armarla

1. Reconstruir con Daiana el pedido en concreto: qué pregunta responde, de qué
   documentos/CSV sale, qué formato y qué idioma tiene la salida, cada cuánto
   lo necesita. Usar las últimas veces que lo pidió como ejemplos.
2. Escribir `SKILL.md` con este formato (frontmatter `name` + `description` con
   el disparador claro, cuerpo con pasos concretos):

```markdown
---
name: reporte-semanal-gerencia
description: Arma el reporte semanal de ventas para gerencia de Home Alliance. Usar cuando Daiana pida "el reporte de gerencia" o los viernes por recordatorio.
---

# Pasos
1. Fuentes: [[reporte-ventas]] (hojas daily y summary) …
2. Calcular con pandas: …
3. Formato de salida: … (en inglés, plantilla de gerencia)
4. Guardar en entregables/AAAA-MM-DD-reporte-gerencia.md y avisar.
```

3. Probarla en el momento con el último pedido real y mostrarle el resultado.
4. Si es recurrente en fecha fija, ofrecer recordatorio o cron (RF-32,
   `_meta/config.yml` → `recordatorios`).
5. Commitear la skill en el repo conocimiento (está versionada como todo lo demás).

## Recomendación de skills (RF-41)

Ante cualquier tarea que matchee una skill existente (del ecosistema o de las
suyas), proponerla por nombre en vez de improvisar el flujo a mano.
