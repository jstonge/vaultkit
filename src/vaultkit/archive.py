"""Fetch a source as markdown. Shells out to uvx, so there's nothing to install."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

IS_VIDEO = re.compile(r"youtube\.com|youtu\.be")

# Source kinds, matched in order; anything unrecognised is a plain blog post.
# "book" has no URL signature, so it has to be passed explicitly.
KINDS = [
    # host-anchored so docs.github.com stays docs
    ("repo", r"^https?://(?:www\.|gist\.)?(?:github|gitlab)\.com/"
             r"|^https?://(?:codeberg|bitbucket)\.org/"),
    ("video", r"youtube\.com|youtu\.be|vimeo\.com"),
    ("paper", r"arxiv\.org|biorxiv\.org|doi\.org|\.pdf(?:$|\?)"),
    ("course", r"/academy(?:/|$)|/courses?(?:/|$)|\.academy/"),
    ("docs", r"docs\.|/docs(?:/|$)|developer\.|/reference/"),
]
ALL_KINDS = [k for k, _ in KINDS] + ["post", "book"]


def infer_kind(url):
    for kind, pat in KINDS:
        if re.search(pat, url, re.I):
            return kind
    return "post"


def flatten_vtt(raw, every=90):
    """YouTube auto-captions repeat each line across cues; keep one copy and
    group the result into timestamped paragraphs."""
    recent, out, cur, start = [], [], [], None
    for block in raw.split("\n\n"):
        m = re.search(r"^(\d\d):(\d\d):(\d\d)\.\d+ -->", block, re.M)
        if not m:
            continue
        t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
        for line in block.split("\n")[1:]:
            line = re.sub(r"<[^>]+>", "", line).strip()
            if not line or line in recent:
                continue
            recent.append(line)
            del recent[:-6]
            start = t if start is None else start
            cur.append(line)
        if start is not None and t - start >= every:
            out.append(f"**[{start // 60:02d}:{start % 60:02d}]** " + " ".join(cur))
            cur, start = [], None
    if cur:
        out.append(f"**[{start // 60:02d}:{start % 60:02d}]** " + " ".join(cur))
    return "\n\n".join(out)


def fetch(url):
    """(markdown, how it was made), or (None, None) if it can't be retrieved."""
    if IS_VIDEO.search(url):
        with tempfile.TemporaryDirectory() as tmp:
            res = subprocess.run(
                ["uvx", "--quiet", "yt-dlp", "--write-auto-subs", "--write-subs",
                 "--sub-lang", "en.*", "--skip-download", "--sub-format", "vtt",
                 "-o", f"{tmp}/v.%(ext)s", url],
                capture_output=True, text=True)
            vtts = sorted(Path(tmp).glob("*.vtt"))
            if vtts:
                return (flatten_vtt(vtts[0].read_text(encoding="utf-8")),
                        "yt-dlp auto-captions; expect transcription errors")
    else:
        res = subprocess.run(
            ["uvx", "--quiet", "trafilatura", "-u", url, "--markdown", "--no-comments"],
            capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip(), "trafilatura article text"
    print(f"could not archive {url}: {res.stderr.strip()[:200]}", file=sys.stderr)
    return None, None
