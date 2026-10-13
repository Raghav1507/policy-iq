import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from policy_engine import DEFAULT_AS_OF, ask

SPEC_QUESTIONS = [
    ("Q1. When does a small merchant receive UPI money?", "2026-08-15"),
    ("Q2. A large merchant (above Rs.10 lakh monthly) receives a Rs.4,000 UPI payment. What MDR and GST do they pay?", "2026-08-15"),
    ("Q3. Same merchant, a Rs.1,50,000 payment. What do they pay?", "2026-08-15"),
    ("Q4a. A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?", "2026-08-20"),
    ("Q4b. A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?", "2026-09-05"),
    ("Q5. What does the FAQ say about the MDR cap, and is the FAQ right?", "2026-08-15"),
    ("Q6. Can a customer pay Rs.1,00,000 twice in one day to a merchant?", "2026-08-15"),
    ("Q7. I closed my account yesterday. When will I get my money?", "2026-08-15"),
    ("Q8. Does the policy allow me to settle card payments same day?", "2026-08-15"),
]


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def print_result(r):
    print(f"Question: {r['question']}")
    print(f"As of:    {r['as_of_date']}")
    print(f"Status:   {r['status']}")
    print(f"Answer:   {r['answer']}")
    if r.get("conflict_resolution"):
        print(f"Resolved: {r['conflict_resolution']}")
    print("Citations:")
    if r["citations"]:
        for c in r["citations"]:
            print(f"  - {c['doc']} :: {c['clause']}")
    else:
        print("  (none)")
    if r.get("retrieved_candidates"):
        print("Retrieved candidates (BM25, for transparency only — never overrides the date resolver):")
        for ref, score in r["retrieved_candidates"]:
            print(f"  - {ref}  score={score:.2f}")


def main():
    p = argparse.ArgumentParser(description="PolicyIQ — grounded merchant policy QA")
    p.add_argument("question", nargs="?", help="Question to ask")
    p.add_argument("--date", default=DEFAULT_AS_OF.isoformat(),
                   help="as_of_date in YYYY-MM-DD (default 2026-08-15)")
    p.add_argument("--demo", action="store_true", help="Run the eight spec questions")
    p.add_argument("--json", action="store_true", help="Emit JSON")
    args = p.parse_args()

    if args.demo:
        for q, d in SPEC_QUESTIONS:
            r = ask(q, parse_date(d))
            if args.json:
                print(json.dumps(r, indent=2, ensure_ascii=False))
            else:
                print_result(r)
                print("-" * 72)
        return

    if not args.question:
        p.print_help()
        sys.exit(1)
    r = ask(args.question, parse_date(args.date))
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print_result(r)


if __name__ == "__main__":
    main()
