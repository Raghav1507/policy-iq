# WHERE_IT_BREAKS.md — three things this system gets wrong or should not be trusted with

Honest list, as required. These are known failure modes, not hypotheticals.

## 1. Paraphrase-heavy or multilingual questions miss the intent router

The intent router (`detect_intent`) is keyword/regex based and BM25 is
lexical. A question like *"bhai ka paisa kitne din me aayega refund karne
pe?"* or *"if I reverse the sale quickly, is the processing percentage
returned?"* may route wrong or fall through to CANNOT_ANSWER even though the
underlying clause (3.3 / 2.x) exists and would answer it.

**Why:** offline constraint rules out embedding models; we chose lexical
retrieval + explicit routing over shipping model weights.
**Mitigation:** ask with the documents' own vocabulary (settlement, MDR,
refund, limit, closure).
**Do not trust it for:** free-form conversational or non-English input.

## 2. It cannot compute real calendar dates ("next Monday", "17 Aug")

T+1, T+2 and "10 working days" all exclude Sundays and bank holidays — but
no holiday calendar exists in the three documents. The system answers at the
policy level ("the next working day") and refuses to name a weekday.

**Why:** inventing an RBI/bank holiday list would be inventing facts, which
the spec forbids ("never invent a clause number" — same spirit for dates).
**Mitigation:** combine the answer with your own bank calendar.
**Do not trust it for:** "exactly which date will the money land?" questions.

## 3. Cross-turn context ("same merchant", previously stated facts)

The engine is stateless per call. Spec Q3's phrasing *"Same merchant, a
Rs.1,50,000 payment"* only works if the merchant tier is restated in the
question (the eval restates it: "A large merchant (above Rs.10 lakh
monthly)…"). Asked bare, "same merchant" carries no memory of Q2's large
merchant: the system still flags the clause 4.1 limit breach (the key
judgement) and shows the capped fee for the default tier, but it will not
remember "large" from a previous turn.

**Why:** no session state by design — every answer must be reproducible from
`(question, as_of_date)` alone, which is also what makes the eval meaningful.
**Mitigation:** restate merchant facts in each question.
**Do not trust it for:** multi-turn support sessions without restatement.
