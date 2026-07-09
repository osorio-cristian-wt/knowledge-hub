# Knowledge Hub — ecosistema OpenClaw para Cleanora

Repo **público** del ecosistema: instalador, pipeline de sincronización, skills y
plantillas. **Jamás contiene datos de la empresa** (C-02). El conocimiento vive en
un segundo repo git **local y sin remoto** en la PC de Daiana (`C:\clawhub\knowledge`).

- Análisis de requisitos: [docs/analisis-requisitos.md](docs/analisis-requisitos.md)
- Diseño técnico: [docs/diseno.md](docs/diseno.md)

## Instalación (PC de Daiana)

Un solo comando en PowerShell (RF-01):

```powershell
irm https://raw.githubusercontent.com/osorio-cristian-wt/knowledge-hub/main/install.ps1 | iex
```

Deja OpenClaw corriendo. Todo lo demás (Telegram, API key, OAuth de Drive,
selección curada, primer sync) lo guía Claw conversando — decirle al bot:
**"arrancá el onboarding"**.

Se le puede hablar a Claw por **Telegram** (principal, y por donde llegan los
avisos) o por **WebChat** en el navegador de la PC (`http://127.0.0.1:18789/`,
loopback con contraseña). Ambos corren sobre el mismo Gateway de OpenClaw.

## Layout del repo

| Ruta | Qué es |
|---|---|
| `install.ps1` | Bootstrap de un solo comando (RF-01, D-12) |
| `pipeline/` | Parte determinista: OAuth, `changes.list`, export, conversión, commits (§1 del diseño) |
| `skills/` | Skills de OpenClaw: onboarding, drive-sync, curaduría, digest, alertas… (§8) |
| `templates/knowledge/` | Esqueleto del repo conocimiento: índices, `AGENTS.md`, `config.yml` (§5) |
| `docs/` | Análisis y diseño |

## Pipeline (uso directo, desarrollo)

Todos los comandos devuelven JSON y se corren desde la raíz del repo:

```
python -m pipeline init                  # crea el repo conocimiento, OAuth, pageToken
python -m pipeline import               # import completo de la selección curada
python -m pipeline run                  # corrida de sync (cambios → espejo → pendientes)
python -m pipeline commit <id> --summary "…"   # commit de un pendiente con resumen
python -m pipeline commit --todos       # commit genérico de todos los pendientes
python -m pipeline add <url> [--dest …] # alta curada + espejo inmediato
python -m pipeline remove <url>         # baja: archiva el espejo, conserva historial
python -m pipeline move <id> <dest>     # reclasificación en el esqueleto (RF-21)
python -m pipeline list / status        # selección curada / estado del manifest
python -m pipeline check                # alertas sobre los CSV (RF-33)
```

Rutas overrideables por entorno (tests): `CLAWHUB_HOME`, `CLAWHUB_KNOWLEDGE`,
`CLAWHUB_STATE`.

## Desarrollo

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r pipeline\requirements.txt pytest
.venv\Scripts\python -m pytest pipeline\tests
```

Antes de publicar para uso real:

1. Reemplazar [pipeline/oauth_client.json](pipeline/oauth_client.json) con el client
   **desktop** real del proyecto GCP de Cristian (DD-12; el client-id de una app
   desktop no es secreto).
2. Validar S-01 con la cuenta corporativa real de Daiana (§12 del diseño, bloqueante).
