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
python build-transcript.py "https://youtu.be/dQw4w9WgXcQ?si=0guRX3FO7wnBGPRN" "my-transcript.txt"
```

The cleaned transcript lands in your `Downloads` folder. Done.

## Other languages

English is the default. For another language, add `-l` with the language code:

```bash
python build-transcript.py "https://youtu.be/GpQSUjNsNm0" "hindi-transcript.txt" -l hi
```

Common codes: `hi` Hindi, `es` Spanish, `fr` French, `de` German, `ja` Japanese.
This only works if the video actually has captions in that language.

## Troubleshooting

- **"Transcripts are disabled"** — the video owner turned captions off. Nothing can be done.
- **"No transcript found"** — the video has no captions in that language. Try another `-l` code.
- **"Video is X hours long"** — only videos up to 10 hours are supported.
