"""Cliente de Drive/Sheets: cambios, metadata, export y descargas (§3.2, §3.3, §3.8).

Sin push notifications (DD-01): todo es pull con changes.list + pageToken.
Backoff exponencial ante 403/429 (rate limits) en todas las llamadas.
"""

import io
import random
import time

FILE_FIELDS = (
    "id,name,mimeType,parents,trashed,version,md5Checksum,"
    "modifiedTime,lastModifyingUser(displayName,emailAddress),"
    "shortcutDetails,webViewLink"
)

RETRYABLE_STATUS = {429, 500, 502, 503}


class ExportLimitError(Exception):
    """El archivo supera el límite de 10 MB de files.export (§3.3)."""


class AccessError(Exception):
    """Se perdió (o nunca hubo) acceso al archivo (PA-07)."""


def _is_rate_limit(err) -> bool:
    text = str(err)
    return "ateLimit" in text or "quota" in text.lower()


def with_backoff(fn, retries: int = 6):
    from googleapiclient.errors import HttpError

    delay = 1.0
    for attempt in range(retries):
        try:
            return fn()
        except HttpError as err:
            status = err.resp.status if err.resp is not None else None
            retryable = status in RETRYABLE_STATUS or (status == 403 and _is_rate_limit(err))
            if not retryable or attempt == retries - 1:
                raise
            time.sleep(delay + random.random())
            delay = min(delay * 2, 64)


class Drive:
    def __init__(self, creds):
        from googleapiclient.discovery import build

        self.svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)

    # --- detección de cambios (§3.2) -------------------------------------

    def start_page_token(self) -> str:
        resp = with_backoff(
            lambda: self.svc.changes().getStartPageToken(supportsAllDrives=True).execute()
        )
        return resp["startPageToken"]

    def list_changes(self, page_token: str) -> tuple[list[dict], str]:
        """Todos los cambios desde page_token. Devuelve (changes, nuevo_token)."""
        changes: list[dict] = []
        token = page_token
        while token:
            resp = with_backoff(
                lambda t=token: self.svc.changes()
                .list(
                    pageToken=t,
                    pageSize=100,
                    includeRemoved=True,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    fields=(
                        "nextPageToken,newStartPageToken,"
                        f"changes(fileId,removed,file({FILE_FIELDS}))"
                    ),
                )
                .execute()
            )
            changes.extend(resp.get("changes", []))
            if "nextPageToken" in resp:
                token = resp["nextPageToken"]
            else:
                return changes, resp["newStartPageToken"]
        return changes, page_token

    # --- metadata ----------------------------------------------------------

    def get_meta(self, file_id: str) -> dict:
        from googleapiclient.errors import HttpError

        try:
            return with_backoff(
                lambda: self.svc.files()
                .get(fileId=file_id, fields=FILE_FIELDS, supportsAllDrives=True)
                .execute()
            )
        except HttpError as err:
            if err.resp is not None and err.resp.status in (403, 404):
                raise AccessError(f"Sin acceso al archivo {file_id}") from err
            raise

    # --- export y descargas (§3.3) ------------------------------------------

    def export_markdown(self, file_id: str) -> str:
        """Google Doc → markdown nativo de la API (límite 10 MB, DD-02)."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

        request = self.svc.files().export_media(fileId=file_id, mimeType="text/markdown")
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        try:
            done = False
            while not done:
                _, done = downloader.next_chunk()
        except HttpError as err:
            if "exportSizeLimitExceeded" in str(err):
                raise ExportLimitError(file_id) from err
            if err.resp is not None and err.resp.status in (403, 404):
                raise AccessError(f"Sin acceso al archivo {file_id}") from err
            raise
        return buf.getvalue().decode("utf-8")

    def download(self, file_id: str) -> bytes:
        """Binarios subidos (docx/xlsx/pdf) para el fallback markitdown."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

        request = self.svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        try:
            done = False
            while not done:
                _, done = downloader.next_chunk()
        except HttpError as err:
            if err.resp is not None and err.resp.status in (403, 404):
                raise AccessError(f"Sin acceso al archivo {file_id}") from err
            raise
        return buf.getvalue()

    def sheet_data(self, spreadsheet_id: str) -> dict[str, list[list]]:
        """Valores por hoja: {titulo: filas} — CSV por hoja, no tablas md (DD-14)."""
        from googleapiclient.errors import HttpError

        try:
            meta = with_backoff(
                lambda: self.sheets.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, fields="sheets(properties(title))")
                .execute()
            )
        except HttpError as err:
            if err.resp is not None and err.resp.status in (403, 404):
                raise AccessError(f"Sin acceso a la planilla {spreadsheet_id}") from err
            raise
        data: dict[str, list[list]] = {}
        for sheet in meta.get("sheets", []):
            title = sheet["properties"]["title"]
            resp = with_backoff(
                lambda t=title: self.sheets.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{t}'",
                    valueRenderOption="UNFORMATTED_VALUE",
                    dateTimeRenderOption="FORMATTED_STRING",
                )
                .execute()
            )
            data[title] = resp.get("values", [])
        return data

    # --- import inicial (§3.8) ------------------------------------------------

    def iter_folder(self, folder_id: str):
        """Recorrido recursivo de una carpeta curada, solo los fields necesarios.

        Rinde (meta, rel_parts) donde rel_parts es la ruta de subcarpetas
        (nombres de Drive) desde la carpeta curada hasta el padre del item.
        Las carpetas también se rinden, para poblar el cache de ancestros.
        """
        pending: list[tuple[str, tuple[str, ...]]] = [(folder_id, ())]
        while pending:
            current, rel = pending.pop()
            token = None
            while True:
                resp = with_backoff(
                    lambda t=token, c=current: self.svc.files()
                    .list(
                        q=f"'{c}' in parents and trashed=false",
                        pageSize=100,
                        pageToken=t,
                        fields=f"nextPageToken,files({FILE_FIELDS})",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for meta in resp.get("files", []):
                    if meta["mimeType"] == "application/vnd.google-apps.folder":
                        pending.append((meta["id"], rel + (meta["name"],)))
                    yield meta, rel
                token = resp.get("nextPageToken")
                if not token:
                    break
