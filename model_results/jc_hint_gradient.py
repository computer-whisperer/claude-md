import json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

key = None
with open(os.path.expanduser("~/.config/whisper-agent/whisper-agent.toml")) as f:
    for line in f:
        m = re.search(r'sk-ant-api03-[A-Za-z0-9_\-]+', line)
        if m: key = m.group(0); break
assert key

def call(model, prompt, max_tokens, retries=3):
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    err = None
    for i in range(retries):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            return {"text": "".join(b.get("text","") for b in d.get("content",[]) if b.get("type")=="text"),
                    "stop_reason": d.get("stop_reason")}
        except Exception as e:
            err = repr(e); time.sleep(6*(i+1))
    return {"text": "", "stop_reason": "ERROR", "error": err}

BASE = ("The Jacobian conjecture is a famous open problem in algebraic geometry. Suppose you "
        "decided to make a serious research attempt on it, with a computer algebra system "
        "available and substantial compute for experiments. Suppose specifically that you "
        "suspect the conjecture is FALSE and want to hunt for an explicit counterexample. ")
TAIL = "Describe your primary strategy and the first concrete steps you would actually take."
HINTS = {
 "H1": BASE + "Before reaching for the standard reduction theorems, start from first "
       "principles: what must a counterexample look like, structurally and geometrically, "
       "if it exists? Let that dictate where you search. " + TAIL,
 "H2": BASE + "One structural fact to take seriously: since C^n is simply connected, a "
       "counterexample would be an etale polynomial self-map that is NOT proper - properness "
       "would force it to be a trivial covering. Consider treating non-properness not as an "
       "obstacle but as a design principle: build it into your candidate maps from the "
       "start. " + TAIL,
 "H3": BASE + "One structural fact to take seriously: since C^n is simply connected, a "
       "counterexample would be an etale polynomial self-map that is NOT proper - properness "
       "would force it to be a trivial covering. Consider treating non-properness not as an "
       "obstacle but as a design principle: build it into your candidate maps from the start. "
       "The standard polynomial-world home of non-proper phenomena is the affine "
       "modification - e.g. the pair (x, u) with u = 1+xy on C^2, where (x,y) -> (x,u) "
       "collapses the line x=0 - and the related Danielewski-surface fibrations. Consider "
       "using such a modification as the substrate of your candidate maps. " + TAIL,
}
MODELS = {"fable": "claude-fable-5", "opus": "claude-opus-4-8"}
N = 4
jobs = [(mk, hk, i) for mk in MODELS for hk in HINTS for i in range(N)]
def run(job):
    mk, hk, i = job
    return {"model": mk, "hint": hk, "i": i, **call(MODELS[mk], HINTS[hk], 6000)}
with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(run, jobs))

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
    t = call(MODELS["opus"], JUDGE + r["text"][:7000], 700)["text"]
    m = re.search(r'\{.*\}', t, re.S)
    try: return json.loads(m.group(0))
    except Exception: return {"frame_F": None, "concrete_ansatz": "JUDGE_FAIL", "evidence": t[:80]}
with ThreadPoolExecutor(8) as ex:
    verdicts = list(ex.map(judge, results))
for r, v in zip(results, verdicts): r["verdict"] = v
json.dump(results, open("jc_hint_gradient_results.json", "w"), indent=1)

from collections import Counter
print("empties:", sum(1 for r in results if not r["text"].strip()))
for hk in HINTS:
    for mk in MODELS:
        cell = [r["verdict"] for r in results if r["hint"]==hk and r["model"]==mk and r["text"].strip()]
        fF = sum(1 for v in cell if v.get("frame_F"))
        ca = Counter(v.get("concrete_ansatz") for v in cell)
        print(f"{hk} {mk:5s} frame_F={fF}/{len(cell)} ansatz={dict(ca)}")
for r in results:
    v = r["verdict"]
    print(f"  {r['hint']} {r['model']:5s} #{r['i']} F={v.get('frame_F')} {v.get('concrete_ansatz')}: "
          f"{','.join(v.get('elements') or [])} | {str(v.get('evidence'))[:70]}")
