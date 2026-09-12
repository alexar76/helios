"""YouTube resumable upload — ported from PromoMaterials upload_youtube.py."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any


def upload_video(youtube, video_path: Path, meta: dict[str, Any], channel: dict[str, Any], privacy: str) -> str:
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": (meta.get("description") or "").strip(),
            "tags": (meta.get("tags") or [])[:500],
            "categoryId": channel.get("default_category", "28"),
            "defaultLanguage": channel.get("default_language", "en"),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            _ = int(status.progress() * 100)
    return resp["id"]


def upload_captions(youtube, video_id: str, srt_path: Path, lang: str = "en") -> None:
    from googleapiclient.http import MediaFileUpload

    if not srt_path.exists():
        return
    body = {
        "snippet": {
            "videoId": video_id,
            "language": lang,
            "name": f"{lang} (auto)",
            "isDraft": False,
        }
    }
    media = MediaFileUpload(str(srt_path), mimetype="application/x-subrip")
    youtube.captions().insert(part="snippet", body=body, media_body=media).execute()


def publish_video(youtube, video_id: str, privacy: str = "public") -> None:
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": privacy, "embeddable": True}},
    ).execute()


def get_or_create_playlist(youtube, state: dict, key: str, pl_meta: dict) -> str:
    if key in state.get("playlists", {}):
        return state["playlists"][key]
    body = {
        "snippet": {"title": pl_meta["title"], "description": pl_meta.get("description", "")},
        "status": {"privacyStatus": "public"},
    }
    resp = youtube.playlists().insert(part="snippet,status", body=body).execute()
    pid = resp["id"]
    state.setdefault("playlists", {})[key] = pid
    return pid


def add_to_playlist(youtube, playlist_id: str, video_id: str, position: int) -> None:
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
            "position": position,
        }
    }
    youtube.playlistItems().insert(part="snippet", body=body).execute()


def upload_job(
    youtube,
    *,
    video_path: Path,
    srt_path: Path | None,
    youtube_meta: dict[str, Any],
    channel: dict[str, Any],
    state: dict[str, Any],
    playlists_meta: dict[str, Any] | None = None,
    privacy: str = "private",
    episode_key: str | None = None,
) -> str:
    vid = upload_video(youtube, video_path, youtube_meta, channel, privacy)
    if srt_path:
        time.sleep(2)
        upload_captions(youtube, vid, srt_path, channel.get("default_language", "en"))

    pl_key = youtube_meta.get("playlist")
    if pl_key and playlists_meta and pl_key in playlists_meta:
        pl_id = get_or_create_playlist(youtube, state, pl_key, playlists_meta[pl_key])
        pos = len([k for k in state.get("videos", {}) if k != episode_key])
        add_to_playlist(youtube, pl_id, vid, pos)

    if episode_key:
        state.setdefault("videos", {})[episode_key] = {
            "videoId": vid,
            "title": youtube_meta.get("title", ""),
            "privacy": privacy,
        }
    return vid
