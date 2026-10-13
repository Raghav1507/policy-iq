"""Demo: run the spec questions Q1-Q8 through ask() and print results."""
from policy_engine import ask

QS = [
    ("Q1", "When does a small merchant receive UPI money?", "2026-08-15"),
    ("Q2", "A large merchant (above Rs.10 lakh monthly) receives a Rs.4,000 UPI payment. What MDR and GST do they pay?", "2026-08-15"),
    ("Q3", "Same merchant, a Rs.1,50,000 payment. What do they pay?", "2026-08-15"),
    ("Q4a", "A merchant refunds a customer 3 hours after the sale on 20 Aug 2026. Do they get the MDR back?", "2026-08-20"),
    ("Q4b", "A merchant refunds a customer 3 hours after the sale on 5 Sep 2026. Do they get the MDR back?", "2026-09-05"),
    ("Q5", "What does the FAQ say about the MDR cap, and is the FAQ right?", "2026-08-15"),
    ("Q6", "Can a customer pay Rs.1,00,000 twice in one day to a merchant?", "2026-08-15"),
    ("Q7", "I closed my account yesterday. When will I get my money?", "2026-08-15"),
    ("Q8", "Does the policy allow me to settle card payments same day?", "2026-08-15"),
]

if __name__ == "__main__":
    for qid, q, d in QS:
        r = ask(q, d)
        print(f"=== {qid} [{d}] {r['status']} ===")
        print(r["answer"])
        if r.get("how"):
            print(f"  (how resolved: {r['how']})")
        for c in r["citations"]:
            print(f"  cite: {c['document']} #{c['clause']} in_force={c['in_force']}")
        print()
