#!/usr/bin/env python3
"""Step 6: assemble src/data/books/<slug>.json from the config + reading guide +
spec + per-chapter quiz JSON. Re-runnable; safe to run on partial progress.

Usage:  python3 tooling/assemble.py <slug>

Inputs:
  tooling/books/<slug>.json              config (meta + parts)
  tooling/work/<slug>/guide.json         reading guide  { tagline, sections }
  tooling/work/<slug>/spec.json          assessment spec (optional)
  tooling/work/<slug>/site-data/ch*.json per-chapter quizzes
Output:
  src/data/books/<slug>.json             -> drives the shelf + /<slug>/ page
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default


def main():
    slug = sys.argv[1]
    cfg = load(os.path.join(ROOT, "tooling", "books", f"{slug}.json"))
    work = os.path.join(ROOT, "tooling", "work", slug)
    guide = load(os.path.join(work, "guide.json"), {"tagline": "", "sections": []})
    spec = load(os.path.join(work, "spec.json"), {})

    chapters = []
    sd = os.path.join(work, "site-data")
    if os.path.isdir(sd):
        for fn in sorted(os.listdir(sd)):
            if fn.startswith("ch") and fn.endswith(".json"):
                c = load(os.path.join(sd, fn))
                if c and c.get("questions"):
                    chapters.append(c)
    chapters.sort(key=lambda c: c.get("chapter", 0))

    parts = cfg.get("parts") or [{"name": "One", "from": 1, "to": len(chapters)}]
    total = cfg.get("totalChapters") or (parts[-1]["to"] if parts else len(chapters))

    book = {
        "slug": cfg["slug"], "title": cfg["title"], "author": cfg["author"],
        "order": cfg.get("order", 99), "cover": f"/covers/{slug}.jpg",
        "blurb": cfg.get("blurb", "Reading guide + chapter quizzes"),
        "parts": parts, "totalChapters": total,
        "guide": guide, "spec": spec, "chapters": chapters,
    }

    outdir = os.path.join(ROOT, "src", "data", "books")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{slug}.json")
    json.dump(book, open(out, "w"), ensure_ascii=False, indent=1)
    tq = sum(len(c.get("questions", [])) for c in chapters)
    print(f"wrote src/data/books/{slug}.json: {len(chapters)}/{total} chapters, {tq} questions, "
          f"guide={'yes' if guide.get('sections') else 'no'}, spec={'yes' if spec else 'no'}")


if __name__ == "__main__":
    main()
