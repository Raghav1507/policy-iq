# WHERE_IT_BREAKS — three things not to trust this system with

Honest failure modes, chosen because they are the ones most likely to bite in
production, not stylistic nits.

## 1. Paraphrased or non-standard money amounts

**Fails on:** "What's the MDR on a forty-thousand rupee payment?", "on ₹40K",
"on 0.4 million rupiah".

**Why:** `extract_amount()` understands `Rs.4,000` / `₹4,000` / `1.5 lakh` forms.
Natural-language number spellings and unfamiliar abbreviations are not parsed. If
no amount is recognised the system answers the general rate question (both tiers)
instead of computing the specific figure — a **plausible-looking but non-responsive**
answer, which is worse than a hard failure.

**Mitigation if trusted further:** a number-spelling normaliser (easy) plus an
explicit "I could not find an amount in your question; please state it as
Rs.X,XXX" clarification turn (better).

## 2. Multi-part questions get a single-intent answer

**Fails on:** "I got refunded within 2 hours and also want to close my account —
when do I get my money and what's the MDR?".

**Why:** The router picks one handler (here `refund`, since refund keywords rank
ahead of closure). The account-closure half is silently dropped. Citations and the
status remain valid for the half that was answered, so the answer reads
confidently incomplete.

**Mitigation:** detect multiple intent clusters and either chain handlers or
explicitly answer "your question has two parts; answering part one…" — the system
does not do this today.

## 3. Unknown merchant-specific account state

**Fails on:** "When will *my* UPI money settle?" where the merchant actually has
the Instant Settlement add-on (or enhanced KYC, or a bank limit below ₹1L).

**Why:** The documents define rules conditioned on facts the system cannot see
(add-on status, KYC tier, the customer's bank limit). It answers the default rule
(T+1, ₹1L, standard KYC) with no way to flag that the merchant's profile may
change the outcome. The circular's T+0 branch is reachable only when the question
itself mentions the add-on.

**Mitigation:** a merchant-profile lookup feeding the resolver's conditions; until
then, support agents must overlay profile facts themselves. The system's
conditional phrasing ("for merchants with the add-on…, otherwise…") is the only
guardrail.

---

Related known gaps (not counted above): FAQ coverage is wired for the five FAQ
items that exist — a sixth FAQ question would be cited only via BM25, not judged;
and answers are English-template composed, so wildly different phrasings of the
same question produce differently worded (though consistently sourced) answers.
