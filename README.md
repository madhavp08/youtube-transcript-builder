# YouTube Transcript Builder

Give it a YouTube link, get a clean, readable transcript saved as a `.txt` file.

It downloads the video's captions (manual or auto-generated), removes noise like `[Music]`, fixes spacing, and splits everything into readable paragraphs. Videos up to **10 hours** are supported.

## How to use

One-time setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then just give it a link and the filename you want:

```bash
python build-transcript.py "https://www.youtube.com/watch?v=zbMOQ5S5n4M" "my-transcript.txt"
```

The cleaned transcript lands in the `transcripts/` folder. Done.

## Troubleshooting

- **"Transcripts are disabled"** — the video owner turned captions off. Nothing can be done.
- **"No English transcript found"** — try `python fetch-transcript.py <link> -l <language-code>` for other languages.
- **"Video is X hours long"** — only videos up to 10 hours are supported.
