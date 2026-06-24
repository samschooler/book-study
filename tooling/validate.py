#!/usr/bin/env python3
"""Validate an assembled book data file before deploy. Exits non-zero on problems.

Usage:  python3 tooling/validate.py <slug>

Catches the failure modes seen in practice: missing chapters, wrong question counts
(verify agents occasionally drop or duplicate items), malformed MCQs (not 4 options
or answer index out of range), and short-answers that aren't shaped right. Run it as
a gate in redeploy.sh so a degraded book never ships.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    partial = "--partial" in sys.argv  # skip completeness check (allows in-progress books)
    slug = args[0]
    cfg = json.load(open(os.path.join(ROOT, "tooling", "books", f"{slug}.json")))
    data = json.load(open(os.path.join(ROOT, "src", "data", "books", f"{slug}.json")))
    want_mcq = cfg.get("mcqPerChapter", 6)
    want_short = cfg.get("shortPerChapter", 2)
    total = data.get("totalChapters") or len(data["chapters"])

    problems = []
    nums = [c["chapter"] for c in data["chapters"]]
    if not partial:
        for n in range(1, total + 1):
            if n not in nums:
                problems.append(f"ch{n}: MISSING")
    if len(nums) != len(set(nums)):
        problems.append("duplicate chapter numbers")

    for c in data["chapters"]:
        ch, qs = c["chapter"], c.get("questions", [])
        if not c.get("summary", "").strip():
            problems.append(f"ch{ch}: empty summary")
        mcq = [q for q in qs if q["type"] == "mcq"]
        short = [q for q in qs if q["type"] == "short"]
        if len(mcq) != want_mcq or len(short) != want_short:
            problems.append(f"ch{ch}: counts {len(mcq)} mcq + {len(short)} short (want {want_mcq}+{want_short})")
        for k, q in enumerate(qs, 1):
            if q["type"] == "mcq":
                if len(q.get("options", [])) != 4:
                    problems.append(f"ch{ch} q{k}: mcq has {len(q.get('options', []))} options")
                if not (isinstance(q.get("answer"), int) and 0 <= q["answer"] < 4):
                    problems.append(f"ch{ch} q{k}: mcq answer index {q.get('answer')} out of range")
                if not q.get("explanation", "").strip():
                    problems.append(f"ch{ch} q{k}: mcq missing explanation")
            else:
                if q.get("options") != []:
                    problems.append(f"ch{ch} q{k}: short should have options=[]")
                if q.get("answer") != -1:
                    problems.append(f"ch{ch} q{k}: short should have answer=-1")
                if not q.get("modelAnswer", "").strip():
                    problems.append(f"ch{ch} q{k}: short missing modelAnswer")

    tq = sum(len(c.get("questions", [])) for c in data["chapters"])
    if problems:
        print(f"VALIDATION FAILED ({len(problems)} problems), {len(data['chapters'])}/{total} chapters, {tq} questions:")
        for p in problems[:40]:
            print("  -", p)
        sys.exit(1)
    print(f"VALID: {len(data['chapters'])}/{total} chapters, {tq} questions, all well-formed.")


if __name__ == "__main__":
    main()
