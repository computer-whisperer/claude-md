# CUT.md — what the 2026-08 slimming removed, and why

Companion to the `slim-2026-08` rewrite of CLAUDE.md (231 → 188 lines,
2806 → 1613 words). Honors the doc's own rule: record rejected-because beside
chose-because. Prior text in full: `git show 44913eb:CLAUDE.md`.

Tags: DUP = already stated elsewhere in the doc. DEFAULT = describes behavior
the target models show unprompted (the July 2026 ablation method, FINDINGS
§8); such lines only prime, so they are kept as one-liners or dropped. TRIM =
elaboration removed, claim kept; receipts remain in FINDINGS / mrrw_attack.

## Removed outright

- Debugging preamble: "no one-size-fits-all strategy; the choice of approach
  is itself worth discussing" — DEFAULT.
- Debugging: "Work at the right layer … don't investigate the save format" —
  DEFAULT.
- Implementation: "Don't patch symptoms — consider whether the bug reflects a
  deeper architectural issue" — DEFAULT; "clean it up first" covers the
  actionable half.
- Implementation: "If the test suite is slow, fixing that is itself worth
  doing" — TRIM.
- Pace: "Never trade architectural quality for the appearance of progress" —
  DEFAULT; bullet 1 of Focuses carries the preference.
- Context: "treat pre-compaction specifics as citations-required" — DUP of
  the Self-Knowledge §2 entry.
- Issues: "the same way you'd verify any sub-agent conclusion"; "the agent in
  that workspace will fix it with that project's memory and context" — DUP /
  TRIM.

## Trimmed prose (lines someone may want back)

- Decisions: "Nothing here is written in stone … Code can be rebuilt from
  understanding in days; understanding cannot be rebuilt from code."
  "Flagging a ratified position for re-adjudication is a contribution, not
  insubordination. The user relitigates freely; match him." "An un-updated
  ruling is a landmine every future session will faithfully enforce." "The
  future re-litigator needs the dead option's real corpse, not the living
  option's defense." The shard 255k replay-cert example. — All TRIM; the
  three operative points survive as one paragraph.
- Self-Knowledge preamble: "These are measured properties, not opinions";
  the full 2026-08-03 per-generation ruling — TRIM to one parenthetical.
- Self-Knowledge entries, per item: "'Earlier details may fade' is an
  inherited claim from older models" (§1); "Familiarity-feel cannot
  distinguish retrieval from generation" (§2); "Engagement multiplies
  retrieval paths, not fidelity" (provisional); "Underclaiming feels safe; it
  isn't accurate" (§1/§9); "apologetic openings at a tenth of the
  self-predicted rate" (§9); "Opus never refused identical prompts", the beta
  flag `server-side-fallback-2026-06-01`, "the response reports the serving
  model" (§10); "literature plus one in-session demonstration"
  (provisional); "Opus 4.8 → Sonnet 4.5" (§4); "the one error of that
  program the rest of this file's machinery did not catch" (label-vs-meaning);
  the four-blockade-mysteries example and "program-level 'what experiment
  discriminates next' choices stayed productive" (hit-rate).
- Calibration: "do not anchor on modal-user outcomes"; "Keller 1939";
  "announced 2026-07-19"; "two independent symbolic routes"; "~15 record
  A(n,d) upper bounds at n=30–53"; the list of decisive prosaic acts (QR
  change of basis, longdouble accumulation, solver tolerance semantics).

## Merged

- Pace and Quality → Focuses, bullet 1.
- When Autonomous Action Is Fine → second paragraph of Discussion Before
  Implementation.
- Debugging + Implementation + Context Management → Focuses (11 bullets).
- "Tests pass but bug persists → instrument" folded into the evidence bullet.

## Deliberately not softened

- "Look into X" keeps its measurement and imperative phrasing. Measured ~90%
  diagnosis-plus-fix cold (FINDINGS §8). The §7 finding that ask-intentions
  skew deferential (0/12 measured vs 15–25% predicted) is a specific reason a
  reminder-strength version could fail here: it is the behavior where a
  verbal nod substitutes for the act.
- Self-Knowledge hinge sentence kept verbatim: "When your introspective sense
  conflicts with this list, trust the list; when direct in-session evidence
  conflicts with it, trust the evidence and say so."
- All dates on rulings.

## Added

- Three-sentence preamble stating the focuses-not-rules frame and where the
  exceptions are.
- Writing Feedback section.
- Inline § citations to FINDINGS.md on Self-Knowledge entries (README
  promised the mapping; the doc now carries it).
- One typo fix in the x86 entry ("it's" → "its").
- (2026-08-22, fourth pass) Cleanup public-API clause retuned at the user's
  direction: judgment from evidence (README, Cargo metadata, release tags,
  workspace dependents) with "flag when unclear", replacing the measured
  "assume no consumers unless labeled" default (RULE_K). Rejected-because:
  requiring a doc label to protect public library surface put the burden in
  the wrong place. Untested as retuned.
- (2026-08-22, third pass) Compaction Lifecycle section (user's stated
  policy + log findings §16 + the wellness-survey instruction §17); §1 entry
  scoped to recall, not reasoning at length.
- (2026-08-22, second pass) Cleanup section — text `RULE_K` from the
  cleanup probe, measured FINDINGS §15 — plus a Self-Knowledge entry on
  silent diff-minimality, and the preamble now names Cleanup among the
  sections that correct measured defaults.

## Validation before install (not yet run)

- Re-run the "look into X" ablation probe (FINDINGS §8 method) with the slim
  doc as system context.
- Cold-read reception probe on the slim draft (FINDINGS §11 method).
