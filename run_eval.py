import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from policy_engine import ask

EVAL_PATH = Path(__file__).parent / "eval.json"


def check_question(entry):
    r = ask(entry["question"], datetime.strptime(entry["as_of_date"], "%Y-%m-%d").date())
    checks = {}
    checks["status"] = r["status"] == entry["expected_status"]
    missing = [s for s in entry["expected_answer_contains"] if s not in r["answer"]]
    checks["answer"] = not missing
    result_cites = {(c["doc"], c["clause"]) for c in r["citations"]}
    missing_cites = [(c["doc"], c["clause"]) for c in entry["expected_citations"]
                     if (c["doc"], c["clause"]) not in result_cites]
    checks["citations"] = not missing_cites
    score = sum(checks.values()) / 3
    return r, checks, missing, missing_cites, score


def main():
    entries = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    print(f"{'ID':<5} {'ADV':<4} {'STATUS':<20} {'status':>6} {'answer':>7} {'cites':>6} {'score':>6}")
    print("-" * 64)
    total = 0.0
    failures = []
    for e in entries:
        r, checks, missing, missing_cites, score = check_question(e)
        total += score
        adv = "ADV" if e.get("adversarial") else ""
        print(f"{e['id']:<5} {adv:<4} {r['status']:<20} "
              f"{'PASS' if checks['status'] else 'FAIL':>6} "
              f"{'PASS' if checks['answer'] else 'FAIL':>7} "
              f"{'PASS' if checks['citations'] else 'FAIL':>6} {score:>6.2f}")
        if not all(checks.values()):
            failures.append((e, r, missing, missing_cites))
    print("-" * 64)
    n = len(entries)
    print(f"TOTAL: {total:.2f} / {n}  ({total/n*100:.0f}%)   questions={n}  "
          f"adversarial={sum(1 for e in entries if e.get('adversarial'))}")
    if failures:
        print("\nFAILURES:")
        for e, r, missing, missing_cites in failures:
            print(f"  {e['id']}: got status={r['status']} expected={e['expected_status']}")
            if missing:
                print(f"       answer missing substrings: {missing}")
            if missing_cites:
                print(f"       missing citations: {missing_cites}")
            print(f"       answer: {r['answer'][:200]}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
