#!/usr/bin/env python3
"""Step 5: reconstruct per-chapter quiz JSON from a Workflow run journal.

Usage:  python3 tooling/extract_journal.py <slug> <path-to-journal.jsonl>

The journal records every agent() result. For each chapter the GENERATE result
lands first and the VERIFY result later; we keep the LAST occurrence so the
verified (corrected) version wins. Writes tooling/work/<slug>/site-data/chNN.json
and reports any chapter that is missing or only got a draft (no verify result) so
you can regenerate it individually before assembling.

It never deletes existing files, so an out-of-band fix dropped into site-data for
a chapter the journal lacks is preserved.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    slug, journal = sys.argv[1], sys.argv[2]
    out = os.path.join(ROOT, "tooling", "work", slug, "site-data")
    os.makedirs(out, exist_ok=True)

    counts, last = {}, {}
    spec = None
    for line in open(journal):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if o.get("type") != "result" or not isinstance(o.get("result"), dict):
            continue
        r = o["result"]
        if "philosophy" in r and "mcqPerChapter" in r:
            spec = r; continue
        ch = r.get("chapter")
        if ch is None or "questions" not in r:
            continue
        counts[ch] = counts.get(ch, 0) + 1
        last[ch] = r

    written, unverified = 0, []
    for ch, r in sorted(last.items()):
        json.dump(r, open(os.path.join(out, f"ch{ch:02d}.json"), "w"), ensure_ascii=False, indent=1)
        written += 1
        if counts[ch] < 2:
            unverified.append(ch)

    if spec:
        json.dump(spec, open(os.path.join(ROOT, "tooling", "work", slug, "spec.json"), "w"), ensure_ascii=False, indent=1)
        print("saved spec.json")
    present = {int(f[2:4]) for f in os.listdir(out) if f.startswith("ch") and f.endswith(".json")}
    hi = max(present) if present else 0
    missing = [c for c in range(1, hi + 1) if c not in present]
    print(f"wrote {written} chapters from journal -> {out}")
    print(f"unverified (draft only): {unverified}")
    print(f"available: {len(present)} chapters; gaps below ch{hi}: {missing}")


if __name__ == "__main__":
    main()
