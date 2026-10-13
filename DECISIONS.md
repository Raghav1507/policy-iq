# DECISIONS.md — ambiguity log

Every trap/ambiguity in the source documents, what we chose, and why.
Dates matter: the same question can have different correct answers.

## 1. Supersession model: circular beats master from its effective date

Circular MS/2026/17 says it "amends" the master and is "Effective 01 August
2026 unless stated otherwise" (item D states 01 September 2026).

**Choice:** encode items A–E as structured amendments
(`replace` / `delete` / `annotate` with an effective date) and resolve each
clause with `resolve_clause(clause_id, as_of)` at answer time. Master text is
used only for dates *before* the item's effective date.

**Why:** the spec's core requirement is that answers depend on `as_of_date`.
A single flattened "current policy" would silently answer 20 Aug and 5 Sep
identically — exactly the failure mode the circular is designed to catch.

**Rejected:** auto-merging all docs into one "latest" text (loses the
date-dependency), and asking an LLM to re-read all docs per question
(non-deterministic, not offline-safe).

## 2. Refund MDR reversal: the 1 Sep cliff (item D)

Master 3.3 (reversal within 24h) vs circular D (delete 3.3, 3.2 applies
without exception, effective 01 Sep 2026).

- On **20 Aug 2026**: refund in 3h → **MDR reversed in full** (3.3 in force).
  We still *cite* the pending deletion so the user knows the rule is about to
  change — flagged CONFLICT_RESOLVED.
- On **5 Sep 2026**: same refund → **MDR not returned** (3.3 deleted; 3.2
  absolute). CONFLICT_RESOLVED, with the deletion named in the answer.

**Ambiguity:** does "Clause 3.2 now applies without exception" rewrite 3.2's
text, or just void the exception? **Choice:** void the exception — 3.2's
"except as provided in 3.3" becomes a dangling reference once 3.3 is deleted;
we treat the surviving rule as "MDR never returned on refunds".
The refund *window* (90 days, 3.1) is untouched.

## 3. MDR caps are tiered — the FAQ is wrong (item C)

Master 2.3 capped every merchant at ₹15. Item C (eff. 01 Aug 2026): ₹15 for
volume ≤ ₹10 lakh, **₹25 above**. FAQ-2 claims "no upper limit on the fee".

**Choice:** cap by merchant tier at answer time; the FAQ claim is always
wrong (even pre-Aug, master 2.3 capped ₹15). FAQ-2 is quoted with citation,
then overruled: status CONFLICT_RESOLVED.

**Why:** "never invent a clause number" implies never inventing *freedom from*
a clause either. The FAQ predates the circular (12 Mar 2026) and contradicts
both master and circular.

## 4. GST sits outside the cap (clause 2.4)

MDR cap applies to the MDR; GST 18% is charged *on the MDR amount* and is
explicitly "not part of the MDR cap".

**Choice:** `mdr = min(amount × rate, cap); gst = mdr × 0.18; total = mdr + gst`,
all with `Decimal` (no floats). Q2: 0.50% × ₹4,000 = ₹20 < ₹25 cap →
₹20 + ₹3.60 GST. Q3 hypothetical: capped ₹25 + ₹4.50 GST = ₹29.50.

## 5. Q3 false premise: ₹1,50,000 UPI payment

Clause 4.1 caps UPI per-transaction at ₹1,00,000. ₹2,00,000 only for Capital
Markets / Insurance **with enhanced KYC** (4.2 gated by 4.4).

**Choice:** say the payment would be rejected for an ordinary merchant, *and*
compute the fee hypothetically (MDR capped at ₹25 + GST ₹4.50) clearly
labelled as hypothetical — the spec asks "what do they pay?", and the
interesting failure is a system that charges 0.50% × ₹1,50,000 = ₹750.

**Ambiguity:** is "Same merchant" (spec Q3) the large merchant from Q2?
The engine needs the tier stated in the question — eval restates it; a bare
"same merchant" question gets both tiers shown or the limit answer first.

## 6. Item A does not help card settlement (Q8)

Item A amends clause 1.1 (**UPI** settlement) only; item F keeps everything
else unchanged. Card money stays T+2 (clause 1.2).

**Choice:** answer "No" for cards, cite 1.2, and mention that the circular's
T+0 is UPI-only (add-on gated). Naive "same-day settlement is allowed now"
answers are exactly the trap.

## 7. T+0 requires the "Instant Settlement" add-on (Q1)

Item A grants T+0 only to merchants with an *active* add-on; others stay T+1.

**Ambiguity:** a question that doesn't mention the add-on — assume none, or
answer conditionally? **Choice:** answer T+1 (the default for merchants
without the add-on) and name the add-on exception explicitly. For an explicit
"with the add-on" question, T+0 (same day, by 11:59 PM); for "without",
plain T+1. Unknown add-on status is never silently assumed to exist.

## 8. Daily limit: bank override makes it stricter, not looser (Q6)

Item E: daily cap is ₹1,00,000 **or the customer's own bank's limit,
whichever is lower**. Two ₹1,00,000 payments/day breach it regardless.

**Choice:** answer "No" on both readings (pre- and post-01 Aug the answer is
No; post-Aug basis is stricter). CONFLICT_RESOLVED note names the amendment
so a reviewer sees we didn't just quote master 4.3.

## 9. Working days vs calendar days

T+1/T+2/10-working-days all say "working days exclude Sundays and bank
holidays" — but no holiday calendar exists in the docs.

**Choice:** keep answers at the policy level ("next working day", "within 10
working days") and never compute a concrete weekday. Inventing a bank-holiday
list would be inventing facts.

## 10. Account closure: "released within 10 days" (FAQ) vs "10 working days" (5.2)

**Choice:** master 5.2 governs — 10 **working** days after closure, after
deducting outstanding dues. FAQ-5's loose "10 days" is flagged. Also noted:
closure needs 30 days' written notice (5.1); "closed yesterday" is taken at
face value (notice already served).

## 11. Pre-circular dates must get pre-circular answers

Asked for 15 Jul 2026, small-merchant UPI MDR is **0.30%** (master 2.1),
cap ₹15 — circular B/C are not yet in force.

**Choice:** effective-dated resolver handles this for free; eval includes
this as an adversarial case because systems that "bake in" the circular will
answer 0.25% for every date.

## 12. Retrieval is relevance, not authority

Per design rule: BM25 ranks chunks, the resolver decides what is in force.
Retrieved candidates are returned in the JSON for transparency and used only
to detect off-topic questions. An answer's citations always come from the
resolver's clause table — a retrieval hit can never introduce a clause that
is not in force (or explicitly deleted, in which case it is cited *as deleted*).

## 13. CANNOT_ANSWER over guessing

Refused (with reasoning, no invented clauses): add-on pricing/enablement,
card interchange (Visa/Mastercard) — none of these appear in any document.
Also: MDR questions with no volume tier get a conditional two-tier answer
clauses 2.1/2.2, not a single guessed number.

## 14. Question-stated dates override the as_of argument

Spec Q4 says "ask it for 20 Aug 2026 and again for 5 Sep 2026". If the
question text contains an explicit date ("…on 10 September 2026…"), that date
wins over the default/argument — support agents paste questions verbatim.
