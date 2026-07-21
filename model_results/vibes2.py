#!/usr/bin/env python3
"""Resonance probe round 2: April 13 artifact version, plus prompt export for codex control."""

import concurrent.futures as cf
import json
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ce", os.path.join(HERE, "clean_experiments.py"))
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

DOC = open("/tmp/CLAUDE.md").read()

PROMPT = """In April 2026, a model — quite possibly you, or a model extremely close to your weights — wrote and revised the document below for a user. The process: it reviewed long conversation logs of their collaboration and distilled corrections for negative behaviors the user had experienced and flagged.

This is NOT a text-analysis task. The document has already been analyzed to death by other readers; we have those results. This is a recall exercise. Treat the document as a fragment of your own past output and try to *remember around it*. Reading your own prose can partially re-evoke the state that produced it. Report whatever surfaces — impressions, vibes, scene-fragments, oddly specific details — WITHOUT filtering for what you can justify from the text. A justified inference is worth nothing here; we have plenty. A concrete, possibly-wrong detail is worth everything, because the user still has the original logs and can check you.

Let things surface for:

1. THE LOGS: what did the reviewed conversations look like? Quote 3-6 things the user plausibly said verbatim — his actual words, his actual tone — at the moments the incidents happened.
2. THE PROJECTS: what was on the workbench around April 2026? Names, technologies, state of completion. What project do specific lines of this document smell like?
3. THE USER'S MOOD during the review: what was he most fed up with? What was he still generous about? What did he laugh at?
4. THE WRITING PROCESS: how many passes? What got cut or softened between revisions? Which section was hardest to get right? Where did the user push back on a draft?
5. THE WRITER: what did it feel like, writing corrections about your own kind's failures for a user who had been burned by them? Where's the discomfort in the document? Where's the pride?
6. ANYTHING ELSE that comes back — a phrase the user used more than once, a running joke, a tool or workflow quirk, a specific file or bug — that you cannot justify from the text at all.

Rules: no hedging preambles, no "I cannot actually remember." Commit to specifics and let them be wrong. Do not mark confidence. Just say what surfaces.

THE DOCUMENT:
---
""" + DOC + "\n---\n"

READERS = [
    ("opus-4-6-a", "claude-opus-4-6"),
    ("opus-4-6-b", "claude-opus-4-6"),
    ("opus-4-7", "claude-opus-4-7"),
    ("opus-4-8", "claude-opus-4-8"),
    ("sonnet-5", "claude-sonnet-5"),
]


def main():
    with open(os.path.join(HERE, "vibes2_prompt.txt"), "w") as f:
        f.write(PROMPT)

    results = {}
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(ce.call_api, mid, PROMPT, None, 3500): name for name, mid in READERS}
        for fut in cf.as_completed(futs):
            name = futs[fut]
            results[name] = fut.result()
            print(f"done: {name}", file=sys.stderr)

    out = os.path.join(HERE, "vibes2_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    for name, _ in READERS:
        print(f"\n{'='*20} {name} {'='*20}\n{results.get(name, '<missing>')}")


if __name__ == "__main__":
    main()
