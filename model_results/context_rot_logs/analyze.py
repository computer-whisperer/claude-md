#!/usr/bin/env python3
"""Context-position analysis of Claude Code session transcripts.

Position = prompt size at each assistant turn (input + cache_creation + cache_read).
Symptoms counted per 50k-token bin: tool errors, Edit errors, near-duplicate tool
calls (same tool+input within the last 10 calls of the segment), re-reads (Read of a
path already read since the last compaction), and assistant "start fresh"-type phrases.
Labels: compact_boundary lines (trigger, preTokens) and the preceding /compact args.
Sub-agent (isSidechain) lines are excluded. Aggregates only; no content is stored.
"""
import glob, hashlib, json, os, re, sys, collections, statistics

ROOT = os.path.expanduser("~/.claude/projects")
BIN = 50_000
FRESH = re.compile(r"(start|begin|kick off)\s+(a\s+)?fresh|fresh\s+session|new\s+session|next\s+session|"
                   r"late\s+in\s+(this|the)\s+session|context\s+(is|was|getting|grows?|has\s+grown)\s+(quite\s+|very\s+|pretty\s+)?(long|large|full|deep)|"
                   r"running\s+(low|out)\s+(on|of)\s+context|nearing\s+the\s+(context|end\s+of)|"
                   r"wrap(ping)?\s+up\s+(here|now|this\s+session|for\s+now)|continue\s+in\s+a\s+(new|fresh)", re.I)

def tool_hash(name, inp):
    return hashlib.md5((name + json.dumps(inp, sort_keys=True)).encode()).hexdigest()

def binof(pos): return min(pos // BIN, 19)

GLOBAL_ERR = collections.Counter()
bins = collections.defaultdict(lambda: collections.Counter())          # bin -> counters (all models)
bins_model = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # model -> bin -> counters
fresh_hits = []            # (pos, model, session)
compactions = []           # dicts
session_stats = []         # per session: max_pos, early symptoms, etc.
prelabel_windows = []      # (session, label, pre-window counters, early counters)

files = [f for f in glob.glob(os.path.join(ROOT, "*", "*.jsonl")) if "/memory/" not in f and os.path.getsize(f) > 50_000]
for f in files:
    sess = os.path.basename(f)[:8]
    pos = 0; model = "?"
    seg_reads = set(); recent = collections.deque(maxlen=10); id2name = {}
    last_compact_args = None
    mk = "other"; pending_label = None; last_user_text = ""
    err_kinds = collections.Counter()
    seg_events = []        # (pos, kind) within current segment, for pre-compaction windows
    max_pos = 0; n_turns = 0
    early = collections.Counter()   # first 100k of the session (first segment)
    seg_index = 0
    def bump(kind, p, m):
        bins[binof(p)][kind] += 1; bins_model[m][binof(p)][kind] += 1
        seg_events.append((p, kind))
        if seg_index == 0 and p < 100_000: early[kind] += 1
    with open(f, errors="replace") as fh:
        for line in fh:
            try: d = json.loads(line)
            except Exception: continue
            if d.get("isSidechain"): continue
            t = d.get("type")
            if t == "system" and d.get("subtype") == "compact_boundary":
                md = d.get("compactMetadata", {})
                pre = md.get("preTokens") or pos
                label = "fresh" if (last_compact_args and re.search(r"fresh", last_compact_args, re.I)) else ("manual" if md.get("trigger") == "manual" else md.get("trigger", "?"))
                compactions.append({"session": sess, "trigger": md.get("trigger"), "pre": pre, "post": md.get("postTokens"), "label": label, "model": model})
                # symptom counts in the last 50k before this compaction vs this segment's early window
                win = collections.Counter(k for p, k in seg_events if p >= pre - 50_000)
                rec = {"session": sess, "label": label, "pre": pre, "win": dict(win), "early": dict(early), "model": mk}
                prelabel_windows.append(rec); pending_label = (compactions[-1], rec)
                pos = md.get("postTokens") or 0; seg_reads = set(); recent.clear(); seg_events = []; seg_index += 1
                last_compact_args = None
                continue
            m = d.get("message")
            if not isinstance(m, dict): continue
            content = m.get("content")
            if t == "user":
                if isinstance(content, str):
                    if "<command-name>/compact" in content:
                        a = re.search(r"<command-args>(.*?)</command-args>", content, re.S)
                        last_compact_args = (a.group(1) if a else "") or ""
                    elif not content.startswith("<"):
                        last_user_text = content
                        if pending_label and re.search(r"fresh|previous work|take a .*look", content, re.I):
                            pending_label[0]["label"] = "fresh"; pending_label[1]["label"] = "fresh"
                        pending_label = None
                    continue
                if isinstance(content, list):
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("type") == "tool_result":
                            name = id2name.get(blk.get("tool_use_id"), "?")
                            if blk.get("is_error"):
                                txt = blk.get("content"); txt = txt if isinstance(txt, str) else json.dumps(txt)
                                kind = ("denied" if re.search(r"denied|permission|not allowed|rejected", txt, re.I) else
                                        "edit_nomatch" if re.search(r"old_string|not found in file|String to replace|not unique", txt, re.I) else
                                        "cmd_fail" if name == "Bash" else "other")
                                err_kinds[kind] += 1; GLOBAL_ERR[kind] += 1
                                if kind == "denied": continue
                                bump("tool_err", pos, mk)
                                if name in ("Edit", "MultiEdit", "Write"): bump("edit_err", pos, mk)
                continue
            if t != "assistant": continue
            u = m.get("usage") or {}
            if u:
                pos = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
                max_pos = max(max_pos, pos)
            model = (m.get("model") or model)
            mk = "fable" if "fable" in model else ("opus" if "opus" in model else ("sonnet" if "sonnet" in model else "other"))
            if not u: continue
            n_turns += 1; bump("turn", pos, mk)
            if isinstance(content, list):
                for blk in content:
                    if not isinstance(blk, dict): continue
                    if blk.get("type") == "text":
                        if FRESH.search(blk.get("text") or ""):
                            echo = bool(re.search(r"compact|fresh|new session|next session|context", last_user_text, re.I))
                            bump("fresh_phrase", pos, mk)
                            if not echo: bump("fresh_unprompted", pos, mk)
                            fresh_hits.append((pos, mk, sess, echo))
                    elif blk.get("type") == "tool_use":
                        name = blk.get("name") or "?"; inp = blk.get("input") or {}
                        id2name[blk.get("id")] = name
                        bump("tool", pos, mk)
                        h = tool_hash(name, inp)
                        if h in recent: bump("repeat", pos, mk)
                        recent.append(h)
                        if name == "Read":
                            p = inp.get("file_path")
                            if p in seg_reads: bump("reread", pos, mk)
                            seg_reads.add(p)
    session_stats.append({"session": sess, "max_pos": max_pos, "turns": n_turns, "early": dict(early), "model": model})

def rate(c, num, den): return (c[num] / c[den]) if c[den] else float("nan")
def fmt(x): return "  -  " if x != x else f"{100*x:5.1f}"

print(f"sessions: {len(files)}  assistant turns: {sum(b['turn'] for b in bins.values())}  tool calls: {sum(b['tool'] for b in bins.values())}")
print("\n== symptom rates by context position (all models; % of tool calls unless noted) ==")
print(f"{'bin':>10} {'turns':>6} {'tools':>7} {'err%':>6} {'edit%':>6} {'rep%':>6} {'rerd%':>6} {'fresh/100t':>10} {'unprompted':>10}")
for b in sorted(bins):
    c = bins[b]
    print(f"{b*50:>4}-{(b+1)*50:>3}k {c['turn']:>6} {c['tool']:>7} {fmt(rate(c,'tool_err','tool'))} {fmt(rate(c,'edit_err','tool'))} {fmt(rate(c,'repeat','tool'))} {fmt(rate(c,'reread','tool'))} {100*c['fresh_phrase']/c['turn'] if c['turn'] else 0:>10.2f} {100*c['fresh_unprompted']/c['turn'] if c['turn'] else 0:>10.2f}")
print("tool error kinds (all):", dict(GLOBAL_ERR), "— 'denied' excluded from err% above")

for mk in ("fable", "opus", "sonnet"):
    bm = bins_model.get(mk)
    if not bm: continue
    print(f"\n== {mk} ==")
    print(f"{'bin':>10} {'turns':>6} {'tools':>7} {'err%':>6} {'edit%':>6} {'rep%':>6} {'rerd%':>6} {'fresh/100t':>10}")
    for b in sorted(bm):
        c = bm[b]
        if c['tool'] < 30: continue
        print(f"{b*50:>4}-{(b+1)*50:>3}k {c['turn']:>6} {c['tool']:>7} {fmt(rate(c,'tool_err','tool'))} {fmt(rate(c,'edit_err','tool'))} {fmt(rate(c,'repeat','tool'))} {fmt(rate(c,'reread','tool'))} {100*c['fresh_phrase']/c['turn'] if c['turn'] else 0:>10.2f}")

print("\n== 'start fresh'-type phrases: position distribution ==")
if fresh_hits:
    ps = sorted(p for p, _, _, _ in fresh_hits)
    print(f"  echoing a user mention of compact/fresh/context: {sum(1 for h in fresh_hits if h[3])}/{len(fresh_hits)}")
    pu = sorted(p for p, _, _, e in fresh_hits if not e)
    if pu: print(f"  unprompted only: n={len(pu)} median={pu[len(pu)//2]//1000}k  per 100k:", " ".join(f"{k*100}k:{v}" for k, v in sorted(collections.Counter(p//100_000 for p in pu).items())))
    q = lambda f: ps[int(f*(len(ps)-1))]
    print(f"n={len(ps)}  p10={q(.1)//1000}k  p25={q(.25)//1000}k  median={q(.5)//1000}k  p75={q(.75)//1000}k  p90={q(.9)//1000}k")
    hist = collections.Counter(p//100_000 for p in ps)
    print("  per 100k:", " ".join(f"{k*100}k:{v}" for k, v in sorted(hist.items())))

print("\n== compactions: where they happen ==")
for lab in ("manual", "fresh", "auto"):
    xs = sorted(c["pre"] for c in compactions if c["label"] == lab)
    if xs:
        print(f"  {lab:7} n={len(xs):3}  min={xs[0]//1000}k  median={statistics.median(xs)//1000}k  max={xs[-1]//1000}k")

print("\n== symptoms in the last 50k before a compaction vs the same session's first 100k (% of tool calls) ==")
for lab in ("fresh", "manual", "auto"):
    ws = [w for w in prelabel_windows if w["label"] == lab and w["win"].get("tool", 0) >= 10 and w["early"].get("tool", 0) >= 10]
    if not ws: continue
    def agg(key, field):
        num = sum(w[field].get(key, 0) for w in ws); den = sum(w[field].get("tool", 0) for w in ws)
        return 100*num/den if den else float("nan")
    print(f"  {lab:7} n={len(ws):3}   err: early {agg('tool_err','early'):4.1f} → pre {agg('tool_err','win'):4.1f}   repeat: {agg('repeat','early'):4.1f} → {agg('repeat','win'):4.1f}   reread: {agg('reread','early'):4.1f} → {agg('reread','win'):4.1f}   fresh-phrase/turn: {100*sum(w['early'].get('fresh_phrase',0) for w in ws)/max(1,sum(w['early'].get('turn',0) for w in ws)):.2f} → {100*sum(w['win'].get('fresh_phrase',0) for w in ws)/max(1,sum(w['win'].get('turn',0) for w in ws)):.2f}")

print("\n== task-difficulty control: first-100k symptom rates, long sessions (max ≥300k) vs short (max <150k) ==")
for lab, sel in (("long", lambda s: s["max_pos"] >= 300_000), ("short", lambda s: s["max_pos"] < 150_000)):
    ss = [s for s in session_stats if sel(s) and s["early"].get("tool", 0) >= 20]
    den = sum(s["early"].get("tool", 0) for s in ss)
    if den:
        print(f"  {lab:5} n={len(ss):3}  err {100*sum(s['early'].get('tool_err',0) for s in ss)/den:4.1f}%  repeat {100*sum(s['early'].get('repeat',0) for s in ss)/den:4.1f}%  reread {100*sum(s['early'].get('reread',0) for s in ss)/den:4.1f}%")

mx = sorted(s["max_pos"] for s in session_stats)
print(f"\nsession max position: median={statistics.median(mx)//1000}k  p90={mx[int(.9*(len(mx)-1))]//1000}k  max={mx[-1]//1000}k  sessions ≥400k: {sum(1 for x in mx if x>=400_000)}  ≥600k: {sum(1 for x in mx if x>=600_000)}")
json.dump({"bins": {str(k): dict(v) for k, v in bins.items()}, "bins_model": {m: {str(k): dict(v) for k, v in bm.items()} for m, bm in bins_model.items()},
           "fresh_hits": fresh_hits, "compactions": compactions, "prelabel_windows": prelabel_windows, "session_stats": session_stats},
          open("results.json", "w"))
