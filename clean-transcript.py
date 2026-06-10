#!/usr/bin/env python3
"""Clean a raw YouTube transcript into readable paragraphs and sections."""

import argparse
import re
import sys
from pathlib import Path

BRACKETED_NOISE = re.compile(r"\[[^\]]+\]")
WHITESPACE = re.compile(r"\s+")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")

SECTION_START = re.compile(
    r"^("
    r"Now[,.]|"
    r"And now\b|"
    r"Let's\b|"
    r"So[,.] what\b|"
    r"What are the\b|"
    r"What I\b|"
    r"What does\b|"
    r"Another reason\b|"
    r"I think less important\b|"
    r"And then of course\b|"
    r"Of course[,.] if\b"
    r")",
    re.IGNORECASE,
)

TOPIC_QUESTION = re.compile(
    r"^(what|how|why|when|where|let's)\b.*\?$",
    re.IGNORECASE,
)

MAX_SENTENCES_PER_PARAGRAPH = 5
MAX_WORDS_PER_PARAGRAPH = 110
# Auto-generated captions have no punctuation; chunk runaway "sentences" by words.
MAX_WORDS_PER_SENTENCE = 25


def clean_text(text: str) -> str:
    """Remove noise and normalize all whitespace (incl. newlines) in raw text."""
    text = BRACKETED_NOISE.sub("", text)
    text = WHITESPACE.sub(" ", text)
    text = SPACE_BEFORE_PUNCT.sub(r"\1", text)
    return text.strip()


def chunk_words(sentence: str, max_words: int = MAX_WORDS_PER_SENTENCE) -> list[str]:
    """Split an overly long (likely unpunctuated) sentence into word chunks."""
    words = sentence.split()
    if len(words) <= max_words:
        return [sentence]

    return [
        " ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)
    ]


def split_sentences(text: str) -> list[str]:
    """Split transcript text into sentences, chunking unpunctuated runs."""
    if not text:
        return []

    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(])', text)

    sentences: list[str] = []
    for part in parts:
        part = part.strip()
        if part:
            sentences.extend(chunk_words(part))
    return sentences


def starts_new_section(sentence: str, previous: str | None) -> bool:
    """Detect when a sentence should begin a new section or paragraph."""
    if SECTION_START.match(sentence):
        return True

    if previous and previous.endswith("?") and TOPIC_QUESTION.match(sentence):
        return True

    return False


def paragraphize(sentences: list[str]) -> list[str]:
    """Group sentences into readable paragraphs with section breaks."""
    if not sentences:
        return []

    paragraphs: list[str] = []
    current: list[str] = []
    current_words = 0
    previous: str | None = None

    for sentence in sentences:
        should_break = bool(current) and (
            len(current) >= MAX_SENTENCES_PER_PARAGRAPH
            or current_words >= MAX_WORDS_PER_PARAGRAPH
            or starts_new_section(sentence, previous)
        )

        if should_break:
            paragraphs.append(" ".join(current))
            current = []
            current_words = 0

        current.append(sentence)
        current_words += len(sentence.split())
        previous = sentence

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def format_transcript(paragraphs: list[str]) -> str:
    """Join paragraphs with blank lines for readability."""
    return "\n\n".join(paragraphs) + "\n"


def clean_transcript(text: str) -> str:
    """Run the full cleaning pipeline on raw transcript text."""
    cleaned = clean_text(text)
    sentences = split_sentences(cleaned)
    paragraphs = paragraphize(sentences)
    return format_transcript(paragraphs)


def resolve_output_path(output: str, output_dir: Path | None) -> Path:
    """Resolve user-provided output name to a full path."""
    output_path = Path(output)

    if output_path.is_absolute() or output_path.parent != Path("."):
        return output_path

    if output_dir is not None:
        return output_dir / output_path.name

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean a raw transcript .txt file into readable paragraphs."
    )
    parser.add_argument("input", help="Path to the raw transcript .txt file")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output filename or path for the cleaned transcript",
    )
    parser.add_argument(
        "-d",
        "--output-dir",
        type=Path,
        help="Directory for output when -o is only a filename (default: input file directory)",
    )
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="Keep the raw input file after cleaning (deleted by default)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    if output_dir is None and Path(args.output).parent == Path("."):
        output_dir = input_path.parent

    output_path = resolve_output_path(args.output, output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        raw_text = input_path.read_text(encoding="utf-8")
        cleaned_text = clean_transcript(raw_text)
        output_path.write_text(cleaned_text, encoding="utf-8")
    except OSError as exc:
        print(f"Error reading or writing files: {exc}", file=sys.stderr)
        return 1

    print(f"Saved cleaned transcript to {output_path.resolve()}")

    if not args.keep_raw:
        input_path.unlink()
        print(f"Deleted raw file {input_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
