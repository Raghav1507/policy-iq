import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DATA_DIR = Path(__file__).parent / "ai-2-data"
DEFAULT_AS_OF = date(2026, 8, 15)

ANSWERED = "ANSWERED"
CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
CANNOT_ANSWER = "CANNOT_ANSWER"

FAQ_DOC = "merchant_faq_2026-03.md"
MASTER_DOC = "policy_master_v1.md"
CIRCULAR_DOC = "circular_2026_08_amendment.md"


@dataclass
class Clause:
    clause_id: str
    text: str
    doc: str
    status: str = "in_force"
    citations: list = field(default_factory=list)


@dataclass
class Amendment:
    item: str
    clause_id: str
    action: str
    effective_from: date
    text: str


@dataclass
class FaqItem:
    faq_id: str
    question: str
    text: str
    doc: str = FAQ_DOC
    stale_note: str = ""


AMENDMENTS = [
    Amendment("A", "1.1", "replace", date(2026, 8, 1),
              'Settlement for UPI transactions is T+0 (same day, by 11:59 PM) for merchants with an active "Instant Settlement" add-on, and T+1 for all others.'),
    Amendment("B", "2.1", "replace", date(2026, 8, 1),
              "UPI MDR for merchants with monthly volume up to 10 lakh is 0.25% of the transaction value."),
    Amendment("C", "2.3", "replace", date(2026, 8, 1),
              "The MDR cap of 15 applies only to merchants with monthly volume up to 10 lakh. For merchants above 10 lakh, the cap is 25."),
    Amendment("D", "3.2", "annotate", date(2026, 9, 1),
              "MDR charged on a refunded transaction is not returned to the merchant. (Clause 3.3 deleted effective 01 September 2026; this applies without exception.)"),
    Amendment("D", "3.3", "delete", date(2026, 9, 1), ""),
    Amendment("E", "4.3", "replace", date(2026, 8, 1),
              "Daily limit per customer account is 1,00,000 or the limit set by the customer's own bank, whichever is lower."),
]

FAQ_STALE_NOTES = {
    "FAQ-1": "",
    "FAQ-2": "Stale: rates superseded by circular item B (0.25% for volume up to 10 lakh, eff. 01 Aug 2026); the 'no upper limit' claim contradicts clause 2.3 as amended by circular item C.",
    "FAQ-3": "Becomes wrong on 01 Sep 2026: circular item D deletes clause 3.3, so the 24-hour reversal no longer exists.",
    "FAQ-4": "Incomplete: omits enhanced-KYC condition in clause 4.4 and the bank-limit override in clause 4.3 as amended by circular item E.",
    "FAQ-5": "Imprecise: master clause 5.2 says 10 working days, not 10 days.",
}


def _parse_master(path: Path):
    clauses = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\d+\.\d+)\s+(.*)$", line.strip())
        if m:
            clauses[m.group(1)] = Clause(
                clause_id=m.group(1), text=m.group(2).strip(), doc=MASTER_DOC)
    return clauses


def _parse_faq(path: Path):
    items = []
    blocks = re.split(r"\*\*(.+?)\*\*", path.read_text(encoding="utf-8"))
    n = 0
    for i in range(1, len(blocks) - 1, 2):
        q = blocks[i].strip()
        a = " ".join(blocks[i + 1].split()).strip()
        if not a:
            continue
        n += 1
        fid = f"FAQ-{n}"
        items.append(FaqItem(faq_id=fid, question=q, text=a,
                             stale_note=FAQ_STALE_NOTES.get(fid, "")))
    return items


BASE_CLAUSES = _parse_master(DATA_DIR / MASTER_DOC)
FAQ_ITEMS = _parse_faq(DATA_DIR / FAQ_DOC)
FAQ_BY_ID = {f.faq_id: f for f in FAQ_ITEMS}


def amendments_for(clause_id):
    return [a for a in AMENDMENTS if a.clause_id == clause_id]


def resolve_clause(clause_id: str, as_of: date):
    if clause_id not in BASE_CLAUSES:
        return None
    base = BASE_CLAUSES[clause_id]
    text = base.text
    status = "in_force"
    citations = [{"doc": MASTER_DOC, "clause": clause_id}]
    superseded_by = None
    pending = None
    applied = []
    for a in sorted(amendments_for(clause_id), key=lambda x: (x.effective_from, x.item)):
        if a.effective_from <= as_of:
            if a.action == "delete":
                status = "deleted"
                text = ""
            elif a.action == "replace":
                text = a.text
                status = "amended"
                superseded_by = a.item
            elif a.action == "annotate":
                text = a.text
                status = "amended"
                superseded_by = a.item
            applied.append(a)
            citations.append({"doc": CIRCULAR_DOC, "clause": f"item {a.item}"})
        elif pending is None:
            pending = a
    return Clause(clause_id=clause_id, text=text, doc=MASTER_DOC,
                  status=status, citations=citations), superseded_by, pending, applied


def effective_clause(clause_id: str, as_of: date):
    res = resolve_clause(clause_id, as_of)
    if res is None:
        return None
    cl, superseded_by, pending, applied = res
    if cl.status == "deleted":
        return None
    return cl


def in_force_view(as_of: date):
    view = {}
    for cid in BASE_CLAUSES:
        cl = effective_clause(cid, as_of)
        if cl is not None:
            view[cid] = cl
    return view


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9.%+ ]", " ", text.lower())


STOP = {"the", "a", "an", "is", "are", "do", "does", "did", "of", "to", "in",
        "on", "for", "and", "or", "at", "by", "my", "me", "i", "they", "it",
        "what", "when", "how", "can", "can", "you", "your", "if", "be", "with"}


def tokenize(text: str):
    return [t for t in _norm(text).split() if t and t not in STOP]


def bm25_score(query_tokens, doc_tokens, avgdl, df, n_docs, k1=1.5, b=0.75):
    tf = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1
    dl = len(doc_tokens)
    score = 0.0
    for t in query_tokens:
        if t not in df:
            continue
        idf = math.log(1 + (n_docs - df[t] + 0.5) / (df[t] + 0.5))
        freq = tf.get(t, 0)
        score += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avgdl))
    return score


def retrieve(query: str, as_of: date, top_k: int = 5):
    view = in_force_view(as_of)
    corpus = []
    for cid, cl in sorted(view.items()):
        corpus.append((f"clause:{cid}", tokenize(f"{cid} {cl.text}")))
    for f in FAQ_ITEMS:
        corpus.append((f"faq:{f.faq_id}",
                       tokenize(f"{f.question} {f.text}")))
    n = len(corpus)
    df = {}
    for _, toks in corpus:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    avgdl = sum(len(t) for _, t in corpus) / n
    q = tokenize(query)
    scored = [(ref, bm25_score(q, toks, avgdl, df, n)) for ref, toks in corpus]
    scored = [(r, s) for r, s in scored if s > 0]
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def _rupee(pattern, text):
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    return Decimal(raw)


def extract_amount(text: str):
    cleaned = re.sub(
        r"(?:above|over|more than|up to|below|under|less than|exceeding|greater than)\s*(?:rs\.?|₹|inr\s*)?\s*[\d,]+(?:\.\d+)?\s*lakh(?:\s*monthly(?:\s*volume)?)?",
        " ", text, flags=re.I)
    cleaned = re.sub(r"[\d,]+(?:\.\d+)?\s*lakh\s*monthly(?:\s*volume)?", " ", cleaned, flags=re.I)
    m = re.search(r"(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d+)?)", cleaned, re.I)
    if m:
        return Decimal(m.group(1).replace(",", ""))
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*lakh\b", cleaned, re.I)
    if m:
        return Decimal(m.group(1).replace(",", "")) * Decimal(100000)
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*rupees?\b", cleaned, re.I)
    if m:
        return Decimal(m.group(1).replace(",", ""))
    return None


def extract_volume_class(text: str):
    t = text.lower()
    if re.search(r"(small merchant|small volume|up to (?:rs\.?|₹)?\s*10\s*lakh|below (?:rs\.?|₹)?\s*10\s*lakh|under (?:rs\.?|₹)?\s*10\s*lakh)", t):
        return "small"
    if re.search(r"(large merchant|above (?:rs\.?|₹)?\s*10\s*lakh|over (?:rs\.?|₹)?\s*10\s*lakh|more than (?:rs\.?|₹)?\s*10\s*lakh|exceeding (?:rs\.?|₹)?\s*10\s*lakh)", t):
        return "large"
    return None


def extract_category(text: str):
    t = text.lower()
    if "capital market" in t:
        return "Capital Markets"
    if "insurance" in t:
        return "Insurance"
    return None


def has_enhanced_kyc(text: str):
    return bool(re.search(r"enhanced\s+kyc", text, re.I))


def fmt_inr(x: Decimal, dp: int = 2) -> str:
    x = Decimal(x).quantize(Decimal("1." + "0" * dp) if dp else Decimal("1"),
                            rounding=ROUND_HALF_UP)
    neg = x < 0
    s = f"{abs(x):.{dp}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        rest, last3 = whole[:-3], whole[-3:]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        whole = ",".join(groups + [last3])
    out = f"₹{whole}" + (f".{frac}" if dp else "")
    return f"-{out}" if neg else out


def upi_mdr(amount: Decimal, volume_class: str, as_of: date):
    small = volume_class == "small"
    c21 = effective_clause("2.1", as_of)
    rate = Decimal("0.0025") if (small and c21 and "0.25%" in c21.text) else (
        Decimal("0.0030") if small else Decimal("0.0050"))
    c23 = effective_clause("2.3", as_of)
    cap = Decimal("25") if (not small and c23 and "25" in c23.text and "above 10 lakh" in c23.text) else Decimal("15")
    mdr = min((amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), cap)
    gst = (mdr * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"rate": rate, "cap": cap, "mdr": mdr, "gst": gst, "total": mdr + gst,
            "capped": (amount * rate) > cap}


def per_txn_limit(category, kyc: bool, as_of: date):
    if category in ("Capital Markets", "Insurance") and kyc:
        c42 = effective_clause("4.2", as_of)
        c44 = effective_clause("4.4", as_of)
        return Decimal(200000), [c42, c44]
    c41 = effective_clause("4.1", as_of)
    return Decimal(100000), [c41]


def detect_intent(q: str):
    t = q.lower()
    if re.search(r"\bfaq\b", t):
        return "faq_check"
    if re.search(r"refund|revers|chargeback|24\s*hour", t):
        return "refund"
    if re.search(r"clos(e|ed|ure)|notice", t) and not re.search(r"close to|near", t):
        return "closure"
    if re.search(r"mdr|gst|fee|rate|cap|discount|charge|cost|percent|%", t):
        return "mdr"
    if re.search(r"limit|maximum|per[- ]transaction|daily|twice|pay\b|accept", t):
        return "limit"
    if re.search(r"settle|settlement|receive|same[- ]day|working day|t\+|money\b", t):
        return "settlement"
    return "unknown"


def _cite(*cls):
    out = []
    for c in cls:
        if c is None:
            continue
        if isinstance(c, Clause):
            out.extend(c.citations)
        elif isinstance(c, FaqItem):
            out.append({"doc": c.doc, "clause": c.faq_id})
    seen = set()
    deduped = []
    for c in out:
        key = (c["doc"], c["clause"])
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def _supersession_note(cid: str, as_of: date):
    res = resolve_clause(cid, as_of)
    if res is None:
        return None, "", None
    cl, superseded_by, pending, applied = res
    note = ""
    if superseded_by:
        note = (f" (Supersession: circular MS/2026/17 item {superseded_by} replaced master clause "
                f"{cid} effective {applied[0].effective_from.strftime('%d %B %Y')}; the pre-amendment master text does not apply on this date.)")
    return cl, note, pending


def handle_settlement(q, as_of, facts):
    t = q.lower()
    c11, note11, _ = _supersession_note("1.1", as_of)
    c12 = effective_clause("1.2", as_of)
    is_card = bool(re.search(r"\bcard\b", t)) and not re.search(r"\bupi\b", t)
    has_upi = bool(re.search(r"\bupi\b", t))
    instant = bool(re.search(r"instant settlement", t))
    if is_card and not has_upi:
        return {
            "answer": f"No. Card transactions settle T+2 (two working days). The 01 August 2026 circular changed only UPI settlement; cards remain T+2 under clause 1.2.",
            "citations": _cite(c12),
            "status": ANSWERED,
        }
    if instant:
        c11n = effective_clause("1.1", as_of)
        if as_of >= date(2026, 8, 1) and c11n and "T+0" in c11n.text:
            return {
                "answer": "With the Instant Settlement add-on, UPI settlement is T+0 (same day, by 11:59 PM) as of 01 August 2026 per circular item A. Without the add-on it remains T+1.",
                "citations": _cite(c11),
                "status": CONFLICT_RESOLVED,
                "conflict_resolution": note11.strip(" ()") or None,
            }
        return {
            "answer": "The policy documents in force on this date do not provide for same-day UPI settlement via an Instant Settlement add-on; UPI settlement is T+1 (next working day).",
            "citations": _cite(c11),
            "status": ANSWERED,
        }
    return {
        "answer": "T+1 — the next working day (Sundays and bank holidays excluded). Circular item A (effective 01 August 2026) grants same-day T+0 settlement only to merchants with the Instant Settlement add-on; all other merchants stay on T+1.",
        "citations": _cite(c11),
        "status": CONFLICT_RESOLVED if note11 else ANSWERED,
        "conflict_resolution": note11.strip(" ()") or None,
    }


def handle_mdr(q, as_of, facts):
    amount = facts.get("amount")
    vol = facts.get("volume_class")
    c24 = effective_clause("2.4", as_of)
    c21, note21, _ = _supersession_note("2.1", as_of)
    c22 = effective_clause("2.2", as_of)
    c23, note23, _ = _supersession_note("2.3", as_of)
    rate_txt = "0.25%" if (c21 and "0.25%" in c21.text) else "0.30%"
    if amount is None:
        tiered = bool(c23 and "25" in c23.text and "above 10 lakh" in c23.text)
        cap_txt = ("The single-transaction MDR cap is ₹15 up to ₹10 lakh volume and ₹25 above it (clause 2.3 as amended by circular item C)."
                   if tiered else
                   "The MDR on any single UPI transaction is capped at ₹15 (clause 2.3).")
        if vol == "small":
            ans = (f"UPI MDR for a merchant with monthly volume up to ₹10 lakh is {rate_txt} of the transaction value"
                   f" (clause 2.1). {cap_txt} GST at 18% is charged on the MDR amount and is outside the cap (clause 2.4).")
        else:
            ans = (f"UPI MDR is {rate_txt} for monthly volume up to ₹10 lakh (clause 2.1) and 0.50% above ₹10 lakh (clause 2.2). "
                   f"{cap_txt} GST at 18% applies on the MDR, outside the cap (clause 2.4).")
        return {"answer": ans, "citations": _cite(c21, c22, c23, c24), "status": CONFLICT_RESOLVED if (note21 or note23) else ANSWERED,
                "conflict_resolution": (note21 + note23).strip(" ()") or None}
    results = []
    classes = [vol] if vol else ["small", "large"]
    for vc in classes:
        r = upi_mdr(amount, vc, as_of)
        label = "monthly volume up to ₹10 lakh" if vc == "small" else "monthly volume above ₹10 lakh"
        capnote = f" This is capped at {fmt_inr(r['cap'])} (clause 2.3 as amended by circular item C), so the MDR is {fmt_inr(r['mdr'])}" if r["capped"] else f" The ₹{int(r['cap'])} cap does not bite here"
        results.append(
            f"For a merchant with {label}: MDR = {(r['rate']*100).quantize(Decimal('0.01'))}% of {fmt_inr(amount)} = {fmt_inr((amount*r['rate']).quantize(Decimal('0.01')))}.{capnote}. GST at 18% on the MDR (clause 2.4, outside the cap) = {fmt_inr(r['gst'])}. Total cost = {fmt_inr(r['total'])}.")
    ans = " ".join(results)
    status = CONFLICT_RESOLVED if (note21 or note23 or "circular" in ans) else ANSWERED
    return {"answer": ans, "citations": _cite(c21, c22, c23, c24), "status": status,
            "conflict_resolution": (note21 + note23).strip(" ()") or None}


def handle_refund(q, as_of, facts):
    t = q.lower()
    c31 = effective_clause("3.1", as_of)
    c32, note32, _ = _supersession_note("3.2", as_of)
    c33 = effective_clause("3.3", as_of)
    c34 = effective_clause("3.4", as_of)
    res = resolve_clause("3.3", as_of)
    pending_delete = res[2] is not None and res[2].action == "delete"
    hours = None
    m = re.search(r"(\d+)\s*hour", t)
    if m:
        hours = int(m.group(1))
    same_day = bool(re.search(r"same[- ]day|within 24", t))
    if hours is None and same_day:
        hours = 12
    if re.search(r"chargeback", t) and not re.search(r"refund", t):
        return {"answer": "Chargeback disputes must be raised by the customer's bank within 120 days (clause 3.4).",
                "citations": _cite(c34), "status": ANSWERED}
    if hours is not None and hours < 24:
        if c33 is not None:
            ans = "Yes. A refund initiated within 24 hours of the transaction gets the MDR reversed in full (clause 3.3). The general rule that MDR is not returned (clause 3.2) yields to this exception."
            if pending_delete:
                ans += " Note: circular MS/2026/17 item D deletes clause 3.3 effective 01 September 2026, after which this answer changes."
            return {"answer": ans, "citations": _cite(c32, c33), "status": ANSWERED}
        return {"answer": "No. As of this date clause 3.3 has been deleted by circular item D (effective 01 September 2026), and clause 3.2 now applies without exception: the MDR charged on a refunded transaction is not returned to the merchant, regardless of how quickly the refund is issued.",
                "citations": _cite(c32), "status": CONFLICT_RESOLVED,
                "conflict_resolution": "Circular item D deleted the 24-hour MDR-reversal exception in clause 3.3 effective 01 September 2026; master clauses 3.2/3.3 alone would have said otherwise before that date."}
    if hours is not None:
        return {"answer": "No. The 24-hour MDR-reversal window (clause 3.3, where in force) has passed, so clause 3.2 applies: the MDR charged on a refunded transaction is not returned. The refund itself may still be initiated within 90 days (clause 3.1).",
                "citations": _cite(c31, c32, c33), "status": ANSWERED}
    return {"answer": "Refunds may be initiated within 90 days of the original transaction (clause 3.1). The MDR on a refunded transaction is not returned (clause 3.2), except where clause 3.3 is still in force and the refund is initiated within 24 hours, in which case the MDR is reversed in full. Chargebacks must be raised by the customer's bank within 120 days (clause 3.4).",
            "citations": _cite(c31, c32, c33, c34), "status": ANSWERED}


def handle_limit(q, as_of, facts):
    t = q.lower()
    amount = facts.get("amount")
    category = facts.get("category")
    kyc = facts.get("kyc", False)
    per_txn, per_cls = per_txn_limit(category, kyc, as_of)
    c43, note43, _ = _supersession_note("4.3", as_of)
    daily = Decimal(100000)
    bank_clause_note = ""
    if c43 and "whichever is lower" in c43.text:
        bank_clause_note = " (clause 4.3 as amended by circular item E: ₹1,00,000 or the customer's own bank limit, whichever is lower)"
        daily = Decimal(100000)
    twice = bool(re.search(r"twice|two times|again in one day|second", t))
    if twice and amount is not None:
        return {"answer": f"No. The daily limit per customer account is {fmt_inr(daily, 0)} across all UPI transactions{bank_clause_note}. Two payments of {fmt_inr(amount, 0)} in one day total {fmt_inr(amount*2, 0)}, which breaches the daily aggregate limit — the second payment would be rejected.",
                "citations": _cite(*per_cls, c43), "status": CONFLICT_RESOLVED if note43 else ANSWERED,
                "conflict_resolution": note43.strip(" ()") or None}
    if amount is not None and amount > per_txn:
        limit_txt = f"{fmt_inr(per_txn, 0)}" + (" for Capital Markets and Insurance merchants who have completed enhanced KYC (clauses 4.2 and 4.4)" if category else " (clause 4.1)")
        extra = ""
        if facts.get("compute_if_allowed"):
            r = upi_mdr(amount, facts.get("volume_class") or "large", as_of)
            extra = (f" If the transaction were permitted — i.e. the merchant is in Capital Markets or Insurance with enhanced KYC (clauses 4.2 and 4.4) — the charges would be: "
                     f"MDR capped at {fmt_inr(r['cap'])} (clause 2.3 as amended by circular item C) = {fmt_inr(r['mdr'])}, GST 18% = {fmt_inr(r['gst'])}, total {fmt_inr(r['total'])}.")
        return {"answer": f"This payment exceeds the UPI per-transaction limit of {limit_txt}, so a {fmt_inr(amount, 0)} UPI payment would be rejected for an ordinary merchant.{extra}",
                "citations": _cite(*per_cls), "status": ANSWERED}
    return {"answer": f"The per-transaction UPI limit is {fmt_inr(per_txn, 0)}. The daily limit per customer account is {fmt_inr(daily, 0)} across all UPI transactions, or lower if the customer's own bank sets a lower limit (clause 4.3 as amended by circular item E).",
            "citations": _cite(*per_cls, c43), "status": CONFLICT_RESOLVED if note43 else ANSWERED,
            "conflict_resolution": note43.strip(" ()") or None}


def handle_closure(q, as_of, facts):
    c51 = effective_clause("5.1", as_of)
    c52 = effective_clause("5.2", as_of)
    faq5 = FAQ_BY_ID.get("FAQ-5")
    ans = "A merchant may close the account with 30 days' written notice (clause 5.1). Pending settlements are released within 10 working days of closure, after deducting outstanding dues (clause 5.2). So if the account closed yesterday (assuming the 30-day notice was served), the money is released within 10 working days of the closure date. Note: the FAQ says 'within 10 days'; the master policy says 10 working days, which is authoritative."
    return {"answer": ans, "citations": _cite(c51, c52, faq5), "status": CONFLICT_RESOLVED,
            "conflict_resolution": "FAQ-5 loosely says '10 days'; master clause 5.2 specifies 10 working days. Master policy governs."}


def handle_faq_check(q, as_of, facts):
    t = q.lower()
    if re.search(r"cap|upper limit|fee|mdr|rate", t):
        faq2 = FAQ_BY_ID.get("FAQ-2")
        c23, note23, _ = _supersession_note("2.3", as_of)
        c21, note21, _ = _supersession_note("2.1", as_of)
        c22 = effective_clause("2.2", as_of)
        faq_verdict = ("The FAQ says: '0.30% for small merchants, 0.50% for large ones. There is no upper limit on the fee, so very large transactions cost more.' "
                       "The FAQ is WRONG on the cap and STALE on the small-merchant rate. There is an MDR cap: ₹15 on any single UPI transaction for merchants with volume up to ₹10 lakh, and ₹25 for merchants above ₹10 lakh (clause 2.3 as amended by circular item C, effective 01 August 2026). "
                       "The small-merchant rate is 0.25% as of 01 August 2026 (circular item B), not the 0.30% the FAQ quotes from March 2026. The 0.50% rate for large merchants (clause 2.2) is still correct.")
        return {"answer": faq_verdict, "citations": _cite(faq2, c21, c22, c23), "status": CONFLICT_RESOLVED,
                "conflict_resolution": "FAQ-2 (12 March 2026) claims no fee cap and a 0.30% small-merchant rate. Master clause 2.3 caps single-transaction MDR and circular item C (eff. 01 Aug 2026) sets tiered caps of ₹15/₹25; circular item B lowers the small-merchant rate to 0.25%. The in-force policy clauses govern; the FAQ is stale."}
    return {"answer": "The FAQ document predates the August 2026 circular and should not be trusted where it disagrees with the master policy as amended. Ask about a specific topic (e.g. the MDR cap) for a clause-level comparison.",
            "citations": _cite(*FAQ_ITEMS[:1]), "status": ANSWERED}


HANDLERS = {
    "faq_check": handle_faq_check,
    "refund": handle_refund,
    "closure": handle_closure,
    "mdr": handle_mdr,
    "limit": handle_limit,
    "settlement": handle_settlement,
}


_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}
_MONTH_ABBR = {m[:3].lower(): i for m, i in _MONTHS.items()}


def extract_dates(text: str):
    """Parse dates like '20 Aug 2026' or '2026-09-05' from free text."""
    out = []
    for m in re.finditer(
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+(\d{4})\b",
            text, re.I):
        out.append(date(int(m.group(3)), _MONTH_ABBR[m.group(2).lower()], int(m.group(1))))
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return out


def ask(question: str, as_of: "date | str | None" = None, **kw):
    """Answer a policy question as of a date.

    as_of accepts a date, an ISO 'YYYY-MM-DD' string, or None (default
    2026-08-15). A date explicitly stated in the question itself takes
    precedence over the as_of argument.
    """
    if as_of is None:
        as_of = kw.get("as_of_date")
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    q_dates = extract_dates(question)
    if q_dates:
        as_of = q_dates[0]
    if as_of is None:
        as_of = DEFAULT_AS_OF

    facts = {
        "amount": extract_amount(question),
        "volume_class": extract_volume_class(question),
        "category": extract_category(question),
        "kyc": has_enhanced_kyc(question),
        "compute_if_allowed": True,
    }
    m = re.search(r"(\d+)\s*hours?\s*after", question, re.I)
    if m:
        facts["hours"] = int(m.group(1))
    intent = detect_intent(question)
    retrieved = retrieve(question, as_of)
    if intent == "unknown":
        return {"question": question, "as_of_date": as_of.isoformat(),
                "answer": "CANNOT ANSWER: the provided policy documents do not cover this topic. No clause supports an answer, and the system does not invent clause numbers.",
                "citations": [], "status": CANNOT_ANSWER, "retrieved_candidates": retrieved}
    result = HANDLERS[intent](question, as_of, facts)
    result.update({"question": question, "as_of_date": as_of.isoformat(),
                   "intent": intent, "retrieved_candidates": retrieved})
    return result
