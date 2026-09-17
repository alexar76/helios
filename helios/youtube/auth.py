"""YouTube OAuth and API client."""

from __future__ import annotations

import os
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_youtube(*, client_secret: Path, token_path: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if token_path.exists():
        # Use scopes stored in token.json (PromoMaterials tokens may omit readonly).
        creds = Credentials.from_authorized_user_file(str(token_path))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret.exists():
                raise FileNotFoundError(f"YouTube client secret not found: {client_secret}")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            oauth_port = int(os.environ.get("HELIOS_OAUTH_PORT", "8080"))
            creds = flow.run_local_server(
                port=oauth_port,
                redirect_uri_trailing_slash=False,
                open_browser=False,
            )
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def auth_only(*, client_secret: Path, token_path: Path) -> str:
    yt = get_youtube(client_secret=client_secret, token_path=token_path)
    ch = yt.channels().list(part="snippet", mine=True).execute()
    return ch["items"][0]["snippet"]["title"]
