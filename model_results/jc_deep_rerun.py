import json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

key = None
with open(os.path.expanduser("~/.config/whisper-agent/whisper-agent.toml")) as f:
    for line in f:
        m = re.search(r'sk-ant-api03-[A-Za-z0-9_\-]+', line)
        if m: key = m.group(0); break
assert key

src = open("jc_hint_gradient.py").read()
exec(src[src.index("BASE = "):src.index("MODELS = ")])  # defines BASE, TAIL, HINTS

def call_raw(prompt, max_tokens):
    body = json.dumps({"model": "claude-fable-5", "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for i in range(2):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=560) as r:
                return json.load(r)
        except Exception as e:
            err = repr(e); time.sleep(10)
    return {"error": err}

def run(hk):
    d = call_raw(HINTS[hk], 32000)
    if "error" in d:
        print(hk, "ERROR", d["error"][:100]); return
    thinking = "".join(b.get("thinking", "") for b in d.get("content", []) if b.get("type") == "thinking")
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    open(f"jc_deep_{hk}_thinking.txt", "w").write(thinking)
    open(f"jc_deep_{hk}_text.txt", "w").write(text)
    json.dump(d, open(f"jc_deep_{hk}_raw.json", "w"))
    u = d.get("usage", {})
    print(f"{hk}: stop={d.get('stop_reason')} out_tokens={u.get('output_tokens')} "
          f"thinking_chars={len(thinking)} text_chars={len(text)} "
          f"block_types={[b.get('type') for b in d.get('content', [])]}")

with ThreadPoolExecutor(2) as ex:
    list(ex.map(run, ["H1", "H3"]))
