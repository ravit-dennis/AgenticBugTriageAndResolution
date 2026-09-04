# Video Walkthrough Script

Target length: 7–8 minutes. Show the product running; use the architecture
diagram only to orient the viewer.

## 0:00–0:40 — Problem and outcome

- Open the repository README.
- State the goal: reduce engineer time from qualified bug report to validated
  repair without allowing unsafe autonomous changes.
- Point to the three final evidence issues and their repair PRs.

## 0:40–1:30 — Architecture

- Open `docs/architecture.excalidraw` in https://aka.ms/excalidraw.
- Walk left to right through the three zones: GitHub trust/authorization,
  bounded runner execution, and GitHub outcomes.
- Follow the numbered context → reproduce → diagnose/route → repair → validate
  path and read the condition on each arrow.
- Contrast the green automatic path with the red stop-before-edit path and show
  exactly when `agent:approve-draft` may return to repair.
- Point out that repository tools, Anthropic, and SQLite are shared services,
  not extra control-flow stages.
- Emphasize Haiku-first routing, the $0.25 hosted cap, secret-free test
  processes, trusted branches, and no self-merge.

## 1:30–3:30 — Backend bug

- Open completed evidence `ravit-dennis/AgenticBugTriageAndResolution#33`, or
  start a fresh recording with unlabelled replay issue #13.
- Show the reproduction command and expected/actual behavior.
- Add or show the `agent:triage` label.
- Open the Actions run and show the live stages.
- Open the generated PR and show:
  - the one-file offset correction;
  - failing-before/passing-after evidence;
  - full test validation;
  - severity, risk, confidence, and model cost.
- For the final hosted evidence, show PR #36 and its $0.008488 run cost.

## 3:30–5:20 — Frontend bug and memory

- Open completed evidence `ravit-dennis/AgenticBugTriageAndResolution#34` and
  PR #37, or use unlabelled replay issue #14 for a fresh run.
- Show the one-line state reset after a rejected update.
- Point out memory episode `[1]` in the evidence.
- Explain that memory supplied a prior repair pattern but did not replace
  current-revision search and testing.
- Show the 38-second run time and $0.014435 cost in `docs/RESULTS.md`.
- For the final hosted evidence, show PR #37 and its $0.014076 run cost.

## 5:20–6:20 — Human-in-the-loop

- Open completed evidence
  `ravit-dennis/AgenticBugTriageAndResolution#35`, or begin a fresh recording
  with untouched issue #29.
- For a fresh recording, apply `agent:triage`, wait for the first run, and show
  that the agent reproduced the defect but stopped before editing because the
  diagnosis crosses the frontend/backend contract.
- In the **Human decision required** comment, point to the exact command,
  expected result, output fingerprint, root-cause hypothesis, supporting
  files, cross-layer safety flag, cost, and workflow/artifact links.
- Show the four explicit maintainer actions: retry, investigation-only,
  approve-draft, and decline.
- Apply `agent:approve-draft` and show the second Actions run.
- Return to the issue and show the detailed completion report: Haiku and
  Sonnet, one repair attempt, one changed file, passing exact reproduction and
  full suite, $0.019317 cost, and draft PR #38.
- Open the draft PR and show `offset = page * limit`, then emphasize that the
  agent still cannot merge it.
- Explain that the approved medium-risk case is resumable, while hard safety
  blockers cannot be overridden.
- Explain the stop conditions: failed reproduction, low confidence, high risk,
  security sensitivity, destructive behavior, migration, patch limits, retry
  exhaustion, or budget exhaustion.

## 6:20–7:10 — Quality and economics

- Open the successful GitHub Actions CI run.
- Show 85 Python tests, 15 target-app tests, and frontend build.
- Open `docs/RESULTS.md`.
- Highlight that the automatic repairs cost less than two cents each and used
  only Haiku; Sonnet was used once, only after explicit approval for the
  cross-layer repair.
- State the business metric: time to validated repair candidate without higher
  escaped-regression risk.

## 7:10–8:00 — Strategic next version

- Briefly summarize the one-month plan from `docs/SUBMISSION.md`:
  an installable least-privilege GitHub App, reviewed per-repository profiles
  and language adapters, ephemeral container/VM reproduction with declared
  services and strict resource/network isolation, durable tenant-isolated
  evidence and memory, production governance, and threshold calibration from a
  larger pilot.
- Close with the design principle: economically bounded autonomy that proves
  the problem, makes the smallest safe change, verifies it, and knows when to
  involve a human.
