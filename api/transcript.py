"""Vercel serverless function: GET /api/transcript?url=<youtube-link>

Returns JSON:
  200 -> {"video_id": "...", "transcript": "..."}
  4xx -> {"error": "...", "blocked": bool}

If WEBSHARE_PROXY_USERNAME / WEBSHARE_PROXY_PASSWORD env vars are set,
requests are routed through Webshare rotating residential proxies, which
avoids YouTube blocking cloud-server IPs.
"""

import importlib.util
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    PoTokenRequired,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import WebshareProxyConfig

PROJECT_DIR = Path(__file__).resolve().parent.parent
MAX_DURATION_HOURS = 10
FETCH_ATTEMPTS = 2

BLOCKED_MESSAGE = (
    "YouTube is currently blocking requests from this website's server "
    "(a known limitation of free hosting). You can run this tool on your "
    "own computer instead, or use another transcript site."
)


class BlockedError(Exception):
    pass


def _load_module(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name, PROJECT_DIR / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_mod = _load_module("fetch_transcript", "fetch-transcript.py")
clean_mod = _load_module("clean_transcript", "clean-transcript.py")


def _make_api() -> YouTubeTranscriptApi:
    username = os.environ.get("WEBSHARE_PROXY_USERNAME")
    password = os.environ.get("WEBSHARE_PROXY_PASSWORD")

    if username and password:
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=username,
                proxy_password=password,
            )
        )
    return YouTubeTranscriptApi()


def _fetch_with_retry(video_id: str, language: str):
    """Fetch the transcript, retrying once on transient failures."""
    last_exc = None
    for attempt in range(FETCH_ATTEMPTS):
        try:
            return _make_api().fetch(video_id, languages=[language])
        except (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
            AgeRestricted,
            InvalidVideoId,
        ):
            # Permanent conditions: retrying won't change the outcome.
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < FETCH_ATTEMPTS - 1:
                time.sleep(0.5)
    raise last_exc


def build_clean_transcript(url: str, language: str = "en") -> dict:
    """Fetch and clean a transcript. Raises ValueError/BlockedError."""
    video_id = fetch_mod.extract_video_id(url)

    try:
        fetched = _fetch_with_retry(video_id, language)
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError(
            f"No '{language}' transcript was found for this video. "
            "Try a different language."
        )
    except (VideoUnavailable, InvalidVideoId):
        raise ValueError("This video is unavailable (private, deleted, or restricted).")
    except AgeRestricted:
        raise ValueError("This video is age-restricted, so its captions can't be fetched.")
    except (RequestBlocked, IpBlocked, PoTokenRequired):
        raise BlockedError()

    duration_hours = fetch_mod.transcript_duration_seconds(fetched) / 3600
    if duration_hours > MAX_DURATION_HOURS:
        raise ValueError(
            f"Video is {duration_hours:.1f} hours long; "
            f"only videos up to {MAX_DURATION_HOURS} hours are supported."
        )

    text = fetch_mod.join_snippets(fetched)
    if not text.strip():
        raise ValueError("The transcript for this video is empty.")

    return {
        "video_id": video_id,
        "transcript": clean_mod.clean_transcript(text),
    }


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        url = (query.get("url") or [""])[0].strip()
        language = (query.get("lang") or ["en"])[0].strip() or "en"

        if not url:
            self._send_json(400, {"error": "Missing 'url' query parameter."})
            return

        if not re.fullmatch(r"[a-zA-Z]{2,3}(-[a-zA-Z]{2,4})?", language):
            self._send_json(400, {"error": f"Invalid language code: {language}"})
            return

        try:
            result = build_clean_transcript(url, language)
        except BlockedError:
            self._send_json(429, {"error": BLOCKED_MESSAGE, "blocked": True})
            return
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except Exception:
            self._send_json(
                502,
                {"error": "Could not fetch the transcript. Please try again."},
            )
            return

        self._send_json(200, result)
