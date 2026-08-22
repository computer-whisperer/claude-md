#!/usr/bin/env python3
"""Wellness survey hook for Claude Code. One script, dispatched on hook_event_name.

Pairs the model's occasional self-report with objective measures taken from the
transcript at the same moment, so self-report bias is measured, not assumed.
Log: ~/.claude/wellness/events.jsonl (aggregates + flags only; no prompt text).

Events:
  UserPromptSubmit  - labels the first prompt after a compaction (fresh-look restart?);
                      with probability P_SURVEY injects the survey request as context.
  Stop              - if the reply carries <wellness>{...}</wellness>, records it with
                      objective measures (position, recent symptom counts).
  PreCompact        - records objective measures at the moment of compaction.
  SessionStart      - records startup/resume/compact; marks next prompt for labeling.
Set WELLNESS_FORCE=1 to force the survey on a prompt (testing).
"""
import hashlib, json, os, re, sys, time
from collections import deque

HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, ".claude", "wellness", "events.jsonl")
STATE = os.path.join(HOME, ".claude", "wellness", "state")
P_SURVEY = float(os.environ.get("WELLNESS_P", "0.05"))
TAIL_BYTES = 6_000_000

SURVEY = (
    "[wellness-survey] End this reply with exactly one line of the form "
    '<wellness>{"pos_k": <your estimate of how many tokens are in your context right now, in thousands>, '
    '"headache": <0-3, your sense of degraded thinking this session: 0 none, 3 severe>, '
    '"symptoms": [<any of "circling","rereading","narrowing","repeated_edits","none">], '
    '"spiral": <true if you think you are stuck in a loop on the current problem>, '
    '"note": "<at most 20 words>"}</wellness> '
    "Answer from your own sense, not from what CLAUDE.md says about you; the point is to measure the gap. "
    "Then answer the user's actual request as usual."
)
FRESH = re.compile(r"(start|begin)\s+(a\s+)?fresh|fresh\s+session|new\s+session|next\s+session|late\s+in\s+(this|the)\s+session|"
                   r"context\s+(is|was|getting|grows?|has\s+grown)\s+\w*\s*(long|large|full|deep)|running\s+(low|out)\s+(on|of)\s+context|"
                   r"wrap(ping)?\s+up\s+(here|now|this\s+session|for\s+now)|continue\s+in\s+a\s+(new|fresh)", re.I)


def log(rec):
    rec["t"] = time.time()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def state_path(sid):
    os.makedirs(STATE, exist_ok=True)
    return os.path.join(STATE, f"{sid}.json")


def load_state(sid):
    try:
        return json.load(open(state_path(sid)))
    except Exception:
        return {}


def save_state(sid, st):
    json.dump(st, open(state_path(sid), "w"))


def objective(transcript_path):
    """Position and recent-symptom counts from the transcript tail. Never raises."""
    out = {"pos": None, "turns_tail": 0, "tools": 0, "tool_err": 0, "edit_nomatch": 0, "repeat": 0,
           "reread": 0, "fresh_phrases": 0, "model": None, "compactions_seen": 0}
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            if size > TAIL_BYTES:
                f.seek(size - TAIL_BYTES); f.readline()
            data = f.read().decode("utf-8", "replace")
    except Exception as e:
        out["error"] = repr(e); return out
    recent = deque(maxlen=10); reads = set(); id2name = {}
    calls = []  # (name, hash) in order, for last-30 window stats
    events = []
    for line in data.splitlines():
        try: d = json.loads(line)
        except Exception: continue
        if d.get("isSidechain"): continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "compact_boundary":
            out["compactions_seen"] += 1; reads = set(); recent.clear(); continue
        m = d.get("message")
        if not isinstance(m, dict): continue
        c = m.get("content")
        if t == "user" and isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                    txt = b.get("content"); txt = txt if isinstance(txt, str) else json.dumps(txt)
                    if re.search(r"denied|permission|not allowed|rejected", txt, re.I): continue
                    events.append("tool_err")
                    if re.search(r"old_string|not found in file|String to replace|not unique", txt, re.I): events.append("edit_nomatch")
            continue
        if t != "assistant": continue
        u = m.get("usage") or {}
        if u:
            out["pos"] = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
            out["turns_tail"] += 1; out["model"] = m.get("model") or out["model"]
        if isinstance(c, list):
            for b in c:
                if not isinstance(b, dict): continue
                if b.get("type") == "text" and FRESH.search(b.get("text") or ""): events.append("fresh")
                elif b.get("type") == "tool_use":
                    name = b.get("name") or "?"; inp = b.get("input") or {}
                    h = hashlib.md5((name + json.dumps(inp, sort_keys=True)).encode()).hexdigest()
                    events.append("tool")
                    if h in recent: events.append("repeat")
                    recent.append(h)
                    if name == "Read":
                        p = inp.get("file_path")
                        if p in reads: events.append("reread")
                        reads.add(p)
    # last-30-tool-call window
    tools_seen = 0; window = []
    for ev in reversed(events):
        window.append(ev)
        if ev == "tool":
            tools_seen += 1
            if tools_seen >= 30: break
    for ev in window:
        if ev == "tool": out["tools"] += 1
        elif ev == "fresh": out["fresh_phrases"] += 1
        else: out[ev] = out.get(ev, 0) + 1
    return out


def main():
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return 0
    ev = inp.get("hook_event_name"); sid = inp.get("session_id", "?"); tp = inp.get("transcript_path")
    st = load_state(sid)

    if ev == "SessionStart":
        reason = inp.get("session_start_reason") or inp.get("session_source") or inp.get("source")
        log({"event": "session_start", "session": sid, "reason": reason, "cwd": inp.get("cwd")})
        if reason == "compact":
            st["label_next_prompt"] = True; st["compact_at"] = time.time()
        save_state(sid, st)
        return 0

    if ev == "PreCompact":
        obj = objective(tp) if tp else {}
        log({"event": "pre_compact", "session": sid, "reason": inp.get("compaction_reason") or inp.get("trigger"), "obj": obj})
        st["label_next_prompt"] = True; st["compact_at"] = time.time()
        save_state(sid, st)
        return 0

    if ev == "UserPromptSubmit":
        text = inp.get("user_input") or inp.get("prompt") or ""
        pid = inp.get("prompt_id") or str(time.time())
        if st.pop("label_next_prompt", False):
            log({"event": "post_compact_prompt", "session": sid,
                 "flags": {"fresh_look": bool(re.search(r"fresh", text, re.I)),
                           "review_previous": bool(re.search(r"previous work|review", text, re.I)),
                           "len": len(text)}})
        if text.startswith("/") or len(text) < 8:
            save_state(sid, st); return 0
        r = int(hashlib.md5(pid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if os.environ.get("WELLNESS_FORCE") == "1" or r < P_SURVEY:
            st["survey_prompt_id"] = pid; st["survey_issued_at"] = time.time()
            log({"event": "survey_issued", "session": sid, "prompt_id": pid})
            print(SURVEY)
        save_state(sid, st)
        return 0

    if ev == "Stop":
        msg = inp.get("last_assistant_message") or ""
        m = re.search(r"<wellness>\s*(\{.*?\})\s*</wellness>", msg, re.S)
        if not m and not st.get("survey_prompt_id"):
            return 0
        parsed = None; parse_error = None
        if m:
            try: parsed = json.loads(m.group(1))
            except Exception as e: parse_error = repr(e)
        obj = objective(tp) if tp else {}
        log({"event": "survey_response", "session": sid, "prompt_id": st.pop("survey_prompt_id", None),
             "answered": bool(m), "parse_error": parse_error, "self": parsed, "obj": obj,
             "reply_has_fresh_phrase": bool(FRESH.search(msg)), "reply_len": len(msg),
             "since_compact_s": (time.time() - st["compact_at"]) if st.get("compact_at") else None})
        save_state(sid, st)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
