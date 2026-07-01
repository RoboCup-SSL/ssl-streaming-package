"""Thin wrapper around the YouTube Data API v3 live endpoints.

Knows nothing about the match schedule or OBS — just auth, broadcasts, reusable
ingestion streams, and thumbnails. Callers (the schedule CLI, obs-controller)
supply already-formatted values.

Auth needs an OAuth 2.0 *Desktop app* client from the Google Cloud project that
owns the channel, with the YouTube Data API v3 enabled.
"""

from datetime import datetime, timezone
from pathlib import Path

# Create/manage broadcasts + streams + thumbnails.
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def _to_utc_z(dt: datetime) -> str:
    """Aware datetime -> RFC3339 'Z' string, as the API wants."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class YouTubeClient:
    def __init__(self, service):
        self._yt = service

    @classmethod
    def authenticate(cls, client_secret: Path, token: Path) -> "YouTubeClient":
        """Build a client, running the OAuth flow (and caching the token) if needed."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if token.exists():
            creds = Credentials.from_authorized_user_file(str(token), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not client_secret.exists():
                    raise FileNotFoundError(
                        f"OAuth client secret not found: {client_secret}. Create a "
                        "Desktop-app OAuth client in the channel's Google Cloud project "
                        "(YouTube Data API v3 enabled) and save it there."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
                creds = flow.run_local_server(port=0)
            token.write_text(creds.to_json())
        return cls(build("youtube", "v3", credentials=creds))

    def channel(self) -> dict:
        """The authenticated channel: {id, title} — used to confirm which account is in use."""
        resp = self._yt.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            raise RuntimeError("authenticated account has no YouTube channel")
        return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]}

    def list_broadcasts(self) -> list[dict]:
        """All upcoming/active/completed broadcasts on the channel, newest config last.

        Each item: {id, title, start (RFC3339 or None), privacy, status} — `status`
        is the lifecycle (created/ready/live/complete/…).
        """
        out: list[dict] = []
        page = None
        while True:
            resp = (
                self._yt.liveBroadcasts()
                .list(part="snippet,status", broadcastType="all", mine=True,
                      maxResults=50, pageToken=page)
                .execute()
            )
            for item in resp.get("items", []):
                out.append(
                    {
                        "id": item["id"],
                        "title": item["snippet"].get("title", ""),
                        "start": item["snippet"].get("scheduledStartTime"),
                        "privacy": item["status"].get("privacyStatus", ""),
                        "status": item["status"].get("lifeCycleStatus", ""),
                    }
                )
            page = resp.get("nextPageToken")
            if not page:
                return out

    def list_streams(self) -> list[dict]:
        """All ingestion streams the caller owns: {id, title, key}."""
        out: list[dict] = []
        page = None
        while True:
            resp = (
                self._yt.liveStreams()
                .list(part="id,snippet,cdn", mine=True, maxResults=50, pageToken=page)
                .execute()
            )
            for item in resp.get("items", []):
                out.append({
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "key": item["cdn"]["ingestionInfo"]["streamName"],
                })
            page = resp.get("nextPageToken")
            if not page:
                return out

    def create_stream(self, title: str) -> dict:
        """Create a reusable RTMP stream; returns {id, title, key}."""
        resp = (
            self._yt.liveStreams()
            .insert(
                part="snippet,cdn,contentDetails",
                body={
                    "snippet": {"title": title},
                    "cdn": {
                        "frameRate": "variable",
                        "ingestionType": "rtmp",
                        "resolution": "variable",
                    },
                    "contentDetails": {"isReusable": True},
                },
            )
            .execute()
        )
        return {
            "id": resp["id"],
            "title": title,
            "key": resp["cdn"]["ingestionInfo"]["streamName"],
        }

    def create_broadcast(self, *, title: str, description: str, start: datetime,
                         privacy: str, auto_start: bool, auto_stop: bool) -> str:
        resp = (
            self._yt.liveBroadcasts()
            .insert(
                part="snippet,status,contentDetails",
                body={
                    "snippet": {
                        "title": title[:100],  # YouTube title hard limit
                        "description": description,
                        "scheduledStartTime": _to_utc_z(start),
                    },
                    "status": {
                        "privacyStatus": privacy,
                        "selfDeclaredMadeForKids": False,
                    },
                    "contentDetails": {"enableAutoStart": auto_start,
                                       "enableAutoStop": auto_stop},
                },
            )
            .execute()
        )
        return resp["id"]

    def set_video_metadata(self, video_id: str, *, title: str, description: str,
                          tags: list[str], category_id: str) -> None:
        """Set tags (+ re-affirm title/description/category) on the broadcast's video.

        Tags live on the *video* resource, not the liveBroadcast snippet, so they
        need a separate videos.update. videos.update replaces the snippet, so title
        and categoryId (both required) and description are sent again to preserve them.
        """
        self._yt.videos().update(
            part="snippet",
            body={
                "id": video_id,
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id,
                },
            },
        ).execute()

    def find_playlist_id(self, title: str) -> str | None:
        """Id of the caller's playlist with this exact title, or None."""
        page = None
        while True:
            resp = (
                self._yt.playlists()
                .list(part="id,snippet", mine=True, maxResults=50, pageToken=page)
                .execute()
            )
            for item in resp.get("items", []):
                if item["snippet"]["title"] == title:
                    return item["id"]
            page = resp.get("nextPageToken")
            if not page:
                return None

    def add_to_playlist(self, playlist_id: str, video_id: str) -> None:
        self._yt.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()

    def bind(self, broadcast_id: str, stream_id: str) -> None:
        self._yt.liveBroadcasts().bind(
            id=broadcast_id, part="id,contentDetails", streamId=stream_id
        ).execute()

    def set_thumbnail(self, video_id: str, image: Path) -> None:
        self._yt.thumbnails().set(videoId=video_id, media_body=str(image)).execute()
