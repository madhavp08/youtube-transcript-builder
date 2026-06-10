#!/usr/bin/env python3
"""Fetch a YouTube transcript from a video URL and save it as a local .txt file."""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


def extract_video_id(url: str) -> str:
    """Extract a YouTube video ID from common URL formats."""
    url = url.strip()

    if re.fullmatch(r"[\w-]{11}", url):
        return url

    parsed = urlparse(url)

    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.lstrip("/").split("/")[0]
        if video_id:
            return video_id

    if parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_ids = parse_qs(parsed.query).get("v", [])
            if video_ids:
                return video_ids[0]

        match = re.match(r"^/(embed|shorts|live)/([\w-]{11})", parsed.path)
        if match:
            return match.group(2)

    raise ValueError(f"Could not extract a video ID from: {url}")


def fetch_transcript(video_id: str, languages: list[str] | None = None):
    """Fetch the transcript snippets for a video."""
    api = YouTubeTranscriptApi()
    return api.fetch(video_id, languages=languages or ["en"])


def transcript_duration_seconds(fetched) -> float:
    """Total video time covered by the transcript, in seconds."""
    if len(fetched) == 0:
        return 0.0
    last = fetched[-1]
    return last.start + last.duration


def fetch_transcript_text(video_id: str, languages: list[str] | None = None) -> str:
    """Fetch transcript snippets and join them into plain text."""
    fetched = fetch_transcript(video_id, languages)
    return " ".join(snippet.text for snippet in fetched)


def save_transcript(text: str, output_path: Path) -> Path:
    """Write transcript text to a .txt file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def default_output_path(video_id: str, output_dir: Path) -> Path:
    return output_dir / f"{video_id}_raw.txt"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a YouTube transcript and save it as a local .txt file."
    )
    parser.add_argument("url", help="YouTube video URL or 11-character video ID")
    parser.add_argument(
        "-o",
        "--output",
        help="Output .txt file path (default: ~/Downloads/<video_id>_raw.txt)",
    )
    parser.add_argument(
        "-d",
        "--output-dir",
        default=str(Path.home() / "Downloads"),
        help="Directory for default output file (default: ~/Downloads)",
    )
    parser.add_argument(
        "-l",
        "--language",
        action="append",
        dest="languages",
        help="Preferred transcript language code(s), e.g. en, es (repeatable)",
    )
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = (
        Path(args.output)
        if args.output
        else default_output_path(video_id, Path(args.output_dir))
    )

    try:
        transcript = fetch_transcript_text(video_id, languages=args.languages)
    except TranscriptsDisabled:
        print(
            f"Error: Transcripts are disabled for video {video_id}.",
            file=sys.stderr,
        )
        return 1
    except NoTranscriptFound:
        print(
            f"Error: No transcript found for video {video_id} "
            f"in languages {args.languages or ['en']}.",
            file=sys.stderr,
        )
        return 1
    except VideoUnavailable:
        print(f"Error: Video {video_id} is unavailable.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error fetching transcript: {exc}", file=sys.stderr)
        return 1

    saved_path = save_transcript(transcript, output_path)
    print(f"Saved transcript to {saved_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
