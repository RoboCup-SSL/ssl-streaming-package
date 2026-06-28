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

    def scheduled_start_times(self) -> set[str]:
        """RFC3339 start times of all upcoming/active broadcasts already on the channel."""
        taken: set[str] = set()
        page = None
        while True:
            resp = (
                self._yt.liveBroadcasts()
                .list(part="snippet", broadcastType="all", mine=True,
                      maxResults=50, pageToken=page)
                .execute()
            )
            for item in resp.get("items", []):
                t = item["snippet"].get("scheduledStartTime")
                if t:
                    taken.add(t)
            page = resp.get("nextPageToken")
            if not page:
                return taken

    def reusable_streams_by_title(self, titles: list[str]) -> dict[str, str]:
        """Map each wanted title -> existing reusable stream id (missing titles omitted)."""
        wanted = set(titles)
        found: dict[str, str] = {}
        page = None
        while True:
            resp = (
                self._yt.liveStreams()
                .list(part="id,snippet", mine=True, maxResults=50, pageToken=page)
                .execute()
            )
            for item in resp.get("items", []):
                title = item["snippet"]["title"]
                if title in wanted:
                    found[title] = item["id"]
            page = resp.get("nextPageToken")
            if not page:
                return found

    def create_reusable_stream(self, title: str) -> str:
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
        return resp["id"]

    def stream_key(self, stream_id: str) -> str:
        """RTMP ingestion key for a stream (what OBS needs in service.json)."""
        resp = self._yt.liveStreams().list(part="cdn", id=stream_id).execute()
        return resp["items"][0]["cdn"]["ingestionInfo"]["streamName"]

    def create_broadcast(self, *, title: str, description: str, start: datetime,
                         privacy: str) -> str:
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
                    "contentDetails": {"enableAutoStart": True, "enableAutoStop": True},
                },
            )
            .execute()
        )
        return resp["id"]

    def bind(self, broadcast_id: str, stream_id: str) -> None:
        self._yt.liveBroadcasts().bind(
            id=broadcast_id, part="id,contentDetails", streamId=stream_id
        ).execute()

    def set_thumbnail(self, video_id: str, image: Path) -> None:
        self._yt.thumbnails().set(videoId=video_id, media_body=str(image)).execute()
