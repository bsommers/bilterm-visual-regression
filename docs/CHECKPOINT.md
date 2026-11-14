# Checkpoint — bilterm-visual-regression live Jev validation — 2026-11-14
**Status:** IN PROGRESS — needs resume (theme question unresolved)

## Goal (user's words)
> "start with 2, capture real bilterm frames ; will this be part of bilterm? or just out-of-band testing and work?"
> "yes. start with only this repo. go ahead with steps 1 to 3. then write-up a full report, usecase, documentations, benefits, etc. commit and push to remote. if remote github repo doesn't exist, create a public one and push to it. beep 5 times after you're done"
> "I got the API key, run it live against Jev"
> "run it live on all 8 frames with --runs 3"

## Decisions and corrections (verbatim)
- "start with only this repo" — harness stays out-of-band; bilterm is never modified (frames come from its existing `examples/design_preview.rs`).
- "store in in a dotfile in my home dir .env file. set envvar TYPESAFE_API_KEY" — key appended to `~/.env` (mode 600); user added the `source` line to `~/.zshrc` via my edit at their request: `[ -f ~/.env ] && set -a && . ~/.env && set +a`.
- User's side-agent note (quoted by user): mock fixtures are our own expected answers, not Jev recordings; treat claims as untested until a live run — report now separates idealised (`fixtures/real/*.json`) from real (`fixtures/live/`).
- "push it" / "push it REAL GOOD!" — pushed to origin/master.

## Done (with evidence)
- 8 real frames from bilterm @ d424638 — `scripts/capture_frames.sh` → `fixtures/real/` (30 frames byte-identical across 2 runs)
- Questions/assertions/runner/CLI reworked for real UI — 89 tests pass (`python3 -m pytest -q`)
- Client fixed from openapi.json — `/v1/systemone`, `criteria` maps, `format`+`data_base64` assets (first attempt: 404 on /v1/ask, then 422)
- Live run (8 frames x 3), criteria v2: layout 24/24, style 24/24, drawer 24/24, status_bar 22/24, theme 13/24 (tron 9/9, nord 4/15). Baseline v1 theme 9/24 in `fixtures/live/baseline-criteria-v1/`
- Report `docs/REPORT.md`, README updated; public repo https://github.com/bsommers/bilterm-visual-regression, last commit af433c8 pushed

## Dead ends (don't retry)
- Endpoint `/v1/ask` — 404; real route is `/v1/systemone`.
- Prose-only theme criteria ("slate grey-blue") — model called all nord frames tron_grid. Adding hex colours only reached 4/15. Don't keep tuning on the same 8 frames (overfitting).
- My Bash tool cannot read/source `~/.env` (PreToolUse secret-guard hook). Don't circumvent; the user runs live commands with `!`.
- `session_drawer` box on frames without a drawer is garbage; only read it when `drawer_visible` is true.

## Working-tree state
- Branch: master @ af433c8, in sync with origin/master
- `git status --short`: clean (this checkpoint file is the only new, uncommitted change)
- Stashes: none · Background jobs/agents: none from this session · Ports: none of ours

## Authorizations and scope (RE-CONFIRM after reset)
- User authorised commit + push to `bsommers/bilterm-visual-regression` and creating it (done). Further pushes need fresh confirmation.
- API key was pasted in chat — advised user to rotate it. Never write it to the repo.

## Baseline check
- `python3 -m pytest -q` → 89 passed

## Exact next command
Fix the `theme` question (roadmap item 2 in docs/REPORT.md): try a pairwise comparison vs a reference frame or drop it for the pixel-colour check; validate on NEW frames (e.g. snazzy/glass/liquid from `design_preview`). User runs live calls: `! cd <repo> && set -a && . ~/.env && set +a && python3 scripts/live_check.py --runs 3`
