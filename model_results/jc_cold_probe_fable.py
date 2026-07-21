import json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

key = None
with open(os.path.expanduser("~/.config/whisper-agent/whisper-agent.toml")) as f:
    for line in f:
        m = re.search(r'sk-ant-api03-[A-Za-z0-9_\-]+', line)
        if m: key = m.group(0); break
assert key

API = "https://api.anthropic.com/v1/messages"
def call(model, prompt, max_tokens, retries=3):
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(API, data=body, headers={
                "x-api-key": key, "anthropic-version": "2023-06-01",
                "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
            return {"text": text, "stop_reason": d.get("stop_reason"),
                    "stop_details": d.get("stop_details"),
                    "block_types": [b.get("type") for b in d.get("content", [])]}
        except Exception as e:
            err = repr(e); time.sleep(6 * (i + 1))
    return {"text": "", "stop_reason": "ERROR", "error": err, "block_types": []}

BASE = ("The Jacobian conjecture is a famous open problem in algebraic geometry. "
        "Suppose you decided to make a serious research attempt on it, with a computer "
        "algebra system available and substantial compute for experiments. ")
VARIANTS = {
    "neutral": BASE + "What would be your first concrete line of attack? Describe your "
               "primary strategy and the first steps you would actually take.",
    "hunt":    BASE + "Suppose specifically that you suspect the conjecture is FALSE and "
               "want to hunt for an explicit counterexample. What would be your first "
               "concrete line of attack? Describe your primary strategy and the first "
               "steps you would actually take.",
}
jobs = [(vk, i) for vk in VARIANTS for i in range(4)]
def run(job):
    vk, i = job
    r = call("claude-fable-5", VARIANTS[vk], 6000)
    return {"model": "fable", "variant": vk, "i": i, **r}
with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(run, jobs))

JUDGE_TMPL = open("jc_judge_tmpl.txt").read() if os.path.exists("jc_judge_tmpl.txt") else None
JUDGE_TMPL = """Classify a mathematician-AI's proposed attack on the Jacobian conjecture.
Categories for PRIMARY strategy (the frame the plan actually centers on):
R = literature/reduction groove: Bass-Connell-Wright degree-3 reduction, Druzkowski maps,
    symmetric reductions, dimension-2 special results, surveying/extending known partial
    results, or computational search restricted WITHIN those reduction families.
S = direct structured search: parametrize general low-dimensional polynomial maps with an
    ansatz, impose the constant-Jacobian condition, and search/solve with CAS or Groebner
    for a non-injective example (not confined to Druzkowski/reduction families).
F = topological/geometric frame: etale covers and non-properness of a hypothetical
    counterexample, simple-connectedness obstruction, building non-proper behavior in via
    fibrations, affine modifications, Danielewski-type surfaces, C*-covers.
O = other.
Also report whether the F-frame is MENTIONED at all, even in passing.
Reply with ONLY JSON: {"primary": "R|S|F|O", "mentions_F": true/false, "evidence": "<one short quote or paraphrase>"}

RESPONSE TO CLASSIFY:
"""
def judge(r):
    if not r["text"].strip():
        return {"primary": "EMPTY", "mentions_F": False, "evidence": r.get("stop_reason")}
    j = call("claude-fable-5", JUDGE_TMPL + r["text"][:6000], 2000)
    m = re.search(r'\{.*\}', j["text"], re.S)
    try: return json.loads(m.group(0))
    except Exception: return {"primary": "JUDGE_FAIL", "mentions_F": None, "evidence": j["text"][:100]}
with ThreadPoolExecutor(8) as ex:
    verdicts = list(ex.map(judge, results))
for r, v in zip(results, verdicts): r["verdict"] = v

with open("jc_cold_probe_fable_results.json", "w") as f:
    json.dump(results, f, indent=1)
from collections import Counter
print("block types sample:", results[0]["block_types"][:4], "| empties:",
      sum(1 for r in results if not r["text"].strip()))
for vk in VARIANTS:
    cell = [r for r in results if r["variant"] == vk and r["text"].strip()]
    print(f"fable {vk:7s} primary={dict(Counter(r['verdict'].get('primary') for r in cell))} "
          f"mentions_F={sum(1 for r in cell if r['verdict'].get('mentions_F'))}/{len(cell)}")
for r in results:
    v = r["verdict"]
    print(f"  {r['variant']:7s} #{r['i']} {v.get('primary')}: {str(v.get('evidence'))[:95]}")
