---
name: actualizar-ecosistema
description: Chequea y aplica actualizaciones del ecosistema desde el repo público de GitHub (git pull + dependencias). Usar en el cron semanal en modo "avisar", o cuando Daiana confirme aplicar, o cuando Cristian avise que hay novedades.
---

# Actualización del ecosistema (RF-03, §10)

El ecosistema vive en `C:\clawhub\ecosystem` (clon del repo público). Las skills
están enlazadas por junction: el pull las actualiza solo.

## Modo "avisar" (cron semanal)

```
git -C C:\clawhub\ecosystem fetch
git -C C:\clawhub\ecosystem log --oneline HEAD..origin/main
```

- Sin novedades → no decir nada.
- Con novedades → resumirle a Daiana en 1-2 líneas qué mejoras hay (traducir
  los mensajes de commit a lenguaje simple) y preguntar si aplica. Solo se
  aplica con su OK.

## Aplicar (con OK de Daiana, o si lo pide directamente)

1. `git -C C:\clawhub\ecosystem pull --ff-only`
   - Si falla (cambios locales / no fast-forward): NO forzar ni descartar nada;
     avisar a Cristian con el error.
2. Si cambió `pipeline/requirements.txt`:
   `C:\clawhub\ecosystem\.venv\Scripts\python.exe -m pip install -r C:\clawhub\ecosystem\pipeline\requirements.txt`
3. Si el update trae `migrations/` con pasos nuevos (carpeta con instrucciones
   numeradas), seguirlos en orden.
4. Verificar que todo sigue vivo: `python -m pipeline status` (cwd ecosystem)
   debe devolver `ok: true`.
5. Confirmarle a Daiana en una línea que quedó actualizado.

Nunca tocar el repo conocimiento en este flujo; solo el ecosistema.
