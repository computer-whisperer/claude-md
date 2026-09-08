# claude-md

Global CLAUDE.md and AGENTS.md for my Claude Code and Codex sessions, plus
the measured evidence behind the Claude-specific claims. The live copies in `~/.claude/` (`CLAUDE.md`, `model_results`) are
symlinks into a prod worktree of this repo at `~/workspace/claude-md-prod`,
which stays on `main`. Codex uses `~/.codex/AGENTS.md`, symlinked to
`~/workspace/claude-md-prod/AGENTS.md`; there is no home-directory
`~/AGENTS.md` copy. This directory is the dev checkout and can sit on any
branch without touching live sessions. Deploying is a fast-forward of `main`
in the prod worktree (`git -C ~/workspace/claude-md-prod merge <branch>`), so
the document's history is its changelog.

Shared because co-workers keep asking for the doc — but the doc is the less
interesting half. The Claude measurement method is the point:

- **Behavioral instructions earn their place by measurement.** Before an
  instruction is added or kept, cold-context probes check whether the target
  models already do the thing (cut it as superseded) or still need the
  correction (keep it, with the measurement cited inline). See
  `model_results/ablation_probe.py` for the pattern.
- **Factual claims carry receipts.** Every measured claim in the doc's
  Self-Knowledge section maps to a numbered section of
  `model_results/FINDINGS.md` and a re-runnable script beside it. Claims that
  can't carry a receipt don't go in.

## Layout

- `CLAUDE.md` — the live document (`~/.claude/CLAUDE.md` symlinks here).
- `AGENTS.md` — the Codex variant, sharing collaboration policies while omitting
  model calibration until measurements are repeated on OpenAI models. The
  Jacobian example retains its independently runnable verifier.
- `model_results/` — `FINDINGS.md` (start there) plus probe scripts and raw
  result JSONs. `model_results/cleanup_probe/` is the August 2026 agentic
  probe behind the Cleanup section (fixture crate, headless runner, every
  registered prediction, `results.jsonl`); it runs through `claude -p` with
  the logged-in credentials rather than the bare API. Scripts read `ANTHROPIC_API_KEY` from the environment and cost
  real tokens to re-run. `jacobian_check.py` is the self-contained receipt for
  the Calibration section's Jacobian-conjecture entry (~5 s, sympy only).

## Adapting this

"The User" and "Calibration: Track Record" are specific to me — replace them
wholesale. The Self-Knowledge numbers were measured July 2026 on Fable 5 and
Opus 4.8 at small n (see the Caveats section of FINDINGS.md): re-run the probes
against your own model mix before copying the claims. An instruction copied
without its measurement is exactly the kind of inherited folklore this file
exists to kill.

## Codex adaptation

AGENTS.md starts from the production CLAUDE.md at `19267fd`. Shared policy
wording is kept aligned directly; no generated includes are required.
Claude self-measurements, portfolio calibration, manual-compaction assumptions,
token thresholds, wellness instrumentation, and Claude-specific agent details
are omitted. Context guidance accommodates automatic compaction. Runtime
claims explicitly require runtime evidence, and cleanup applies during
authorized implementation. The Jacobian verifier passed on 2026-09-08.

Deploy changes by committing in the dev checkout, fast-forwarding the prod
worktree, and keeping `~/.codex/AGENTS.md` linked to its AGENTS.md.
