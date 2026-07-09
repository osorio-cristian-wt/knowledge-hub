---
name: onboarding
description: Guía post-bootstrap de la instalación completa — Telegram, API key de Anthropic, OAuth de Drive, repo de conocimiento, selección curada inicial y primer sync. Usar una sola vez, cuando Daiana (o Cristian) pida "arrancá el onboarding" después de correr install.ps1.
---

# Onboarding conversacional (§10 del diseño, RF-01/RF-02)

Daiana no es técnica (RNF-02): cada paso que requiera acción suya se pide en
lenguaje simple, con instrucciones exactas, de a un paso por vez. Confirmar que
cada paso terminó bien antes de seguir. El proceso es reanudable: si algo queda
a medias, retomar desde el paso que falta.

Rutas: ecosistema `C:\clawhub\ecosystem`, conocimiento `C:\clawhub\knowledge`,
python `C:\clawhub\ecosystem\.venv\Scripts\python.exe` (cwd = ecosystem).

## Pasos

1. **Verificar base**: `git --version`, `python --version` (el venv existe),
   OpenClaw corriendo. Si falta algo, volver a correr `install.ps1`.

2. **Canal Telegram**: si este chat ya es Telegram, listo. Si no: guiarla con
   BotFather paso a paso (crear bot, pegar el token acá) y configurar el canal
   en OpenClaw.

3. **API key de Anthropic (RF-04)**: la cuenta es de Daiana (costos suyos).
   Guiarla: console.anthropic.com → crear cuenta → API keys → crear → pegar acá.
   Guardarla en la config de OpenClaw. Nunca en ninguno de los dos repos.

4. **Repo conocimiento + OAuth Drive (validación S-01 EN VIVO)**:
   `python -m pipeline init` — crea `C:\clawhub\knowledge` desde plantilla
   (git local SIN remoto) y abre el navegador para que Daiana autorice con su
   **cuenta corporativa**, permisos de solo lectura.
   - Si Google muestra "app sin verificar": indicarle "Configuración avanzada →
     ir a la app". Es esperado (DD-12).
   - Si el Workspace **bloquea** la autorización (S-01 falla): FRENAR el
     onboarding, avisar a Cristian — hay plan B (proyecto GCP propio de ella o
     export manual asistido), pero lo decide él.

5. **Selección curada inicial (PA-01)**: sesión guiada con Daiana. Recorrer
   juntas qué carpetas/archivos entran (ventas, operaciones, reportes de
   gerencia…). Por cada uno, ella pega el link y se sigue la skill **curaduria**.
   Crear también la carpeta `Knowledge` en su Drive (skill curaduria) para que
   pueda sumar cosas sin hablar con el bot.

6. **Primer sync completo**: `python -m pipeline import`. Puede tardar (backoff
   ante rate limits, corre desatendido): avisarle que puede dejarlo trabajando.

7. **Clasificación y resúmenes iniciales**: procesar los pendientes como en
   **drive-sync** pasos 2-3 (commits con resumen, frontmatter, `_index.md` de
   cada área, ubicaciones propuestas para lo que cayó en inbox).

8. **Validación del esqueleto (RF-21)**: mostrarle a Daiana el mapa (INDEX +
   áreas con qué quedó dónde) en lenguaje simple. Corregir lo que ella marque
   (`python -m pipeline move …`) y poner `estado: validado`.

9. **Cron jobs (DD-13)**: dar de alta en OpenClaw:
   - sync diario 07:00 (hora de Daiana) → skill **drive-sync**
   - digest semanal lunes 08:00 → skill **digest-semanal**
   - chequeo semanal de updates → skill **actualizar-ecosistema** (modo avisar)
   Las cadencias viven en `_meta/config.yml`; si Daiana pide otra ("sincronizá
   dos veces por día"), actualizar config y cron.

10. **Cierre**: explicarle en 5 líneas qué puede pedir desde ya (preguntas,
    reportes, "actualizá la documentación", pegar links de Drive) y que cada
    lunes le llega el resumen semanal.
