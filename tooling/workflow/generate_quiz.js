export const meta = {
  name: 'book-study-quiz',
  description: 'Research quiz design, then generate + verify per-chapter academic comprehension quizzes for a book',
  phases: [
    { title: 'Research', detail: 'best practices for academic comprehension quizzes' },
    { title: 'Generate', detail: 'one agent per chapter, reads chapter text + spec' },
    { title: 'Verify', detail: 'adversarial answer-key + distractor check per chapter' },
  ],
}

// Run via the Workflow tool. Pass args, e.g.:
//   { title: "East of Eden", chaptersDir: "/abs/.../work/east-of-eden/chapters",
//     chapters: [{ n: 1, part: 1 }, ...], mcqPerChapter: 6, shortPerChapter: 2 }
// Returns { spec, chapters }. Also reconstructable from the run journal via extract_journal.py.

const TITLE = args.title
const DIR = args.chaptersDir
const CHAPTERS = args.chapters
const MCQ = args.mcqPerChapter ?? 6
const SHORT = args.shortPerChapter ?? 2

const SPEC_SCHEMA = {
  type: 'object',
  required: ['philosophy', 'mcqPerChapter', 'shortPerChapter', 'bloomDistribution', 'mcqGuidelines', 'shortAnswerGuidelines', 'distractorRules', 'sources'],
  properties: {
    philosophy: { type: 'string' },
    mcqPerChapter: { type: 'integer' },
    shortPerChapter: { type: 'integer' },
    bloomDistribution: { type: 'string' },
    mcqGuidelines: { type: 'string' },
    shortAnswerGuidelines: { type: 'string' },
    distractorRules: { type: 'string' },
    sources: { type: 'array', items: { type: 'string' } },
  },
}

const CH_SCHEMA = {
  type: 'object',
  required: ['chapter', 'summary', 'questions'],
  properties: {
    chapter: { type: 'integer' },
    summary: { type: 'string' },
    questions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['type', 'bloom', 'difficulty', 'question', 'options', 'answer', 'modelAnswer', 'explanation'],
        properties: {
          type: { type: 'string', enum: ['mcq', 'short'] },
          bloom: { type: 'string' },
          difficulty: { type: 'string', enum: ['recall', 'comprehension', 'analysis', 'evaluation'] },
          question: { type: 'string' },
          options: { type: 'array', items: { type: 'string' } },
          answer: { type: 'integer' },
          modelAnswer: { type: 'string' },
          explanation: { type: 'string' },
        },
      },
    },
  },
}

phase('Research')
const spec = await agent(
  `You are an assessment-design expert. Research, using web search, the best way to build a RIGOROUS, ACADEMIC-LEVEL reading-comprehension quiz for a literary novel ("${TITLE}") used as a per-chapter FORMATIVE self-check that a reader takes immediately after finishing each chapter.

Investigate and synthesize current best practice on: Bloom's revised taxonomy and Barrett's reading-comprehension taxonomy applied to literature; the right mix of multiple-choice vs. constructed-response questions; high-quality MCQ distractor construction (plausible, parallel, single defensible key, no "all/none of the above"); literal vs. inferential vs. evaluative comprehension; how many questions per chapter avoid fatigue while ensuring coverage; and the testing effect / retrieval practice. Pull from authoritative sources.

Then commit to a CONCRETE spec the downstream writers follow. Use mcqPerChapter=${MCQ} and shortPerChapter=${SHORT}. Weight toward inferential/analytical questions over trivia. List the real sources you used.`,
  { schema: SPEC_SCHEMA, phase: 'Research' }
)
log(`Spec ready. Generating ${CHAPTERS.length} chapters (${MCQ} MCQ + ${SHORT} short each)...`)
const specText = JSON.stringify(spec, null, 1)

const results = await pipeline(
  CHAPTERS,
  (ch) => {
    const file = `${DIR}/ch${String(ch.n).padStart(2, '0')}.txt`
    return agent(
      `You are writing an academic-level reading-comprehension quiz for ONE chapter of "${TITLE}".

First READ the full chapter text at this path using the Read tool: ${file}
This is Chapter ${ch.n}.

Follow this assessment design spec exactly:
${specText}

Write exactly ${MCQ} multiple-choice and ${SHORT} short-answer questions for THIS chapter.
- Weight toward inference, theme, character psychology, symbolism, and narrative technique — not surface trivia.
- Every MCQ: exactly 4 options, one defensible correct answer ("answer" = its 0-based index), plausible parallel distractors, no "all/none of the above". modelAnswer="" for MCQ.
- Every short-answer: options=[], answer=-1, with a 3-5 sentence exemplar modelAnswer.
- Every question: a real Bloom level and an "explanation" grounded in specific events/quotes from THIS chapter.
- Also a 2-3 sentence "summary" of the chapter (shown only after the reader finishes it).
- Ground everything strictly in the chapter text you read; do not invent events.

Return the structured object for chapter ${ch.n}.`,
      { schema: CH_SCHEMA, label: `gen:ch${ch.n}`, phase: 'Generate' }
    )
  },
  (draft, ch) => {
    if (!draft) return null
    const file = `${DIR}/ch${String(ch.n).padStart(2, '0')}.txt`
    return agent(
      `You are an adversarial assessment QA reviewer for a quiz on Chapter ${ch.n} of "${TITLE}".

READ the chapter text at: ${file}

Draft quiz JSON:
${JSON.stringify(draft)}

Verify and CORRECT against the actual text:
- For each MCQ, confirm the keyed "answer" is the single best, textually-defensible choice; fix the index if wrong; rewrite any distractor that is also-correct, ambiguous, or implausible; ensure exactly 4 options.
- Confirm each explanation is accurate (no invented events); fix hallucinations.
- Confirm short-answer modelAnswers are accurate (options=[], answer=-1).
- Keep the same number of questions and the academic intent; sharpen weak items toward inference/analysis.

Return the corrected final structured object for chapter ${ch.n}.`,
      { schema: CH_SCHEMA, label: `verify:ch${ch.n}`, phase: 'Verify' }
    )
  }
)

const chapters = results.filter(Boolean).sort((a, b) => a.chapter - b.chapter)
const totalQ = chapters.reduce((s, c) => s + (c.questions ? c.questions.length : 0), 0)
log(`Done: ${chapters.length}/${CHAPTERS.length} chapters, ${totalQ} questions.`)
return { spec, chapters }
