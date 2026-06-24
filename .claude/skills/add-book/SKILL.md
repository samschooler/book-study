---
name: add-book
description: >-
  Add a new book to the Book Study site (book-study.sam.ink). Runs the full
  pipeline: fetch the ebook from Library Genesis, generate a reading guide, generate
  AND adversarially verify an academic per-chapter comprehension quiz, assemble the
  data file, and deploy via GitHub + Coolify. Use this WHENEVER working in the
  book-study repo and the user wants to add a book, build chapter quizzes, write a
  reading guide, regenerate a failed/missing chapter, re-assemble book data, or
  redeploy the site — even if they don't name the tooling scripts. Also the right
  skill for questions about how a book gets onto the shelf.
---

# Add a book to Book Study

This repo is a data-driven Astro static site. Each book is one file at
`src/data/books/<slug>.json`; dropping a finished one in makes the bookshelf entry
**and** the `/<slug>/` page generate themselves (see `src/lib/books.js`). Your job
is to produce that JSON and deploy. The factory lives in `tooling/`.

**Read `tooling/README.md` first** — it has the canonical recipe. This skill adds the
operational knowledge and the exact Claude-tool invocations the scripts can't do
themselves. Keep a todo list of the steps below; it's a long pipeline and easy to
drop a step.

## The pipeline

Steps 1, 5, 6, 7 are plain scripts. Steps 3–4 are **you** driving the Agent/Workflow
tools. Intermediates live in `tooling/work/<slug>/` (gitignored — see Copyright).

1. **Config** — write `tooling/books/<slug>.json` (copy `east-of-eden.json`). Set
   `slug`, `title`, `author`, `order`, `searchQuery`, `mcqPerChapter`,
   `shortPerChapter`, and the `parts` array. `searchQuery` is the Library Genesis
   title search; prefer title-only if a title+author query returns nothing.

2. **Fetch + split** — `python3 tooling/fetch_split.py <slug>`. Downloads the EPUB,
   extracts the cover to `public/covers/<slug>.jpg`, and splits chapters to
   `tooling/work/<slug>/chapters/chNN.txt`. **Open `manifest.json` and sanity-check
   the chapter count against the real book.** Segmentation skips docs under ~250
   words (front matter / part dividers); if a book paginates oddly, tune `MIN_WORDS`
   in the script or fix the manifest before continuing.

3. **Reading guide (Agent)** — dispatch one Agent with the prompt in
   `tooling/prompts/reading_guide.md` (fill in title/author/audience). It returns
   `{ tagline, sections }`. Save it verbatim to `tooling/work/<slug>/guide.json`.

4. **Generate + verify quizzes (Workflow)** — run the Workflow tool with
   `tooling/workflow/generate_quiz.js`. Build `args` from the manifest:
   ```json
   { "title": "<title>", "chaptersDir": "<ABS path to tooling/work/<slug>/chapters>",
     "chapters": [{ "n": 1, "part": 1 }, ...],
     "mcqPerChapter": 6, "shortPerChapter": 2 }
   ```
   It runs research → one generator per chapter → one adversarial verifier per
   chapter, and returns `{ spec, chapters }`. It runs in the background; you'll be
   notified on completion. Don't block on it — set up the deploy path meanwhile.

5. **Reconstruct from the journal** — `python3 tooling/extract_journal.py <slug>
   <journalPath>`. The journal (`…/workflows/<runId>/journal.jsonl`) holds full
   result payloads, so this is more robust than the tool's return value and lets you
   assemble partial progress. It keeps each chapter's **verify** result over its
   draft, saves `spec.json`, and reports any chapter that's missing or draft-only.

6. **Assemble** — `python3 tooling/assemble.py <slug>` → writes
   `src/data/books/<slug>.json`. Safe to run on partial progress (the page shows a
   "being prepared" state until chapters exist, and locks each chapter's quiz until
   the reader marks it finished).

7. **Validate** — `python3 tooling/validate.py <slug>` (strict: completeness +
   well-formedness). This is the gate; **always run it before claiming done.** Add
   `--partial` to allow an in-progress book (skips the missing-chapter check but
   still rejects malformed items). `redeploy.sh` runs `--partial` on every book
   automatically and aborts the deploy on failure.

8. **Deploy** — `bash tooling/redeploy.sh "<commit message>"`. Validates, builds,
   pushes to GitHub, triggers the Coolify deploy, and polls to completion.

## Things that will bite you (learned the hard way)

- **Agents fail in three sneaky ways the workflow accepts as "success":** (a) output
  missing `questions` → fails schema, retries, dies, pipeline drops the chapter
  (you end up at N-1); (b) a verify agent returns a schema-valid but EMPTY object
  ("couldn't read the text" — a flaky-read it should have retried) which then
  overwrites the good draft; (c) a verify agent returns the wrong COUNT (1, 9, 12
  questions instead of 8) or a malformed MCQ. `extract_journal.py` handles (a)/(b)
  (keeps the last result that actually has questions, and reports `empty` chapters);
  `validate.py` catches (c). **Trust neither the workflow's success status nor the
  chapter count alone — always run `validate.py`.** On the East of Eden run, 1
  chapter hit (a), 17 hit (b), and 8 hit (c) — 26 of 55 needed recovery.
- **Recover in batches** with a tiny parallel workflow: one self-contained agent per
  chapter that reads `chNN.txt` + the spec, generates EXACTLY 6 mcq + 2 short,
  self-verifies, and **writes its own `site-data/chNN.json`** (no schema arg, no
  return-value dependency — this is far more reliable than the two-stage pipeline for
  a known list of chapters). Then re-run `assemble.py` → `validate.py`. Inline the
  chapter list and paths as constants in the script; passing them via Workflow `args`
  did not bind reliably.
- **Workflow concurrency is capped** at `min(16, cpu_cores − 2)` by the runtime — not
  configurable. Verify agents queue behind generators; a 55-chapter book takes a
  while. That's expected, not a hang.
- **Coolify API base needs `/api/v1`.** `~/repo/skills/coolify-deploy/.env.coolify`'s
  `COOLIFY_API_URL` is just the host; append `/api/v1`. The book-study app uuid is
  baked into `redeploy.sh` (`y004o80kccw8w8sos0cog04c`); domain is `book-study.sam.ink`.
- **Continuous deploy:** you can run steps 5–7 repeatedly while the workflow is still
  running to push partial progress; the live URL never goes down.

## Copyright

`tooling/work/` and `*.epub` are gitignored — they hold the full book text. **Never
commit them.** Only the derivative quiz/guide JSON and the (small) cover thumbnail go
in the repo. Before any commit that touches book content, confirm no `work/`,
`*.epub`, or `chapters/*.txt` is staged.

## Verifying the result

The site is mobile-first; reader progress is `localStorage` keyed
`book-study:<slug>:v1`. When checking layout (especially the bookshelf) on mobile,
drive a real browser with proper **mobile viewport emulation** (the browser-harness
skill: `Emulation.setDeviceMetricsOverride` with `mobile:true, deviceScaleFactor:2`).
A raw headless `--window-size=390,844` does NOT emulate the mobile viewport and gives
false overflow/clipping. Check 390px and 320px.
