# AI_USAGE — honest log of AI tool use

## Summary

AI tools were used to **author this system during the timed assignment**. No AI is
called when the system **runs** — answers at runtime come from deterministic code
(retrieval, date resolver, Decimal calculators). This satisfies the offline /
no-API-key requirement in the strongest form.

## What was used

| Tool | Used for |
|---|---|
| AI coding assistant (LLM, opencode) | Writing `policy_engine.py`, `ask.py`, `run_eval.py`, `eval.json`, and all documentation, under the human author's direction |

## Disclosed in detail

1. **Code authoring.** The LLM wrote the bulk of the code and docs in one timed
   session. The human author directed the architecture — notably the split the
   author insisted on: *BM25 retrieval surfaces candidate clauses; the date-aware
   resolver alone determines which rules are in force* — and reviewed outputs.
2. **PDF spec extraction.** The assignment PDF was text-extracted with a local
   Python snippet (zlib + ASCII85 decode) and read by the LLM to produce the task
   list; the spec requirements were not invented.
3. **Answer verification.** Expected answers for the eight spec questions and the
   15 eval questions were worked out from the source documents, then checked
   against engine output; mismatches were fixed in the engine (e.g. the
   within-24-hours boundary, KYC-negation parsing, pre-amendment cap text), never
   by faking outputs.
4. **Eval design.** The adversarial questions (stale FAQ rate, deleted-clause date
   shift, false premise on the ₹1,50,000 payment, missing KYC condition, pre-
   amendment date, out-of-scope CANNOT_ANSWER) were designed with LLM assistance
   and anchored to specific traps in the documents.

## What was NOT used

- No LLM, embedding API, or network call at runtime — `ask()` is deterministic.
- No cached model responses shipped as answers.
- No clause numbers anywhere in the code or answers that do not exist in the
  source documents.

## Verbatim disclosure line for reviewers

> All application code and documents in this repository were generated with LLM
> assistance under human direction during the 60-minute window (see git history).
> The running system contains no AI component: keyword retrieval (BM25), an
> explicit amendment table with effective dates, and Decimal arithmetic produce
> every answer. The author can explain every line and the reasoning behind each
> decision recorded in DECISIONS.md.
