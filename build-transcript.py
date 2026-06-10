#!/usr/bin/env python3
"""Fetch a YouTube transcript, clean it, and save it to the transcripts folder."""

import argparse
import importlib.util
import sys
from pathlib import Path

from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

TRANSCRIPTS_DIR = Path(__file__).resolve().parent / "transcripts"
MAX_DURATION_HOURS = 10


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_output_name(name: str) -> str:
    filename = Path(name).name
    if not filename.endswith(".txt"):
        filename = f"{filename}.txt"
    return filename


def build_transcript(
    url: str,
    output_name: str,
    languages: list[str] | None = None,
) -> Path:
    """Fetch, clean, delete raw, and return the final transcript path."""
    project_dir = Path(__file__).resolve().parent
    fetch_mod = load_module("fetch_transcript", project_dir / "fetch-transcript.py")
    clean_mod = load_module("clean_transcript", project_dir / "clean-transcript.py")

    video_id = fetch_mod.extract_video_id(url)
    raw_path = fetch_mod.default_output_path(video_id, TRANSCRIPTS_DIR)
    output_path = TRANSCRIPTS_DIR / normalize_output_name(output_name)

    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    fetched = fetch_mod.fetch_transcript(video_id, languages=languages)

    duration_hours = fetch_mod.transcript_duration_seconds(fetched) / 3600
    if duration_hours > MAX_DURATION_HOURS:
        raise ValueError(
            f"Video is {duration_hours:.1f} hours long; "
            f"only videos up to {MAX_DURATION_HOURS} hours are supported."
        )

    transcript = " ".join(snippet.text for snippet in fetched)
    if not transcript.strip():
        raise ValueError("Transcript is empty for this video.")

    fetch_mod.save_transcript(transcript, raw_path)

    cleaned_text = clean_mod.clean_transcript(transcript)
    output_path.write_text(cleaned_text, encoding="utf-8")

    raw_path.unlink()

    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a cleaned YouTube transcript from a URL. "
            "Provide only the link and desired output filename."
        )
    )
    parser.add_argument("url", help="YouTube video URL or 11-character video ID")
    parser.add_argument(
        "output",
        help="Final transcript filename, e.g. adobe-transcript-1.txt",
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
        output_path = build_transcript(args.url, args.output, languages=args.languages)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except TranscriptsDisabled:
        print("Error: Transcripts are disabled for this video.", file=sys.stderr)
        return 1
    except NoTranscriptFound:
        print(
            f"Error: No transcript found in languages {args.languages or ['en']}.",
            file=sys.stderr,
        )
        return 1
    except VideoUnavailable:
        print("Error: Video is unavailable.", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error reading or writing files: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error building transcript: {exc}", file=sys.stderr)
        return 1

    print(f"Saved cleaned transcript to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
