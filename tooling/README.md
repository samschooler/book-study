# Book Study — generation tooling

Everything needed to add a new book to the shelf: fetch the ebook, generate a
reading guide, generate + verify a per-chapter comprehension quiz, and deploy.

The website itself is data-driven: drop a finished `src/data/books/<slug>.json`
into the repo and the bookshelf entry **and** the `/<slug>/` page generate
themselves (see `src/lib/books.js`). This tooling is the factory that produces
that JSON.

## Layout

```
tooling/
  books/<slug>.json        per-book config (you write this)
  prompts/reading_guide.md  prompt for the reading-guide subagent
  fetch_split.py           1. download EPUB from Library Genesis, split chapters, grab cover
  workflow/generate_quiz.js 2. Workflow script: research spec -> generate -> verify, per chapter
  extract_journal.py       3. rebuild per-chapter JSON from a workflow journal
  assemble.py              4. build src/data/books/<slug>.json from all the parts
  redeploy.sh              5. build + push + trigger Coolify deploy
  work/<slug>/             intermediate artifacts (chapters/, site-data/, guide.json, spec.json)
```

Steps 2 and the reading guide are **Claude-driven** (they call the Workflow / Agent
tools). Steps 1, 3, 4, 5 are plain scripts you can run directly.

## Add a new book — full recipe

1. **Write the config** `tooling/books/<slug>.json` (copy an existing one). Set
   `slug`, `title`, `author`, `order`, `searchQuery`, `mcqPerChapter`,
   `shortPerChapter`, and the `parts` array (chapter groupings shown on the page).

2. **Fetch + split**
   ```bash
   python3 tooling/fetch_split.py <slug>
   ```
   Downloads the EPUB, writes `tooling/work/<slug>/chapters/chNN.txt`, a
   `manifest.json`, and `public/covers/<slug>.jpg`. Open the manifest and sanity-
   check the chapter count/segmentation (some EPUBs need a tweak — see the script).

3. **Reading guide** (Claude): dispatch a subagent with
   `tooling/prompts/reading_guide.md` (swap in the book) and save its JSON to
   `tooling/work/<slug>/guide.json`.

4. **Generate + verify quizzes** (Claude): run the Workflow tool with
   `tooling/workflow/generate_quiz.js`, passing `args` built from the manifest:
   ```json
   { "title": "...", "chaptersDir": "<abs path to work/<slug>/chapters>",
     "chapters": [{ "n": 1, "part": 1 }, ...],
     "mcqPerChapter": 6, "shortPerChapter": 2 }
   ```
   It returns `{ spec, chapters }`. Save `spec` to `work/<slug>/spec.json`.

5. **Reconstruct chapters from the run journal** (robust against truncated
   returns; also lets you assemble partial progress):
   ```bash
   python3 tooling/extract_journal.py <slug> /path/to/workflows/<runId>/journal.jsonl
   ```
   Writes `work/<slug>/site-data/chNN.json`, preferring each chapter's *verify*
   result over its draft, and reports any chapter that is missing or draft-only.
   Regenerate those individually (see "Recovering a failed chapter") and drop the
   JSON into `site-data/` before assembling.

6. **Assemble the data file**
   ```bash
   python3 tooling/assemble.py <slug>
   ```
   Writes `src/data/books/<slug>.json`.

7. **Deploy**
   ```bash
   bash tooling/redeploy.sh "Add <title>"
   ```
   Builds the Astro site, pushes to GitHub, and triggers the Coolify deploy.

## Recovering a failed chapter

Generator agents occasionally return output that fails schema validation and die.
`extract_journal.py` reports these as missing/draft-only. Regenerate just that
chapter with a single Agent using the same spec and the chapter's `chNN.txt`,
have it write `work/<slug>/site-data/chNN.json`, then re-run `assemble.py`.

## Notes
- Concurrency in the Workflow runtime is capped at `min(16, cpu_cores - 2)`.
- The site is static; reader progress (unlocked chapters, answers, scores) lives
  in `localStorage`, keyed `book-study:<slug>:v1`.
