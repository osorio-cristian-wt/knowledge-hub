---
name: curaduria
description: Alta, baja y clasificación de la selección curada de Google Drive — cuando Daiana pega un link de Drive, pide seguir/dejar de seguir un documento o carpeta, o hay que configurar la carpeta Knowledge. También valida la clasificación de documentos nuevos.
---

# Curaduría de la selección (§3.7, DD-17/DD-18)

Comandos desde `C:\clawhub\ecosystem` con `.venv\Scripts\python.exe`. La fuente
de verdad es `_meta/manifest.json`; nunca editarlo a mano.

## Alta por link (Daiana pega una URL de Drive en el chat)

1. Decidir el destino en el esqueleto ANTES de agregar, si es evidente por el
   nombre/contexto de la conversación (ej. "este es el manual de operaciones" →
   `cleanora/operaciones`). Si no es evidente, usar el inbox y clasificar después.
2. `python -m pipeline add "<url>" --dest <contexto>/<area>` (omitir `--dest`
   para que caiga en `_meta/inbox`). Sirve para archivos sueltos Y carpetas;
   los atajos se resuelven solos al archivo real.
3. El comando espeja al toque. Con el resultado: leer el documento, completar
   frontmatter (`tipo`, `importancia`, `resumen`, `related`), commitear los
   pendientes con resumen (como en drive-sync paso 2) y agregar la fila al
   `_index.md` del área.
4. Confirmarle a Daiana en una línea: qué se agregó, dónde quedó y qué es.

Semántica de carpetas (DD-18): curar una carpeta = todo su contenido presente y
futuro, recursivo. Explicárselo a Daiana al dar de alta una carpeta.

## Carpeta `Knowledge` (alta sin hablar con el bot)

En el onboarding se crea una carpeta `Knowledge` en la raíz del Drive de Daiana
(la crea ella desde la UI de Google, guiada paso a paso). Registrarla con:

```
python -m pipeline add "<url de la carpeta>" --source knowledge-folder
```

Todo lo que ella suelte ahí (archivos o atajos, desde PC o celular) entra solo
en la corrida siguiente del sync, cae en `_meta/inbox` y se clasifica como
documento nuevo (drive-sync paso 3).

## Clasificación de documentos nuevos (RF-21)

Para cada archivo en `_meta/inbox` o marcado `estado: pendiente-validacion`:

1. Leer el documento (o su ficha), proponer ubicación:
   `python -m pipeline move <drive_id> <contexto>/<area>`.
2. Completar frontmatter y fila en `_index.md` marcada `⏳ pendiente de validación`.
3. Cuando Daiana confirme la ubicación ("sí, va en operaciones"), poner
   `estado: validado` en el frontmatter y quitar la marca ⏳.

## Baja ("dejá de seguir X")

```
python -m pipeline remove "<url o id>"
```

El espejo local se archiva en `_meta/archivo/` (el historial git no se borra) y
se quita la fila del `_index.md`. Confirmárselo a Daiana. Si pide dar de baja un
archivo suelto DENTRO de una carpeta curada, explicarle que se sigue la carpeta
entera: o se da de baja la carpeta, o ese archivo seguirá espejándose.

## Consultas

`python -m pipeline list` — qué se está siguiendo (para responder "¿qué documentos
tenés?" en lenguaje natural, agrupado por área).
