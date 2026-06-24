#!/usr/bin/env python3
"""Step 1: download a book's EPUB from Library Genesis, extract the cover, and
split it into per-chapter text files.

Usage:  python3 tooling/fetch_split.py <slug>

Reads tooling/books/<slug>.json. Writes:
  tooling/work/<slug>/book.epub
  tooling/work/<slug>/chapters/chNN.txt   (one per chapter)
  tooling/work/<slug>/manifest.json
  public/covers/<slug>.jpg

Chapter segmentation: each EPUB spine HTML document with > MIN_WORDS of text is
treated as one chapter, numbered sequentially. Front-matter and part-divider
pages (which are tiny) are skipped. If a book paginates differently, adjust
MIN_WORDS or the spine handling below.

Requires: pip3 install --break-system-packages libgen-api-enhanced
"""
import json, os, re, sys, subprocess, zipfile
from html.parser import HTMLParser

MIN_WORDS = 250  # documents shorter than this are treated as front matter / dividers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_cfg(slug):
    return json.load(open(os.path.join(ROOT, "tooling", "books", f"{slug}.json")))


class TX(HTMLParser):
    def __init__(s):
        super().__init__(); s.t = []; s.skip = False
    def handle_starttag(s, tag, a):
        if tag in ("script", "style"): s.skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3"): s.t.append("\n")
    def handle_endtag(s, tag):
        if tag in ("script", "style"): s.skip = False
    def handle_data(s, d):
        if not s.skip: s.t.append(d)
    def text(s):
        out = re.sub(r"[ \t]+", " ", "".join(s.t))
        return re.sub(r"\n\s*\n+", "\n\n", out).strip()


def download_epub(cfg, dest):
    from libgen_api_enhanced import LibgenSearch
    s = LibgenSearch()
    results = []
    for _ in range(3):
        try:
            results = s.search_title(cfg["searchQuery"]); break
        except Exception as e:
            print("search retry:", e, file=sys.stderr)
    lang = cfg.get("language", "English")
    cands = [r for r in results if r.md5 and r.extension == "epub" and (r.language or "") == lang]
    cands.sort(key=lambda r: 0 if "Centennial" in (r.title or "") else 1)
    for r in cands:
        try:
            r.resolve_direct_download_link()
        except Exception as e:
            print("resolve fail:", e, file=sys.stderr); continue
        subprocess.run(["curl", "-s", "-L", "--max-time", "180",
                        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "-o", dest, r.resolved_download_link])
        if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
            ft = subprocess.run(["file", dest], capture_output=True, text=True).stdout
            if "EPUB" in ft.upper() or "Zip" in ft:
                print(f"downloaded: {r.title} ({r.size})"); return True
    return False


def main():
    slug = sys.argv[1]
    cfg = load_cfg(slug)
    work = os.path.join(ROOT, "tooling", "work", slug)
    chdir = os.path.join(work, "chapters")
    os.makedirs(chdir, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "public", "covers"), exist_ok=True)
    epub = os.path.join(work, "book.epub")

    if not (os.path.exists(epub) and os.path.getsize(epub) > 100_000):
        if not download_epub(cfg, epub):
            print("ERROR: could not download an EPUB; refine searchQuery", file=sys.stderr); sys.exit(1)

    z = zipfile.ZipFile(epub)
    # cover
    imgs = [n for n in z.namelist() if re.search(r"\.(jpe?g|png)$", n, re.I)]
    cover = next((n for n in imgs if "cover" in n.lower()), imgs[0] if imgs else None)
    if cover:
        ext = ".jpg"
        open(os.path.join(ROOT, "public", "covers", f"{slug}{ext}"), "wb").write(z.read(cover))
        print("cover ->", f"public/covers/{slug}{ext}")

    # chapters: spine HTML docs in reading order, skip the tiny ones
    htmls = [n for n in z.namelist() if n.endswith((".xhtml", ".html", ".htm"))]
    htmls.sort()
    manifest, n = [], 0
    for name in htmls:
        p = TX(); p.feed(z.read(name).decode("utf-8", "ignore"))
        txt = re.sub(r"^" + re.escape(cfg["title"]) + r"\s*", "", p.text())
        if len(txt.split()) < MIN_WORDS:
            continue
        n += 1
        open(os.path.join(chdir, f"ch{n:02d}.txt"), "w").write(txt)
        manifest.append({"chapter": n, "words": len(txt.split()), "src": name,
                         "opening": " ".join(txt.split()[:16])})
    # assign parts from config (or one part)
    parts = cfg.get("parts") or [{"name": "One", "from": 1, "to": n}]
    def part_of(c):
        for i, p in enumerate(parts, 1):
            if p["from"] <= c <= p["to"]:
                return i
        return 1
    for m in manifest:
        m["part"] = part_of(m["chapter"])
    json.dump({"slug": slug, "chapters": manifest}, open(os.path.join(work, "manifest.json"), "w"), indent=1)
    print(f"extracted {n} chapters -> {chdir}")
    print(f"manifest -> tooling/work/{slug}/manifest.json  (verify chapter count vs the real book!)")


if __name__ == "__main__":
    main()
