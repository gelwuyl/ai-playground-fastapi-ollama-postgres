"""Pre-deploy functional test for Mr. Kaypoh's engine (no DB/network needed).

Simulates a full ReAct run by monkeypatching decide_action to follow a scripted
sequence, then asserts the 3-page gate, FINISH acceptance, and eval scoring.
Run: python test_research_engine.py
"""
import os
os.environ["USE_FIXTURES"] = "1"  # use canned search/read results
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")  # gemini_service reads at import

from services import research_engine as engine
from services import research_service as rs

# Scripted model decisions: SEARCH, then 3 READS, then FINISH
SCRIPT = [
    {"reason": "find sources", "action": "SEARCH", "query": "gold price today past month movement factors"},
    {"reason": "read 1", "action": "READ", "url": "https://tradingeconomics.com/commodity/gold"},
    {"reason": "read 2", "action": "READ", "url": "https://gold.org/"},
    {"reason": "read 3", "action": "READ", "url": "https://www.kitco.com/charts/historicalgold.html"},
    {"reason": "enough", "action": "FINISH", "report": "Gold is ~$4,403/oz. Recommend monitoring. [https://tradingeconomics.com/commodity/gold]"},
]
_calls = {"n": 0}
def fake_decide(goal, steps):
    i = _calls["n"]
    _calls["n"] += 1
    return SCRIPT[i] if i < len(SCRIPT) else {"reason": "done", "action": "FINISH", "report": "done"}

rs.decide_action = fake_decide

session = {"id": 1, "query": "what is the price of gold today, and what moved it over the past month?", "status": "PENDING", "final_report": None}
steps = []

# Run the loop
for _ in range(rs.STEP_LIMIT + 1):
    step = engine.run_one_step(session, steps)
    steps.append(step)
    if step["action"] == "FINISH":
        break

print("=== TRACE ===")
for s in steps:
    print(f"STEP {s['step_number']} {s['action']} {s.get('query') or s.get('url') or ''} -> {s.get('observation')}")

# Assertions
assert steps[-1]["action"] == "FINISH", "Should have finished"
assert rs.count_pages_read(steps) >= 3, "Should have read >= 3 pages"
assert steps[-1].get("report"), "Report should be present"

# Test the 3-page gate: FINISH before 3 reads must be refused
gate_steps = [{"step_number": 1, "action": "READ", "url": "https://a.com", "chars_read": 100}]
gate = engine.run_one_step(session, gate_steps)
assert gate["action"] == "REFUSED", "FINISH before 3 pages must be refused"
assert "FINISH refused" in gate["observation"], "Refusal message expected"

# Test duplicate read refusal
dup_steps = [{"step_number": 1, "action": "READ", "url": "https://x.com", "chars_read": 100}]
dup = engine.run_one_step(session, dup_steps)
# scripted next is SEARCH, so force a READ decision
rs.decide_action = lambda g, s: {"reason": "dup", "action": "READ", "url": "https://x.com"}
dup = engine.run_one_step(session, dup_steps)
assert dup["action"] == "READ" and "already read" in dup["observation"], "Duplicate read must be refused"

# Eval
result = rs.evaluate_run(steps, steps[-1].get("report", ""))
print("\n=== EVAL ===")
for c in result["checks"]:
    print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['name']}")
print(f"Score: {result['score']}/{result['total']}")
assert result["score"] >= 5, "Expected high eval score"

print("\nALL ENGINE TESTS PASSED")