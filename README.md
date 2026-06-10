# YouTube Transcript Builder

Paste a YouTube link, get a clean, readable transcript. Free, no sign-up, no popups.

Works two ways: a **web page** anyone can use, or a **command line tool** on your own machine.

## How it works

1. You give it a YouTube link.
2. It downloads the video's captions (manual or auto-generated).
3. It cleans them up — removes noise like `[Music]`, fixes spacing, and splits the text into readable paragraphs.
4. You get a `.txt` file with the name you want.

Videos up to **10 hours** are supported. Nothing is stored on the server.

## Use the web page

The site is one input box. Paste a link, click **Get transcript**, then **Download .txt** or **Copy**.

### Deploy your own copy on Vercel (free)

1. Push this repo to GitHub (already done if you're reading this there).
2. Go to [vercel.com](https://vercel.com), sign in with GitHub, and click **Add New → Project**.
3. Pick this repo and click **Deploy**. No settings to change.

That's it — Vercel serves `index.html` and runs `api/transcript.py` automatically.

> **Heads up:** YouTube sometimes blocks requests coming from cloud servers (like Vercel's).
> If a video fails on the website but works on your machine, that's why — try the command line instead.

### Run the website locally

```bash
npm i -g vercel
vercel dev
```

Then open http://localhost:3000.

## Use the command line

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

## Files in this project

| File | What it does |
|---|---|
| `build-transcript.py` | The all-in-one command: fetch → clean → save |
| `fetch-transcript.py` | Downloads the raw transcript from YouTube |
| `clean-transcript.py` | Turns the raw text into readable paragraphs |
| `index.html` | The web page |
| `api/transcript.py` | The web page's backend (runs on Vercel) |
| `test_pipeline.py` | Tests — run with `python test_pipeline.py` |

## Troubleshooting

- **"Transcripts are disabled"** — the video owner turned captions off. Nothing can be done.
- **"No English transcript found"** — try `python fetch-transcript.py <link> -l <language-code>` for other languages.
- **"Video is X hours long"** — only videos up to 10 hours are supported.
