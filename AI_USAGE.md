# AI_USAGE — disclosure of AI tool use

## Summary

I used AI as a development tool while building this project, specifically the
**opencode** coding assistant, alongside normal engineering work (reading the
source documents, running the code, checking outputs). **No AI is called when the
system runs** — answers at runtime come from deterministic code (BM25 retrieval,
date-aware resolver, Decimal calculators). This satisfies the offline /
no-API-key requirement in the strongest form.

## How AI (opencode) was used

| Area | What I used it for |
|---|---|
| Scaffolding | Drafting the initial structure of `policy_engine.py`, `ask.py`, and `run_eval.py` |
| Spec extraction | Text-extracting the assignment PDF (local Python snippet, zlib + ASCII85) and turning it into a task list |
| Test design | Drafting adversarial eval questions (stale FAQ, deleted clause, false premises), each anchored to a specific trap in the documents |
| Docs | First drafts of this file, `DECISIONS.md`, and `WHERE_IT_BREAKS.md` |

## What I did myself / what the runtime does

- I reviewed every answer against the source documents and fixed the engine where
  it disagreed (e.g. the within-24-hours boundary, KYC-negation parsing,
  pre-amendment cap text) — never by faking eval outputs.
- I chose the architecture, including the split the reviewer asked for: BM25
  retrieval surfaces candidate clauses; the date-aware resolver alone determines
  which rules are in force.
- The running system contains no AI component. Keyword retrieval (BM25), an
  explicit amendment table with effective dates, and Decimal arithmetic produce
  every answer.

## What was NOT used

- No LLM, embedding API, or network call at runtime — `ask()` is deterministic.
- No cached model responses shipped as answers.
- No clause numbers anywhere in the code or answers that do not exist in the
  source documents.

## Disclosure line for reviewers

> I used AI (opencode) as a development tool while building this project during
> the timed assignment (see git history). The running system itself contains no
> AI component: keyword retrieval (BM25), an explicit amendment table with
> effective dates, and Decimal arithmetic produce every answer. **I can explain
> every line and the reasoning behind each decision recorded in DECISIONS.md.**
