# Video Walkthrough Script

Target length: 7–8 minutes. Show the product running; use the architecture
diagram only to orient the viewer.

## 0:00–0:40 — Problem and outcome

- Open the repository README.
- State the goal: reduce engineer time from qualified bug report to validated
  repair without allowing unsafe autonomous changes.
- Point to the two GitHub issues and repair PRs.

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

- Open completed evidence `ravit-dennis/AgenticBugTriageAndResolution#7`, or
  start a fresh recording with unlabelled replay issue #13.
- Show the reproduction command and expected/actual behavior.
- Add or show the `agent:triage` label.
- Open the Actions run and show the live stages.
- Open the generated PR and show:
  - the one-file offset correction;
  - failing-before/passing-after evidence;
  - full test validation;
  - severity, risk, confidence, and $0.009210 model cost.
- For the final hosted evidence, show PR #10 and its $0.008568 run cost.

## 3:30–5:20 — Frontend bug and memory

- Open completed evidence `ravit-dennis/AgenticBugTriageAndResolution#8` and
  PR #11, or use unlabelled replay issue #14 for a fresh run.
- Show the one-line state reset after a rejected update.
- Point out memory episode `[1]` in the evidence.
- Explain that memory supplied a prior repair pattern but did not replace
  current-revision search and testing.
- Show the 38-second run time and $0.014435 cost in `docs/RESULTS.md`.
- For the final hosted evidence, show PR #11 and its $0.014259 run cost.

## 5:20–6:20 — Human-in-the-loop

- Open `ravit-dennis/AgenticBugTriageAndResolution#6`.
- Show the **Human decision required** comment and
  `agent:needs-information` label.
- Expand the reproduction output and point to the exact command, expected
  behavior, root-cause hypothesis, supporting files, safety flags, cost, and
  workflow-run link.
- Show the four explicit maintainer actions: retry, investigation-only,
  approve-draft, and decline.
- Explain that draft approval is disabled for this high-risk destructive case;
  hard safety blockers cannot be overridden.
- Confirm that no repair branch or PR was published.
- Explain the stop conditions: failed reproduction, low confidence, high risk,
  security sensitivity, destructive behavior, migration, patch limits, retry
  exhaustion, or budget exhaustion.

## 6:20–7:10 — Quality and economics

- Open the successful GitHub Actions CI run.
- Show 82 Python tests, 15 target-app tests, and frontend build.
- Open `docs/RESULTS.md`.
- Highlight that the successful demonstrations cost less than two cents each
  and used only Haiku.
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
