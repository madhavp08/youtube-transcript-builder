#!/usr/bin/env python3
"""Offline tests for the transcript pipeline (no network required).

Run with: python test_pipeline.py
"""

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_mod = load_module("fetch_transcript", PROJECT_DIR / "fetch-transcript.py")
clean_mod = load_module("clean_transcript", PROJECT_DIR / "clean-transcript.py")
build_mod = load_module("build_transcript", PROJECT_DIR / "build-transcript.py")


class TestExtractVideoId(unittest.TestCase):
    def test_url_formats(self):
        cases = [
            "https://www.youtube.com/watch?v=zbMOQ5S5n4M",
            "https://youtube.com/watch?v=zbMOQ5S5n4M",
            "https://m.youtube.com/watch?v=zbMOQ5S5n4M&t=120",
            "https://youtu.be/zbMOQ5S5n4M",
            "https://youtu.be/zbMOQ5S5n4M?si=abc",
            "https://www.youtube.com/embed/zbMOQ5S5n4M",
            "https://www.youtube.com/shorts/zbMOQ5S5n4M",
            "https://www.youtube.com/live/zbMOQ5S5n4M",
            "zbMOQ5S5n4M",
        ]
        for url in cases:
            with self.subTest(url=url):
                self.assertEqual(fetch_mod.extract_video_id(url), "zbMOQ5S5n4M")

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            fetch_mod.extract_video_id("https://example.com/watch?v=zbMOQ5S5n4M")


class TestCleanText(unittest.TestCase):
    def test_removes_bracketed_noise(self):
        self.assertEqual(
            clean_mod.clean_text("Hello [Music] world [clears throat]."),
            "Hello world.",
        )

    def test_normalizes_newlines_and_spaces(self):
        raw = "Gates of Imagination presents Adventures\nof Huckleberry Finn.\n  Twice."
        self.assertEqual(
            clean_mod.clean_text(raw),
            "Gates of Imagination presents Adventures of Huckleberry Finn. Twice.",
        )


class TestUnpunctuatedTranscripts(unittest.TestCase):
    """Auto-generated captions have no punctuation; output must still be readable."""

    def test_long_unpunctuated_text_gets_paragraphs(self):
        words = ("word " * 50_000).strip()
        cleaned = clean_mod.clean_transcript(words)
        paragraphs = [p for p in cleaned.split("\n\n") if p]

        self.assertGreater(len(paragraphs), 100)
        for paragraph in paragraphs:
            self.assertLessEqual(
                len(paragraph.split()),
                clean_mod.MAX_WORDS_PER_PARAGRAPH
                + clean_mod.MAX_WORDS_PER_SENTENCE,
            )

    def test_chunk_words_keeps_short_sentences_intact(self):
        self.assertEqual(clean_mod.chunk_words("short sentence"), ["short sentence"])


class TestPunctuatedTranscripts(unittest.TestCase):
    def test_paragraph_word_cap(self):
        long_sentence = "This sentence has exactly these many words in it now. "
        cleaned = clean_mod.clean_transcript(long_sentence * 200)
        for paragraph in cleaned.split("\n\n"):
            if paragraph:
                self.assertLessEqual(len(paragraph.split()), 150)

    def test_demo_style_text(self):
        raw = (
            "Hi there, fellow investors. Welcome to my preview. "
            "Now, what are the most important things to look at? "
            "Let's start with revenue. It looks stable. "
        )
        cleaned = clean_mod.clean_transcript(raw)
        self.assertIn("\n\n", cleaned)
        self.assertTrue(cleaned.endswith("\n"))

    def test_empty_text(self):
        self.assertEqual(clean_mod.clean_transcript(""), "\n")


class TestNonEnglishTranscripts(unittest.TestCase):
    def test_zero_width_chars_removed(self):
        raw = "\u200b\u200bअब हम\u200b \u200bफँसे हुए हैं।\u200b"
        self.assertEqual(clean_mod.clean_text(raw), "अब हम फँसे हुए हैं।")

    def test_hindi_danda_splits_sentences(self):
        text = "अब हम फँसे हुए हैं। हमें शेल्टर बनाना होगा। कोई प्रेशर नहीं।"
        sentences = clean_mod.split_sentences(text)
        self.assertEqual(len(sentences), 3)

    def test_consecutive_duplicate_snippets_dropped(self):
        class Snippet:
            def __init__(self, text):
                self.text = text

        snippets = [Snippet("a"), Snippet("a"), Snippet("b"), Snippet("b"), Snippet("a")]
        self.assertEqual(fetch_mod.join_snippets(snippets), "a b a")


class TestBuildHelpers(unittest.TestCase):
    def test_normalize_output_name(self):
        self.assertEqual(build_mod.normalize_output_name("foo"), "foo.txt")
        self.assertEqual(build_mod.normalize_output_name("foo.txt"), "foo.txt")
        self.assertEqual(build_mod.normalize_output_name("../../evil"), "evil.txt")

    def test_output_dir_is_downloads(self):
        self.assertEqual(build_mod.TRANSCRIPTS_DIR, Path.home() / "Downloads")

    def test_duration_helper(self):
        class Snippet:
            def __init__(self, start, duration):
                self.start = start
                self.duration = duration

        snippets = [Snippet(0.0, 2.0), Snippet(35999.0, 5.0)]
        self.assertAlmostEqual(
            fetch_mod.transcript_duration_seconds(snippets), 36004.0
        )
        self.assertEqual(fetch_mod.transcript_duration_seconds([]), 0.0)


class TestPerformance(unittest.TestCase):
    def test_ten_hour_scale_transcript_cleans_quickly(self):
        import time

        # ~110k words mixing punctuated and unpunctuated runs (10h scale).
        block = ("Some sentence here. " * 20) + ("nopunct " * 200)
        text = block * 250

        start = time.monotonic()
        cleaned = clean_mod.clean_transcript(text)
        elapsed = time.monotonic() - start

        self.assertLess(elapsed, 10.0)
        self.assertGreater(cleaned.count("\n\n"), 500)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))
