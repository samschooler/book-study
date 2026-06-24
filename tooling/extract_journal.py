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

    # Collect every result per chapter in journal order. The generate result lands
    # first and the verify result later, BUT a verify agent can "succeed" while
    # returning an error object with an empty questions array (e.g. it failed to read
    # the chapter file). So we can't blindly take the last result — we take the last
    # result that actually HAS questions, falling back to the draft when verify came
    # back empty, and report those so they can be re-verified.
    per = {}  # ch -> list of results in order
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
        per.setdefault(ch, []).append(r)

    written, unverified, draft_fallback, empty = 0, [], [], []
    for ch, results in sorted(per.items()):
        good = [r for r in results if r.get("questions")]
        if not good:
            empty.append(ch)            # no usable result at all -> regenerate
            continue
        chosen = good[-1]               # last result that actually has questions
        json.dump(chosen, open(os.path.join(out, f"ch{ch:02d}.json"), "w"), ensure_ascii=False, indent=1)
        written += 1
        if len(results) < 2:
            unverified.append(ch)       # only ever got one result (no verify ran)
        elif chosen is not results[-1]:
            draft_fallback.append(ch)    # verify result was empty/errored -> using the draft

    if spec:
        json.dump(spec, open(os.path.join(ROOT, "tooling", "work", slug, "spec.json"), "w"), ensure_ascii=False, indent=1)
        print("saved spec.json")
    present = {int(f[2:4]) for f in os.listdir(out) if f.startswith("ch") and f.endswith(".json")}
    hi = max(present) if present else 0
    missing = [c for c in range(1, hi + 1) if c not in present]
    print(f"wrote {written} chapters from journal -> {out}")
    print(f"unverified (only one result, no verify ran): {unverified}")
    print(f"draft-fallback (verify came back empty -> using draft, re-verify these): {draft_fallback}")
    print(f"empty (no usable result -> regenerate): {empty}")
    print(f"available: {len(present)} chapters; gaps below ch{hi}: {missing}")


if __name__ == "__main__":
    main()
