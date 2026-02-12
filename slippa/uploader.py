"""
Uploader module — uploads clips to YouTube via the YouTube Data API v3.

How YouTube API Authentication Works:
    1. You create a Google Cloud project and enable YouTube Data API v3.
    2. You create OAuth2 credentials and download them as 'client_secrets.json'.
    3. First time: the user is redirected to Google login to grant permission.
    4. After login: a 'token.json' is saved so you don't need to login again.
    5. If the token expires, it auto-refreshes using the refresh token.

Prerequisites:
    1. Go to https://console.cloud.google.com
    2. Create a project (or select existing one)
    3. Enable "YouTube Data API v3"
    4. Go to Credentials → Create OAuth 2.0 Client ID (type: Desktop App)
    5. Download the JSON and save as 'client_secrets.json' in the Slippa root

Privacy: Uploads default to "private" so nothing goes public accidentally.
"""

import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
import googleapiclient.errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# YouTube API config
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# File paths for credentials
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"


def is_configured() -> bool:
    """
    Check if YouTube upload is configured (client_secrets.json exists).
    Returns True if the credentials file is present.
    """
    return os.path.exists(CLIENT_SECRETS_FILE)


def is_authenticated() -> bool:
    """
    Check if we already have a valid token (user has logged in before).
    """
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return creds and creds.valid
    except Exception:
        return False


def get_auth_url() -> str:
    """
    Generate the Google OAuth2 authorization URL.
    The user visits this URL to grant YouTube upload permission.

    Returns:
        str: The authorization URL to redirect the user to.
    """
    if not is_configured():
        raise FileNotFoundError(
            f"'{CLIENT_SECRETS_FILE}' not found. "
            "Download it from Google Cloud Console → Credentials → OAuth 2.0 Client IDs."
        )

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:5000/oauth/callback",
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",     # Get a refresh token
        include_granted_scopes="true",
        prompt="consent",
    )

    return auth_url


def handle_oauth_callback(authorization_response_url: str) -> bool:
    """
    Handle the OAuth2 callback after user grants permission.

    Args:
        authorization_response_url: The full callback URL with the auth code.

    Returns:
        bool: True if authentication succeeded.
    """
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:5000/oauth/callback",
    )

    flow.fetch_token(authorization_response=authorization_response_url)
    creds = flow.credentials

    # Save the token for future use
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    return True


def _get_youtube_service():
    """
    Build an authenticated YouTube API service.
    Uses saved token, refreshes if expired.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                "Not authenticated. Please log in via the web UI first."
            )

    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=creds
    )


def upload_video(
    file_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy_status: str = "private",
    category_id: str = "22",
) -> dict:
    """
    Upload a video to YouTube.

    Args:
        file_path: Path to the video file.
        title: Video title.
        description: Video description.
        tags: List of tags.
        privacy_status: 'private', 'public', or 'unlisted'.
        category_id: YouTube category ('22' = People & Blogs).

    Returns:
        dict: Upload result with 'id', 'title', 'status' keys.

    How it works:
        1. We build a request body with the video metadata
           (title, description, tags, privacy).
        2. We create a MediaFileUpload for the video file:
           - resumable=True: if upload is interrupted, it can continue.
           - chunksize=-1: upload the entire file in one request
             (simpler for small clips).
        3. We call youtube.videos().insert() to start the upload.
        4. We loop calling next_chunk() until the upload completes.
        5. YouTube returns the video ID on success.
    """
    youtube = _get_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or ["Slippa", "AI Clips", "Automated"],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media = googleapiclient.http.MediaFileUpload(
        file_path,
        chunksize=-1,
        resumable=True,
    )

    request_obj = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print(f"  Uploading '{title}' to YouTube...")

    response = None
    while response is None:
        status, response = request_obj.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"  Upload progress: {progress}%")

    video_id = response["id"]
    print(f"  ✅ Uploaded! Video ID: {video_id}")
    print(f"  🔗 https://www.youtube.com/watch?v={video_id}")

    return {
        "id": video_id,
        "title": title,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "status": privacy_status,
    }
