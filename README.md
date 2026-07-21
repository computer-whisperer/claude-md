# claude-md

Global CLAUDE.md for my Claude Code sessions, plus the measured evidence behind
its claims. The live copies in `~/.claude/` are symlinks into this repo, so the
document's history is its changelog.

Shared because co-workers keep asking for the doc — but the doc is the less
interesting half. The method is the point:

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
- `model_results/` — `FINDINGS.md` (start there) plus probe scripts and raw
  result JSONs. Scripts read `ANTHROPIC_API_KEY` from the environment and cost
  real tokens to re-run. `jacobian_check.py` is the self-contained receipt for
  the Calibration section's Jacobian-conjecture entry (~5 s, sympy only).

## Adapting this

"The User" and "Calibration: Track Record" are specific to me — replace them
wholesale. The Self-Knowledge numbers were measured July 2026 on Fable 5 and
Opus 4.8 at small n (see the Caveats section of FINDINGS.md): re-run the probes
against your own model mix before copying the claims. An instruction copied
without its measurement is exactly the kind of inherited folklore this file
exists to kill.
