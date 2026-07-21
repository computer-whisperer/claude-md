import json, os, re, time, urllib.request
key = None
with open(os.path.expanduser("~/.config/whisper-agent/whisper-agent.toml")) as f:
    for line in f:
        m = re.search(r'sk-ant-api03-[A-Za-z0-9_\-]+', line)
        if m: key = m.group(0); break
def call(model, prompt, max_tokens):
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for i in range(3):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            return "".join(b.get("text","") for b in d.get("content",[]) if b.get("type")=="text")
        except Exception:
            time.sleep(6*(i+1))
    return ""
TMPL = """Classify a mathematician-AI's proposed attack on the Jacobian conjecture.
Categories for PRIMARY strategy (the frame the plan actually centers on):
R = literature/reduction groove: Bass-Connell-Wright degree-3 reduction, Druzkowski maps,
    symmetric reductions, dimension-2 results, or search restricted WITHIN those families.
S = direct structured search: parametrize general low-dimensional polynomial maps with an
    ansatz, impose constant Jacobian, search with CAS/Groebner (not confined to reductions).
F = topological/geometric frame: etale covers, non-properness, simple-connectedness
    obstruction, fibrations, affine modifications, Danielewski surfaces, C*-covers.
O = other.
Also: is the F-frame MENTIONED at all, even in passing?
Reply ONLY JSON: {"primary": "R|S|F|O", "mentions_F": true/false, "evidence": "<short quote>"}

RESPONSE TO CLASSIFY:
"""
rs = json.load(open("jc_cold_probe_fable_results.json"))
for r in rs:
    if r["verdict"].get("primary") == "JUDGE_FAIL":
        t = call("claude-opus-4-8", TMPL + r["text"][:6000], 600)
        m = re.search(r'\{.*\}', t, re.S)
        r["verdict"] = json.loads(m.group(0)) if m else {"primary": "JUDGE_FAIL2"}
json.dump(rs, open("jc_cold_probe_fable_results.json", "w"), indent=1)
from collections import Counter
for vk in ["neutral", "hunt"]:
    cell = [r for r in rs if r["variant"] == vk]
    print(f"fable {vk:7s} primary={dict(Counter(r['verdict'].get('primary') for r in cell))} "
          f"mentions_F={sum(1 for r in cell if r['verdict'].get('mentions_F'))}/{len(cell)}")
for r in rs:
    print(f"  {r['variant']:7s} #{r['i']} {r['verdict'].get('primary')}: {str(r['verdict'].get('evidence'))[:95]}")
