# context_rot_logs — symptom rates vs context position, from session transcripts

2026-08-22. `analyze.py` walks every Claude Code session transcript under
`~/.claude/projects` (≥50 KB; sub-agent lines excluded), takes the context
position at each assistant turn from `usage` (input + cache_creation +
cache_read), and counts per 50k-token bin: tool errors (permission denials
excluded), Edit/Write no-match errors, near-duplicate tool calls (same tool +
input within the last 10 calls of a segment), re-reads (Read of a path already
read since the last compaction), and assistant "start fresh"-type phrases
(split by whether the preceding user message mentioned compaction/context).
Compactions come from `compact_boundary` system lines (trigger, preTokens);
the first user prompt after a boundary is checked for "fresh look" wording.

Registered predictions (made before running, in the 2026-08-22 session):
1. Symptom rate rises ~1.5–2× from the first 100k to the 400–600k band.
2. Repeated-call rate rises more sharply than edit-failure rate.
3. "Start fresh" proposals cluster at 150–250k regardless of window.
4. The last 50k before a fresh-look restart shows a symptom spike vs the
   session's first 100k.

Results: `report.txt`. Summary: (1) wrong for errors — tool and edit errors are
flat ~2%/0.4% from 50k to 500k and fall after; right for repeats — 0.3% →
1.5% past 500k, on 21 events. (2) right. (3) wrong — unprompted phrases
(35/43) have median 274k and the per-turn rate rises 5–10× past 300k, which
is also where the user compacts (median 332–363k). (4) label contaminated:
the user's routine restart prompt also says "review the previous work";
errors fall and repeats rise (0.1% → 0.4%) before compactions generally.
All 245 compactions were manual; zero auto. Sessions: median max 337k, 38
≥400k, 8 ≥600k, max 723k. Long sessions' first 100k look like short
sessions' (err 3.6% vs 3.2%), so the curves aren't task-mix.

Caveat: these are coarse symptoms. Reasoning quality at position (tunnel
vision, missed alternatives) is not measured here — that is what the
wellness survey (`model_results/wellness/`) pairs self-report with.
