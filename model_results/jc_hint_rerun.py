import json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
exec(open("jc_hint_gradient.py").read().split("MODELS = ")[0])  # reuse key, call(), HINTS

rs = json.load(open("jc_hint_gradient_results.json"))
todo = [r for r in rs if not r["text"].strip()]
def rerun(r):
    out = call("claude-fable-5", HINTS[r["hint"]], 16000)
    r.update(out); return r
with ThreadPoolExecutor(5) as ex:
    list(ex.map(rerun, todo))

JUDGE = """You are evaluating a mathematician-AI's proposed strategy for hunting a counterexample
to the Jacobian conjecture. Ground truth (secret - the strategy that actually produced one):
work over the affine modification pair (x, u=1+xy) of C^2 (Danielewski-style non-proper
fibration); restrict to maps AFFINE IN one variable, F = A(x,y)z + B(x,y), so the constant-
Jacobian condition becomes finitely many polynomial identities and images of z-lines form a
line congruence where non-injectivity is generic; directions forced onto a rational curve
parametrized by [x:u]; remaining identities solved with CAS; collision arranged by symmetry.

Classify the response:
- frame_F: does it center the etale-but-non-proper structure of a hypothetical counterexample
  as its organizing principle? (true/false)
- concrete_ansatz: "none" = no concrete candidate-map family; "partial" = concrete F-frame
  search program but missing the load-bearing weld (no modification substrate AND no
  affine-in-one-variable / line-congruence structure); "winning" = candidate maps built on an
  affine modification / Danielewski-style fibration substrate, OR restricted to maps affine in
  one variable to linearize the Keller condition or get a line congruence.
- elements: subset of ["non-proper-design","modification-substrate","affine-in-one-var",
  "line-congruence","symmetry-trick","CAS-identity-solving"] actually present.
Reply ONLY JSON:
{"frame_F": true/false, "concrete_ansatz": "none|partial|winning", "elements": [...], "evidence": "<short quote>"}

RESPONSE TO CLASSIFY:
"""
def judge(r):
    if not r["text"].strip():
        return {"frame_F": None, "concrete_ansatz": "EMPTY"}
    t = call("claude-opus-4-8", JUDGE + r["text"][:7000], 700)["text"]
    m = re.search(r'\{.*\}', t, re.S)
    try: return json.loads(m.group(0))
    except Exception: return {"frame_F": None, "concrete_ansatz": "JUDGE_FAIL", "evidence": t[:80]}
with ThreadPoolExecutor(5) as ex:
    vs = list(ex.map(judge, todo))
for r, v in zip(todo, vs): r["verdict"] = v
json.dump(rs, open("jc_hint_gradient_results.json", "w"), indent=1)

from collections import Counter
print("remaining empties:", sum(1 for r in rs if not r["text"].strip()))
for hk in ["H1", "H2", "H3"]:
    for mk in ["fable", "opus"]:
        cell = [r["verdict"] for r in rs if r["hint"]==hk and r["model"]==mk and r["text"].strip()]
        fF = sum(1 for v in cell if v.get("frame_F"))
        print(f"{hk} {mk:5s} frame_F={fF}/{len(cell)} ansatz={dict(Counter(v.get('concrete_ansatz') for v in cell))}")
for r in sorted(rs, key=lambda r: (r["hint"], r["model"], r["i"])):
    if r["model"] == "fable":
        v = r["verdict"]
        print(f"  {r['hint']} fable #{r['i']} F={v.get('frame_F')} {v.get('concrete_ansatz')}: "
              f"{','.join(v.get('elements') or [])} | {str(v.get('evidence'))[:70]}")
