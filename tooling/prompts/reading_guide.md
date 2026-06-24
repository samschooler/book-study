# Reading-guide subagent prompt

Dispatch one Agent with the prompt below (replace `{{TITLE}}` / `{{AUTHOR}}` and
the audience line). Save the returned JSON to `tooling/work/<slug>/guide.json`.

The audience default is "a thoughtful adult reading on their own for general
intellectual development" — adjust per request.

---

Write a high-quality "how to read this book" reading guide for **{{TITLE}}** by
{{AUTHOR}}. The audience is {{AUDIENCE — e.g. a thoughtful 29-year-old reading on
their own for general intellectual development, NOT a student in a class}}. Tone:
intelligent, warm, direct, practical — like a brilliant friend orienting you
before a big read. Avoid academic jargon. Avoid spoilers of late plot beats
(naming a central, early-foregrounded concept is fine; revealing endings is not).

You may use web search to ground yourself in the book's structure, themes, and
reception, but write original prose.

Return ONLY a JSON object of this shape:

```json
{
  "tagline": "one evocative sentence under the 'Reading Guide' heading",
  "sections": [ { "title": "...", "body": "..." } ]
}
```

Aim for ~6 sections, roughly: (1) why this book now / what a reflective adult
gains; (2) how to read it — concrete active-reading habits specific to this book's
structure; (3) the one central idea to hold onto; (4) what to watch for — recurring
motifs/questions as a scannable list, plus a "cast to keep straight" mini-orientation
(one spoiler-light line per major character); (5) a reading cadence tied to the
book's parts, with the habit of taking the chapter quiz after each chapter to
consolidate; (6) how to read intelligently in general — transferable habits this
book is good for practicing.

Each `body` is plain text; separate paragraphs with `\n\n`; use a leading "• " for
list items. ~120–220 words per section. No markdown headers inside `body`.
