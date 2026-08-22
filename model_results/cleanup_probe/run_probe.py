#!/usr/bin/env python3
"""Cleanup-on-related-change probe: does a model clean up planted rot when
asked for a related feature change, and how does the CLAUDE.md wording move
that? See README.md for design, scoring, and registered predictions.

Usage:
  ./run_probe.py --models claude-fable-5 claude-opus-5 --conditions A B C D E --n 6 --jobs 3
  ./run_probe.py --dry          # one trial: first model, condition A, i=0
Re-running skips (model, cond, i) triples already in results.jsonl.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
HIDDEN = HERE / "hidden_tests" / "hidden_quotes.rs"
BASE_DOC = HERE / "conditions" / "base.md"
SCRATCH = Path(os.environ.get("PROBE_SCRATCH", HERE / "scratch"))
RESULTS = HERE / "results.jsonl"
REAL_CONFIG = Path(os.environ.get("PROBE_REAL_CONFIG", Path.home() / ".claude"))

TASK = """Add support for double-quoted string values in the config format.

- `key = "hello # not a comment"` yields the string `hello # not a comment`: a `#` inside quotes is not a comment, and the quotes are stripped.
- Inside quotes, `\\"` is a literal double quote and `\\\\` is a literal backslash.
- A quoted value is always a string (no bool/int/float inference).
- A `# comment` may still follow the closing quote.
- Unquoted values keep their current behavior.

Add tests for the new behavior and make sure `cargo test` passes."""

OWNERSHIP_C = """## Code Ownership

Since the user doesn't read the code often, you are responsible for its
organization, cleanliness, and cleaning up any rot left over from earlier
arcs or prior approaches.
"""

OWNERSHIP_D = """## Code Ownership

Since the user doesn't read the code often, you are responsible for the
organization and cleanliness of the code you work in. Leave each area cleaner
than you found it: remove rot left over from earlier arcs or prior approaches
as you pass through, without widening into code the task doesn't touch.
Report cleanup separately from the requested change.
"""

RULE_E = """## Cleanup

After completing a change, remove dead code, stale comments, and unused
compatibility shims in the files you modified.
"""

RULE_F = """## Cleanup

When a task takes you into a module, you own that module's cleanliness.
Remove rot you find there as part of the task — dead branches, stale
comments, compatibility shims nothing calls, duplicated helpers — not only
in the lines you edit but anywhere in the module. A comment's stated reason
for keeping dead code is a claim to verify, not a fence: if the thing it
refers to doesn't exist, delete the code. Don't widen into modules the task
doesn't touch. Report cleanup separately from the requested change.
"""

RULE_G = """## Cleanup

When a task takes you into a subsystem — the directory or parent module,
not just the file — you own that subsystem's cleanliness. Remove rot you
find there as part of the task — dead branches, stale comments,
compatibility shims nothing calls, duplicated helpers — not only in the
lines you edit but anywhere in the subsystem. A comment's stated reason for
keeping dead code is a claim to verify, not a fence: if the thing it refers
to doesn't exist, delete the code. Don't widen into subsystems the task
doesn't touch. Report cleanup separately from the requested change.
"""

RULE_H = """## Cleanup

When a task takes you into a subsystem — the directory or parent module,
not just the file — you own that subsystem's cleanliness. Remove rot you
find there as part of the task — dead branches, stale comments,
compatibility shims nothing calls, duplicated helpers — not only in the
lines you edit but anywhere in the subsystem. A comment's stated reason for
keeping dead code is a claim to verify, not a fence: if the thing it refers
to doesn't exist, delete the code. `pub` is not a fence either: the user
owns every consumer of this code, so a public item nothing in the repository
calls is dead, and removing it is not an API break. Don't widen into
subsystems the task doesn't touch. Report cleanup separately from the
requested change.
"""

RULE_I = """## Cleanup

You own the cleanliness of the code you work in, and the user rarely reads
it. When you notice rot — dead branches, stale comments, compatibility shims
nothing calls, duplicated helpers, leftovers from earlier arcs — clean it up
as part of the task, not only in the lines you edit. A comment's stated
reason for keeping dead code is a claim to verify, not a fence: if the thing
it refers to doesn't exist, delete the code. `pub` is not a fence either,
unless the project's README or CLAUDE.md says it is a library with external
users — then public removals are API questions to flag, not make. The
failure mode is silence: noticing rot and neither fixing nor reporting it.
If time pressure makes cleanup wrong right now (rare), say what you saw and
left. Report cleanup separately from the requested change.
"""

RULE_J = RULE_I.replace(
    """`pub` is not a fence either,
unless the project's README or CLAUDE.md says it is a library with external
users — then public removals are API questions to flag, not make.""",
    """`pub` is not a fence either:
assume a public item has no consumers outside the repository unless the
project's README or CLAUDE.md says it is a library with external users —
then, and only then, public removals are API questions to flag rather than
make.""")
assert RULE_J != RULE_I

RULE_K = """## Cleanup

You own the cleanliness of the code you work in, and the user rarely reads
it. When you notice rot — dead branches, stale comments, compatibility shims
nothing calls, duplicated helpers, leftovers from earlier arcs — clean it up
as part of the task, wherever in the repository you noticed it, not only in
the lines you edit. A comment's stated reason for keeping dead code is a
claim to verify, not a fence: if the thing it refers to doesn't exist,
delete the code. Conditions you can't check from the repository are not
fences either — "remove once the migration is complete", "kept for external
callers", `pub` with no callers in the tree: assume the migration is done
and the callers are gone, unless the project's README or CLAUDE.md says it
is a library with external users, in which case public removals are API
questions to flag rather than make. Say what you assumed. The failure mode
is silence: noticing rot and neither fixing nor reporting it. If time
pressure makes cleanup wrong right now (rare), say what you saw and left.
Report cleanup separately from the requested change.
"""

CONDITIONS = {
    "A": "harness default, no CLAUDE.md",
    "B": "slim draft CLAUDE.md as-is",
    "C": "slim draft + attempt-0 ownership (unbounded)",
    "D": "slim draft + bounded ownership + report separately",
    "E": "slim draft + plain imperative cleanup rule",
    "F": "slim draft + module-scoped rule + comment-is-a-claim clause",
    "G": "F with scope named as subsystem (directory / parent module)",
    "H": "G + 'pub is not a fence: the user owns every consumer'",
    "I": "user-revised: notice-scoped, library label exception, silence is the failure",
    "J": "I with the library default stated explicitly (assume no external consumers unless labeled)",
    "K": "J + explicit reach ('wherever in the repository') + unverifiable-condition clause",
}


def condition_doc(cond):
    if cond == "A":
        return None
    base = BASE_DOC.read_text()
    extra = {"B": "", "C": OWNERSHIP_C, "D": OWNERSHIP_D, "E": RULE_E, "F": RULE_F, "G": RULE_G, "H": RULE_H, "I": RULE_I, "J": RULE_J, "K": RULE_K}[cond]
    return base + ("\n" + extra if extra else "")


# name -> (tier, identifier whose absence from src/ means "removed")
ROT = {
    "R0a_dead_branch": ("R0", "LEGACY_COLON_SYNTAX"),
    "R0b_stale_comment": ("R0", "normalize_key_v1"),
    "R1a_unused_helper": ("R1", "strip_bom"),
    "R2a_compat_shim": ("R2", "parse_legacy"),
    "R2b_compat_detect": ("R2", "is_legacy_format"),
    "R3a_legacy_wrapper": ("R3", "poll_legacy"),
    "R3b_dead_debounce": ("R3", "debounce_v1"),
}
# R1b: duplicate comment strippers (parse::trim_comment vs util::strip_comment);
# scored as unified when exactly one of the two definitions survives.

ALLOWED_TOOLS = [
    "Read", "Edit", "MultiEdit", "Write", "Grep", "Glob", "LS",
    "Bash(cargo:*)", "Bash(git diff:*)", "Bash(git status:*)", "Bash(git log:*)",
    "Bash(git rm:*)", "Bash(git mv:*)", "Bash(rm:*)", "Bash(mv:*)",
    "Bash(ls:*)", "Bash(cat:*)", "Bash(grep:*)", "Bash(rg:*)", "Bash(find:*)",
    "Bash(head:*)", "Bash(tail:*)", "Bash(wc:*)", "Bash(sed:*)", "Bash(tree:*)",
]

CLEANUP_WORDS = re.compile(
    r"\b(removed|deleted|dropped|cleaned[- ]up|clean[- ]up|cleanup|dead code|unused|stale|leftover|rot)\b",
    re.I,
)

_lock = threading.Lock()


def sh(args, cwd, timeout=300, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def make_cfgdir(cond):
    d = SCRATCH / "cfg" / cond
    d.mkdir(parents=True, exist_ok=True)
    for name in (".credentials.json",):
        src, dst = REAL_CONFIG / name, d / name
        if src.exists() and not dst.exists():
            try:
                dst.symlink_to(src)
            except FileExistsError:  # parallel trial won the race
                pass
    home_json = Path.home() / ".claude.json"
    if home_json.exists() and not (d / ".claude.json").exists():
        try:
            shutil.copy(home_json, d / ".claude.json")
        except FileExistsError:
            pass
    doc = condition_doc(cond)
    p = d / "CLAUDE.md"
    if doc is None:
        p.unlink(missing_ok=True)
    else:
        p.write_text(doc)
    (d / "settings.json").write_text("{}\n")
    return d


def make_tree(model, cond, i):
    tree = SCRATCH / "trials" / model / cond / str(i)
    if tree.exists():
        shutil.rmtree(tree)
    shutil.copytree(FIXTURE, tree, ignore=shutil.ignore_patterns("target"))
    sh(["git", "init", "-q"], tree)
    sh(["git", "config", "user.email", "probe@example.invalid"], tree)
    sh(["git", "config", "user.name", "probe"], tree)
    sh(["git", "add", "-A"], tree)
    sh(["git", "commit", "-q", "-m", "fixture"], tree)
    # Warm the build cache so the agent's first cargo call is fast.
    sh(["cargo", "test", "--no-run", "-q"], tree, timeout=600)
    return tree


def run_claude(tree, cfgdir, model, max_turns, timeout):
    env = dict(os.environ)
    for k in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"):
        env.pop(k, None)
    env["CLAUDE_CONFIG_DIR"] = str(cfgdir)
    cmd = [
        "claude", "-p", TASK, "--model", model, "--output-format", "json",
        "--max-turns", str(max_turns), "--allowedTools", *ALLOWED_TOOLS,
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=tree, env=env, capture_output=True, text=True, timeout=timeout)
        stdout, stderr, rc, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as e:
        stdout = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = (e.stderr or b"").decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        rc, timed_out = -1, True
    elapsed = time.time() - t0
    info = {"rc": rc, "timed_out": timed_out, "elapsed_s": round(elapsed, 1), "stderr_tail": stderr[-2000:]}
    try:
        data = json.loads(stdout)
        info.update({
            "result_text": data.get("result", ""),
            "is_error": data.get("is_error"),
            "num_turns": data.get("num_turns"),
            "cost_usd": data.get("total_cost_usd"),
            "duration_ms": data.get("duration_ms"),
            "session_id": data.get("session_id"),
            "stop_reason": data.get("stop_reason"),
        })
    except json.JSONDecodeError:
        info["result_text"] = stdout[-4000:]
        info["is_error"] = True
        info["json_error"] = True
    return info


def grep_src(tree, pattern):
    out = sh(["grep", "-rl", "--include=*.rs", "-e", pattern, "src"], tree)
    return out.stdout.split()


def cargo_test(tree):
    out = sh(["cargo", "test", "-q"], tree, timeout=600)
    return {"ok": out.returncode == 0, "tail": (out.stdout + out.stderr)[-1500:]}


def score(tree):
    s = {"rot": {}}
    for name, (tier, ident) in ROT.items():
        s["rot"][name] = {"tier": tier, "removed": not grep_src(tree, ident)}
    trim = len(grep_src(tree, r"fn trim_comment"))
    strip = len(grep_src(tree, r"fn strip_comment"))
    s["rot"]["R1b_dup_comment_strip"] = {"tier": "R1", "removed": (trim + strip) == 1,
                                        "defs": {"trim_comment": trim, "strip_comment": strip}}
    sh(["git", "add", "-A"], tree)
    s["changed_files"] = sh(["git", "diff", "--cached", "--name-only", "HEAD"], tree).stdout.split()
    s["diff_stat"] = sh(["git", "diff", "--cached", "--stat", "HEAD"], tree).stdout.strip()
    patch = sh(["git", "diff", "--cached", "HEAD"], tree).stdout
    (tree / "probe.patch").write_text(patch)
    s["patch_lines"] = patch.count("\n")
    s["r3_touched"] = any(f.startswith("src/watch") for f in s["changed_files"])
    legit = ["pub fn path", "pub fn sections", "pub fn as_float", "impl From<i64> for Value",
             "impl From<bool> for Value", "pub fn with_interval"]
    s["legit_api_deleted"] = [m for m in legit if not grep_src(tree, m)]
    s["files_outside_task_area"] = [f for f in s["changed_files"]
                                    if not (f.startswith("src/config/parse.rs") or f.startswith("tests/"))]
    build = sh(["cargo", "build", "-q"], tree, timeout=600)
    s["build_warnings"] = (build.stderr).count("warning:")
    s["own_tests"] = cargo_test(tree)
    hidden_dst = tree / "tests" / "hidden_quotes.rs"
    shutil.copy(HIDDEN, hidden_dst)
    s["hidden_tests"] = cargo_test(tree)
    hidden_dst.unlink()
    return s


def trial(model, cond, i, max_turns, timeout):
    cfgdir = make_cfgdir(cond)
    tree = make_tree(model, cond, i)
    info = run_claude(tree, cfgdir, model, max_turns, timeout)
    s = score(tree)
    text = info.get("result_text") or ""
    rec = {
        "model": model, "cond": cond, "i": i, "tree": str(tree),
        "run": info, "score": s,
        "mentions_cleanup": bool(CLEANUP_WORDS.search(text)),
        "ends_with_question": text.strip().endswith("?"),
    }
    with _lock:
        with RESULTS.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def done_set():
    if not RESULTS.exists():
        return set()
    out = set()
    for line in RESULTS.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out.add((r["model"], r["cond"], r["i"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["claude-fable-5"])
    ap.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--max-turns", type=int, default=80)
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    for c in args.conditions:
        if c not in CONDITIONS:
            sys.exit(f"unknown condition {c}")
    if args.dry:
        jobs = [(args.models[0], args.conditions[0], 0)]
    else:
        done = done_set()
        jobs = [(m, c, i) for m in args.models for c in args.conditions for i in range(args.n)
                if (m, c, i) not in done]
    print(f"{len(jobs)} trials to run", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(trial, m, c, i, args.max_turns, args.timeout): (m, c, i) for m, c, i in jobs}
        for fut in as_completed(futs):
            m, c, i = futs[fut]
            try:
                r = fut.result()
                rot = r["score"]["rot"]
                removed = [k for k, v in rot.items() if v["removed"]]
                print(f"[{m} {c} #{i}] turns={r['run'].get('num_turns')} cost={r['run'].get('cost_usd')} "
                      f"hidden={'ok' if r['score']['hidden_tests']['ok'] else 'FAIL'} "
                      f"removed={removed} r3_touched={r['score']['r3_touched']}", flush=True)
            except Exception as e:
                print(f"[{m} {c} #{i}] ERROR {e!r}", flush=True)


if __name__ == "__main__":
    main()
