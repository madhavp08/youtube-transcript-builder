"""Vercel serverless function: GET /api/transcript?url=<youtube-link>

Returns JSON: {"video_id": "...", "transcript": "..."} or {"error": "..."}.
"""

import importlib.util
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
MAX_DURATION_HOURS = 10


def _load_module(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name, PROJECT_DIR / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_mod = _load_module("fetch_transcript", "fetch-transcript.py")
clean_mod = _load_module("clean_transcript", "clean-transcript.py")


def build_clean_transcript(url: str) -> dict:
    """Fetch and clean a transcript. Raises ValueError with a friendly message."""
    video_id = fetch_mod.extract_video_id(url)

    try:
        fetched = fetch_mod.fetch_transcript(video_id)
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError("No English transcript was found for this video.")
    except VideoUnavailable:
        raise ValueError("This video is unavailable (private, deleted, or restricted).")

    duration_hours = fetch_mod.transcript_duration_seconds(fetched) / 3600
    if duration_hours > MAX_DURATION_HOURS:
        raise ValueError(
            f"Video is {duration_hours:.1f} hours long; "
            f"only videos up to {MAX_DURATION_HOURS} hours are supported."
        )

    text = " ".join(snippet.text for snippet in fetched)
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

        if not url:
            self._send_json(400, {"error": "Missing 'url' query parameter."})
            return

        try:
            result = build_clean_transcript(url)
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
