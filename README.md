# PolicyIQ — Grounded Merchant Policy QA

PolicyIQ is a question-answering assistant for merchant support over three policy
documents that were written at different times and do not always agree: a master
policy, an August 2026 amendment circular, and a stale March 2026 FAQ. The core
idea is that **the correct answer depends on when you ask** — so every question is
resolved against an `as_of_date`. A structured table of circular amendments (item
letter, clause, action, effective date) decides which clauses are actually in
force on that date; superseded clauses are replaced or deleted before any answer
text is composed. BM25 keyword retrieval surfaces candidate clauses for
transparency, but it never decides what is legally applicable — the date-aware
resolver does. All fee, cap, GST and limit arithmetic is computed by code with
`Decimal` (HALF_UP, 2 dp), never guessed by a language model, and every answer
carries real citations (document + clause number) or an honest `CANNOT_ANSWER`.

**Documents:**

- `ai-2-data/policy_master_v1.md` — base policy, v1.0 (effective 01 Jan 2026)
- `ai-2-data/circular_2026_08_amendment.md` — circular MS/2026/17 (most items effective 01 Aug 2026; the refund change effective 01 Sep 2026)
- `ai-2-data/merchant_faq_2026-03.md` — FAQ last updated 12 Mar 2026 (**stale**; contradicts the policy in places)

## Quick start

```bash
# Single question (default as_of_date = 2026-08-15)
python ask.py "When does a small merchant receive UPI money?"
python ask.py "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?" --date 2026-09-05
python ask.py "..." --json          # machine-readable output

# Run the eight questions from the assignment spec
python ask.py --demo

# Run the evaluation suite (15 questions, 7 adversarial)
python run_eval.py
```

No dependencies beyond Python 3.10+. No API key. No network. No LLM at runtime.

## What `ask()` returns

```json
{
  "answer": "T+1 — the next working day ...",
  "citations": [{"doc": "policy_master_v1.md", "clause": "1.1"},
                {"doc": "circular_2026_08_amendment.md", "clause": "item A"}],
  "status": "CONFLICT_RESOLVED",
  "conflict_resolution": "circular MS/2026/17 item A replaced clause 1.1 effective 01 Aug 2026 ...",
  "retrieved_candidates": [["clause:1.1", 3.21]]
}
```

Status values:

| Status | Meaning |
|---|---|
| `ANSWERED` | A single in-force clause set supports the answer. |
| `CONFLICT_RESOLVED` | Documents disagreed (amendment superseded master text, or FAQ contradicts policy); the answer says which rule governs and why. |
| `CANNOT_ANSWER` | No clause supports an answer. The system does not invent clause numbers. |

## Architecture

```
question + as_of_date
        │
        ├─► fact extraction (amount, volume class, merchant category, KYC, hours)
        │
        ├─► BM25 retrieval  ── surfaces candidate clauses/FAQ items (transparency only)
        │                       NEVER decides which rule is legally applicable
        │
        ├─► intent router (settlement | mdr | refund | limit | closure | faq_check | unknown)
        │
        ├─► date-aware resolver  ── for each clause: base text + amendments with
        │                          effective_from <= as_of_date  →  text in force
        │                          (replacements, deletions, annotations)
        │
        └─► deterministic calculators  ── Decimal money math: rate, cap, GST, limits
```

The split matters: **retrieval finds relevant text; the resolver decides what is
law for the given date.** A BM25 score can never promote a superseded clause over
the in-force one. All arithmetic (MDR, caps, GST) is computed by code with
`Decimal` (HALF_UP, 2 dp) — never guessed by a language model.

## Correctness highlights (the traps in the data)

| Trap | How it is handled |
|---|---|
| Circular item C replaces the ₹15 cap with tiered ₹15/₹25 caps from 01 Aug 2026 | Resolver applies item C on that date; Rs.4,000 large-merchant MDR = ₹20 + ₹3.60 GST |
| Item D deletes the 24-hour MDR-reversal clause on 01 Sep 2026 | Same refund question: **yes** on 20 Aug, **no** on 5 Sep |
| FAQ claims "no upper limit" on MDR and a 0.30% small-merchant rate | Flagged as stale: FAQ-2 vs clause 2.3 as amended + item B → `CONFLICT_RESOLVED` |
| Rs.1,50,000 UPI payment exceeds the ₹1,00,000 per-txn limit | Answer leads with the limit rejection, then gives the hypothetical (Capital Markets/Insurance + enhanced KYC) fees |
| FAQ omits the enhanced-KYC condition for ₹2,00,000 insurance limits | Insurance merchant **without** KYC is held to ₹1,00,000 (clauses 4.1/4.4) |
| Item E: daily limit is min(₹1L, customer's bank limit) | Two ₹1L payments in a day → answer "No" with the amended clause |

## Evaluation

```bash
python run_eval.py
```

Current score: **15/15 (100%)**, including 7 adversarial questions (stale FAQ
rate, deleted-clause date shift ×2, false premise ×2, out-of-scope topic,
pre-amendment date). Output also saved in `EVAL_RESULTS.txt`.

## Files

| File | Purpose |
|---|---|
| `policy_engine.py` | Clause parsing, amendment registry, date resolver, BM25 retrieval, fact extraction, calculators, handlers |
| `ask.py` | CLI + `--demo` of the eight spec questions |
| `eval.json` | 15 questions (7 adversarial) with expected status/answer fragments/citations |
| `run_eval.py` | Runs `eval.json`, prints a score table (status / answer / citations per question) |
| `DECISIONS.md` | Every ambiguity hit and the choice made |
| `AI_USAGE.md` | Disclosure of AI tool use |
| `WHERE_IT_BREAKS.md` | Three things the system should not be trusted with |

## Known limitations

See `WHERE_IT_BREAKS.md`. Short version: paraphrased money amounts, multi-part
questions, and unknown merchant-specific account state are weak spots.
