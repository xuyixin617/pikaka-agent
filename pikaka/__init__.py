"""pikaka-agent — a minimal, transparent, local-first Pikaka.

Four pillars, one module each:
  harness  → pikaka/runtime + pikaka/gateway  (scaffolding around the raw LLM)
  loop     → pikaka/loop                      (observe → reason → act → repeat)
             pikaka/graph                     (opt-in structure around the loop — extends this pillar)
  memory   → pikaka/memory                    (procedural / semantic / episodic)
  ops      → pikaka/ops + evals/              (trace → eval → gate → release)
"""

__version__ = "0.1.0"
