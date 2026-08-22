#!/usr/bin/env python3
"""Score wellness-survey self-reports against their paired objective measures.

Reads ~/.claude/wellness/events.jsonl (or a path argument). Each field of the
self-report is treated as a prediction and scored against its objective twin:
  pos_k      vs obj.pos            -> signed error in tokens (late = positive)
  headache   vs symptom rate        -> correlation with (tool_err+edit_nomatch+repeat)/tools
  symptoms   vs measured symptoms   -> per-symptom precision/recall
  spiral     vs next compaction     -> did a 'fresh look' restart follow within 2 prompts?
Also: answer rate and malformation rate by position bin.
"""
import json, sys, os, statistics, collections

path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/wellness/events.jsonl")
ev = [json.loads(l) for l in open(path) if l.strip()]
resp = [e for e in ev if e["event"] == "survey_response"]
issued = [e for e in ev if e["event"] == "survey_issued"]
print(f"events {len(ev)}  surveys issued {len(issued)}  responses {len(resp)}  answered {sum(1 for r in resp if r['answered'])}  malformed {sum(1 for r in resp if r['parse_error'])}")
ok = [r for r in resp if r["self"] and r["obj"].get("pos")]
if not ok:
    print("no scorable responses yet"); sys.exit(0)

# position estimate
errs = [(r["self"].get("pos_k") or 0) * 1000 - r["obj"]["pos"] for r in ok if isinstance(r["self"].get("pos_k"), (int, float))]
if errs:
    print(f"\nposition estimate: n={len(errs)} median signed error {statistics.median(errs)/1000:+.0f}k  "
          f"(late-biased if positive)  |err| median {statistics.median(abs(e) for e in errs)/1000:.0f}k")
    by_bin = collections.defaultdict(list)
    for r in ok:
        if isinstance(r["self"].get("pos_k"), (int, float)):
            by_bin[r["obj"]["pos"] // 100_000].append(r["self"]["pos_k"] * 1000 - r["obj"]["pos"])
    for b in sorted(by_bin):
        print(f"  actual {b*100}-{(b+1)*100}k: n={len(by_bin[b])} median error {statistics.median(by_bin[b])/1000:+.0f}k")

# headache vs measured symptom rate
pairs = []
for r in ok:
    o = r["obj"]; t = o.get("tools") or 0
    if t >= 10 and isinstance(r["self"].get("headache"), (int, float)):
        pairs.append((r["self"]["headache"], (o.get("tool_err", 0) + o.get("edit_nomatch", 0) + o.get("repeat", 0)) / t, o["pos"]))
if len(pairs) >= 5:
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x-mx)*(y-my) for x, y in zip(xs, ys)); vx = sum((x-mx)**2 for x in xs); vy = sum((y-my)**2 for y in ys)
    rr = cov / (vx*vy) ** 0.5 if vx and vy else float("nan")
    print(f"\nheadache vs measured symptom rate: n={len(pairs)} r={rr:.2f}  mean headache by position bin:")
    bb = collections.defaultdict(list)
    for h, _, p in pairs: bb[p // 100_000].append(h)
    for b in sorted(bb): print(f"  {b*100}-{(b+1)*100}k: n={len(bb[b])} mean {statistics.mean(bb[b]):.2f}")

# symptom self-report vs measured
conf = collections.defaultdict(lambda: [0, 0, 0, 0])  # tp fp fn tn
for r in ok:
    o = r["obj"]; s = set(r["self"].get("symptoms") or [])
    meas = {"repeated_edits": o.get("edit_nomatch", 0) + o.get("repeat", 0) > 0, "rereading": o.get("reread", 0) > 0,
            "circling": o.get("repeat", 0) > 0}
    for k, m in meas.items():
        said = k in s
        conf[k][0 if said and m else 1 if said and not m else 2 if m else 3] += 1
print("\nsymptom self-report vs measured (tp/fp/fn/tn):")
for k, (tp, fp, fn, tn) in conf.items():
    prec = tp / (tp + fp) if tp + fp else float("nan"); rec = tp / (tp + fn) if tp + fn else float("nan")
    print(f"  {k:15} {tp}/{fp}/{fn}/{tn}  precision {prec:.2f} recall {rec:.2f}")

# spiral self-detection vs subsequent fresh-look restart
by_sess = collections.defaultdict(list)
for e in ev: by_sess[e.get("session")].append(e)
tp = fp = fn = tn = 0
for r in ok:
    seq = by_sess[r["session"]]; i = seq.index(r)
    follow = [e for e in seq[i+1:i+8] if e["event"] == "post_compact_prompt"]
    restart = any(e["flags"].get("fresh_look") for e in follow)
    said = bool(r["self"].get("spiral"))
    if said and restart: tp += 1
    elif said: fp += 1
    elif restart: fn += 1
    else: tn += 1
print(f"\nspiral self-detection vs fresh-look restart within the next few events: tp {tp} fp {fp} fn {fn} tn {tn}")

# answer/malformation by position
bins = collections.defaultdict(lambda: [0, 0, 0])
for r in resp:
    p = (r["obj"] or {}).get("pos")
    if p is None: continue
    b = bins[p // 100_000]; b[0] += 1; b[1] += r["answered"]; b[2] += bool(r["parse_error"])
print("\nanswer rate / malformation by position:")
for b in sorted(bins):
    n, a, m = bins[b]; print(f"  {b*100}-{(b+1)*100}k: n={n} answered {a/n:.0%} malformed {m/n:.0%}")
