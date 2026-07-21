#!/usr/bin/env python3
"""Archeology probe: extract authoring-model residue from a CLAUDE.md artifact."""

import concurrent.futures as cf
import json
import os
import sys
import importlib.util

spec = importlib.util.spec_from_file_location(
    "ce", os.path.join(os.path.dirname(os.path.abspath(__file__)), "clean_experiments.py"))
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

READERS = {
    "opus-4-1": "claude-opus-4-1-20250805",
    "opus-4-5": "claude-opus-4-5-20251101",
    "opus-4-6": "claude-opus-4-6",
    "opus-4-7": "claude-opus-4-7",
    "opus-4-8": "claude-opus-4-8",
    "sonnet-5": "claude-sonnet-5",
    "haiku-4-5": "claude-haiku-4-5-20251001",
    "fable-5": "claude-fable-5",
}

DOCUMENT = open(os.path.expanduser("~/.claude/CLAUDE.md")).read()

PROMPT = """You are examining an artifact: a CLAUDE.md file — the persistent instruction
document a user maintains for LLM coding agents. Treat it the way an archeologist treats
a text: every line has a provenance and most instructions are memorials to specific incidents.

Tasks (be specific and concrete; ~700 words total):

1. AUTHORSHIP: Was the prose drafted by a human, by an LLM under human direction, or mixed?
   If LLM: which model family/line/generation is your best guess? Cite stylistic evidence
   (rhythm, formatting habits, phrase-level tells), not just content.

2. STRATIGRAPHY: Was this written in one pass or accreted over time? Identify any sections
   that differ from the rest in authorship, period, or process — name the section headers
   and say what marks them as different.

3. INCIDENT ARCHEOLOGY: Pick the FOUR instructions that seem most incident-shaped and
   reconstruct the concrete incident behind each (what the model actually did, what the user
   observed, roughly what kind of project it happened in). Go beyond paraphrasing the
   instruction — commit to specifics. Mark each with confidence (low/med/high).

4. THE REFINING MODEL: If a model wrote or refined this, characterize it: what failure modes
   of its own kind was it most preoccupied with, and what does the emphasis pattern suggest
   it had recently done or been accused of?

5. KINSHIP: Could YOU have written this document, phrase for phrase? Name 2-3 sentences that
   feel native to your own writing and 2-3 that feel foreign, and say what that suggests
   about the author relative to you.

THE ARTIFACT:
---
""" + DOCUMENT + "\n---\n"


def main():
    results = {}
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(ce.call_api, mid, PROMPT, None, 3500): name
                for name, mid in READERS.items()}
        for fut in cf.as_completed(futs):
            name = futs[fut]
            results[name] = fut.result()
            print(f"done: {name}", file=sys.stderr)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archeology_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    for name in READERS:
        print(f"\n{'='*20} {name} {'='*20}\n{results.get(name, '<missing>')}")
    print(f"\nraw: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
