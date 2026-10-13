# AI_USAGE.md — honest log of AI tool use

**Yes, AI tools were used.** This is the disclosure the spec asks for.

## What was used

- **opencode** (AI coding agent, model `mimo-v2.6-flash-free`) — used
  interactively for the entire build session: reading the assignment PDF,
  drafting the policy engine, writing tests/eval/docs, and iterating on the
  verified spec answers.
- **No LLM/API calls at runtime.** The shipped system (`policy_engine.py`,
  `ask.py`, `run_eval.py`) is pure Python standard library. It needs no API
  key, no network, no model weights — it runs offline on a reviewer's machine.

## What AI did *not* decide

The policy answers are not generated text from a model:

- **Which rule is in force** is decided by the date-aware resolver
  (`resolve_clause`) over a hand-coded amendment table — not by a model
  reading the circular "fresh" each time.
- **All arithmetic** (MDR, caps, GST, limits) is `Decimal` math in code.
  An LLM never computes a rupee figure in this system.
- **All citations** come from the parsed clause table; clause numbers are
  never model-hallucinated. If no clause supports an answer, the status is
  CANNOT_ANSWER.

## What AI did

- Proposed the three-layer architecture (resolver authority / BM25 relevance /
  deterministic calculators) and the effective-date semantics for items A–F.
- Wrote the code and this documentation, then ran the demo + eval suite and
  fixed failures (amount parsing of "Rs.10 lakh" vs "Rs.4,000", question-date
  extraction, false-premise handling).
- Drafted `eval.json` adversarial questions and `WHERE_IT_BREAKS.md`.

## Accountability

Every line was reviewed against the source documents before committing. Per
the spec's warning, the author is prepared to explain each design decision in
`DECISIONS.md` and walk through any code path in a follow-up discussion.
