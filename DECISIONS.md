# DECISIONS — ambiguities, traps, and the choices made

Chronological; each entry says what was ambiguous, what was chosen, and why.

## 1. How to represent the circular's amendments

**Ambiguity:** The circular is prose ("Clause 1.1 is replaced: ...", "Clause 3.3 is
deleted. Effective 01 September 2026."). A generic NLP parser of legal prose is a
rabbit hole and risky under time pressure; hard-coding *answers* instead of
*amendments* would be memorisation, not reasoning.

**Choice:** Encode the circular once as a structured amendment registry
(`AMENDMENTS` in `policy_engine.py`) — item letter, clause id, action
(replace/delete/annotate), effective date, new text. The master document and FAQ
are genuinely parsed from the files (regex on clause numbers / bold FAQ questions).
Citations always point at the real document + clause/item, never invented ids.

**Why:** The correctness risk in this assignment is *date handling and
supersession*, not circular-parsing. The registry makes effective-date logic
explicit and testable. In a production build with more time, the registry would be
emitted by an LLM pass over the circular and verified against this hand-encoded
golden copy.

## 2. Retrieval must not decide legal applicability

**Ambiguity:** BM25 scores topical similarity. A superseded clause can score higher
than the amendment that replaces it (the amendment often doesn't repeat the
question's keywords). Letting retrieval pick "the winning rule" silently answers
from stale policy — exactly the trap in this data set.

**Choice:** Strict split. BM25 retrieves *candidates* (surfaced in the output under
`retrieved_candidates` for transparency, and used to pull FAQ items into citation
sets). The **date-aware resolver** alone decides which text is in force: an
amendment with `effective_from <= as_of_date` replaces or deletes the base clause
before any answer text is composed.

**Why:** The spec grades document reasoning — superseded clauses, effective dates,
the stale FAQ. Retrieval is a finding tool, not a legal arbiter.

## 3. When to say `CONFLICT_RESOLVED` vs `ANSWERED`

**Ambiguity:** Item A replaced clause 1.1, but for a merchant *without* the Instant
Settlement add-on the outcome (T+1) is the same as the old text. Is that a
"conflict"?

**Choice:** If the clause the answer relies on was amended in force on the given
date, or a FAQ item contradicts the governing clause, status is
`CONFLICT_RESOLVED` and `conflict_resolution` explains the supersession — even when
the numeric outcome coincides. `ANSWERED` is reserved for answers resting only on
unchanged clauses.

**Why:** Over-claiming `ANSWERED` hides that we did the date reasoning at all.
The reviewer can see exactly which circular item moved.

## 4. Q3 — Rs.1,50,000 UPI payment (false premise)

**Ambiguity:** The question asks "what do they pay?" for an amount that exceeds the
₹1,00,000 per-transaction UPI limit (clause 4.1). Answering only the fee math
endorses an impossible transaction; answering `CANNOT_ANSWER` dodges the intent.

**Choice:** `ANSWERED` leading with the limit rejection (the correct real-world
answer), then the hypothetical fees *if* the merchant were in Capital Markets or
Insurance with enhanced KYC (clauses 4.2 + 4.4): MDR capped at ₹25 (item C), GST
₹4.50, total ₹29.50.

**Why:** Support agents get asked "what would it cost" about borderline
transactions; both facts matter and the conditions must be stated.

## 5. FAQ says "no upper limit" — is the FAQ ever authoritative?

**Ambiguity:** FAQ-2 (12 Mar 2026) claims there is no MDR cap and quotes 0.30% for
small merchants. Master clause 2.3 caps MDR; item B (0.25%) and item C (₹15/₹25
caps) supersede both the FAQ *and* parts of the master.

**Choice:** The FAQ is treated as **evidence of a claim**, never as governing rule.
When a question touches a FAQ-covered topic, the FAQ text is quoted, then judged
against the in-force clauses: FAQ is wrong on the cap, stale on the rate, right on
0.50% for large merchants. Status `CONFLICT_RESOLVED`.

**Why:** "Is the FAQ right?" is an explicit spec question; a grounded system must
be able to say a first-party document is wrong.

## 6. Refund inside 24 hours — the date fork

**Ambiguity:** Clause 3.3 (24-hour MDR reversal) is deleted by item D effective
01 Sep 2026, and 3.2 then "applies without exception". The FAQ still advertises
the reversal.

**Choice:** The resolver returns no clause 3.3 on/after 01 Sep 2026, so the refund
handler answers from 3.2 alone: MDR **not** returned; before that date, reversed in
full with a forward-looking note about item D. Eval tests both sides of the fork
(20 Aug vs 5 Sep, and 10 Sep).

**Why:** This is the assignment's core "the policy that changed" mechanic; the
answer must flip purely from `as_of_date`.

## 7. "Within 24 hours" boundary

**Ambiguity:** Does "exactly 24 hours later" fall inside clause 3.3's window?

**Choice:** Inclusive: `hours <= 24` counts as within. Phrasings like "within 24
hours" or "same day" are normalised into the window.

**Why:** "Within 24 hours of the transaction" reads inclusively; a system that
rejects the boundary second would mislead a merchant racing the clock.

## 8. Daily limit vs the customer's bank limit (item E)

**Ambiguity:** Item E makes the daily limit "₹1,00,000 or the limit set by the
customer's own bank, whichever is lower". We do not know any customer's bank limit.

**Choice:** Answer the knowable part: ₹1,00,000 is the ceiling; a bank may set
lower, never higher (the rule takes the *lower*). For "can I pay ₹1L twice?" the
answer is No regardless of the bank's limit.

**Why:** Never invent facts not in the documents; still answer decisively where the
outcome is determined (Q6 is No under every possible bank limit).

## 9. Q7 — "closed my account yesterday": notice period vs release

**Ambiguity:** "Yesterday" conflicts with clause 5.1's 30-day written notice.
Presumably the merchant means the closure *effective* date after notice, but the
phrasing skips that.

**Choice:** Assume closure has already taken effect (notice served), answer the
actual question — money released within **10 working days** of closure (5.2) — and
state the 30-day notice requirement. Also flag that FAQ-5's "within 10 days" is
imprecise versus the master's "10 working days"; master governs.

## 10. Unspecified merchant volume tier

**Ambiguity:** "What is the UPI MDR?" with no volume figure — clause 2.1 and 2.2
give different rates.

**Choice:** State both tiers explicitly rather than assuming one and rather than
`CANNOT_ANSWER`. When an amount is present but the tier is unstated, the same
two-branch answer is given with per-tier computed figures.

**Why:** Defaulting to the cheap tier would quietly under-charge in a
merchant-facing answer; both branches is the honest complete answer.

## 11. Arithmetic and rounding

**Choice:** All money math in `Decimal`, GST computed on the MDR (clause 2.4: GST
is *outside* the cap), HALF_UP rounding to 2 dp at each computed step (MDR, then
GST). The cap compares the unrounded MDR against the cap, then takes the cap.

**Why:** Floats are banned for money; rounding steps match how a ledger would post
paise. Cap-then-GST order follows 2.3/2.4 structure (cap is on MDR, GST is on the
charged MDR).

## 12. Status of an unchanged figure inside an amended clause set

**Ambiguity:** E14 asks for the per-transaction maximum for an insurance merchant
with enhanced KYC — the ₹2,00,000 figure is unchanged — but the handler's full
answer also covers the daily limit, which *was* amended (item E).

**Choice:** Status `CONFLICT_RESOLVED` because the answer as a whole rests in part
on amended 4.3. The per-txn citations (4.2/4.4) are exact.

**Why:** Status describes the answer delivered, not the single figure queried.

## 13. No LLM at runtime

**Ambiguity:** The spec allows LLMs but requires the reviewer to run everything
without an API key.

**Choice:** Runtime is pure deterministic code (retrieval + resolver + calculators).
No network, no keys, no cached model responses needed. AI tool use is disclosed in
`AI_USAGE.md` — it was used to *author* the system during the timed assignment,
not to *answer* questions when the system runs.

**Why:** Guarantees reproducibility and satisfies the offline requirement in the
strongest way; the graded reasoning (dates, supersession, arithmetic) is encoded as
explicit logic a reviewer can read line by line.
