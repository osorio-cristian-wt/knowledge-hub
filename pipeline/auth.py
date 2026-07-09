"""OAuth 2.0 desktop flow (loopback) con scopes de solo lectura (§3.1, DD-12).

El client pertenece a un proyecto GCP de Cristian y viaja en el repo público
(para apps desktop el client-id no es secreto). El refresh token queda fuera
de ambos repos, en %LOCALAPPDATA%\\clawhub (DD-15).
"""

from pathlib import Path

from . import config

# Solo lectura: refuerza RF-15 por permiso, no solo por convención.
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

CLIENT_CONFIG_PATH = config.ECOSYSTEM_ROOT / "pipeline" / "oauth_client.json"


class AuthError(Exception):
    pass


def token_path() -> Path:
    return config.state_dir() / "drive-token.json"


def get_credentials(interactive: bool = True):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    tp = token_path()
    if tp.exists():
        creds = Credentials.from_authorized_user_file(str(tp), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save(creds)
            return creds
        except Exception:
            if not interactive:
                raise AuthError(
                    "El token de Drive expiró y no se pudo refrescar. "
                    "Hay que re-autorizar: correr `python -m pipeline init`."
                )
    if not interactive:
        raise AuthError(
            "No hay credenciales de Drive. Correr `python -m pipeline init` "
            "(abre el navegador para que Daiana autorice, validación S-01)."
        )

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_CONFIG_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    _save(creds)
    return creds


def _save(creds) -> None:
    tp = token_path()
    tp.write_text(creds.to_json(), encoding="utf-8")
