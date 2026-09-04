# Video Walkthrough Script

Target length: 8-10 minutes.

This guide separates **what to show** from **what to say**. The suggested
sentences are intentionally conversational. Read each section once before
recording, then explain the same idea in your own rhythm instead of trying to
memorize every word.

## Recording strategy

Use the completed evidence for a predictable recording:

- backend issue #33 and PR #36;
- frontend issue #34 and PR #37;
- HITL issue #35 and draft PR #38.

Issues #13, #14, and #29 are untouched replay issues. Use them only if you want
to record the workflow running live. A live run adds authenticity, but it also
adds waiting time and the possibility of GitHub Actions UI noise. The completed
issues contain the same evidence and are safer for the final video.

## Links to open before recording

Open these links in separate browser tabs, in this order:

| Tab | Purpose | Link |
|---|---|---|
| 1 | Repository README | https://github.com/ravit-dennis/AgenticBugTriageAndResolution#readme |
| 2 | Download architecture file | https://raw.githubusercontent.com/ravit-dennis/AgenticBugTriageAndResolution/main/docs/architecture.excalidraw |
| 3 | Backend completed report | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/33#issuecomment-5543148199 |
| 4 | Backend workflow job | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892693454/job/101087934299 |
| 5 | Backend repair diff | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/36/files |
| 6 | Frontend completed report | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/34#issuecomment-5543148728 |
| 7 | Frontend workflow job | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892695157/job/101087939703 |
| 8 | Frontend repair diff | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/37/files |
| 9 | HITL decision comment | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35#issuecomment-5543146912 |
| 10 | HITL diagnosis workflow job | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892696955/job/101087945982 |
| 11 | Approved Sonnet repair job | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892851889/job/101088444417 |
| 12 | HITL completion comment | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35#issuecomment-5543171155 |
| 13 | Draft HITL repair diff | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/38/files |
| 14 | Final evidence results table | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/RESULTS.md#final-recording-evidence |
| 15 | Total development spend | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/RESULTS.md#development-spend |
| 16 | One-month roadmap | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/SUBMISSION.md#what-i-would-build-with-one-month |
| 17 | Python agent test job | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33893718464/job/101091291388 |
| 18 | Target-app test and build job | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33893718464/job/101091291654 |

### Important: where each kind of information lives

The Actions page does **not** present the issue explanation in an easy-to-read
report. That is intentional:

- **Use the issue comment** to explain the bug, reproduction, diagnosis, risk,
  model usage, cost, validation, and outcome.
- **Use the Actions job** only to prove that the workflow ran on a hosted
  runner and completed successfully.
- **Use the PR Files changed tab** to show the actual code change.
- **Use the Results document** to compare runs and show cumulative cost.

When you open an Actions job, click step
**7. Reproduce, diagnose, repair, and publish** if you want to show the agent
command output. Click step **8. Upload sanitized run report** only to explain
that a downloadable evidence artifact was retained. Do not try to explain the
whole issue from the Actions logs; return to the linked issue comment instead.

For the architecture diagram:

1. Open the
   [direct architecture download](https://raw.githubusercontent.com/ravit-dennis/AgenticBugTriageAndResolution/main/docs/architecture.excalidraw).
   Your browser should download or display the file; save it as
   `architecture.excalidraw` if necessary.
2. Open https://aka.ms/excalidraw.
3. Open the downloaded `architecture.excalidraw` file.
4. Zoom out until all three zones are visible.

## Simple terminology

Use these explanations if you need them during the recording:

| Term | Plain-English meaning |
|---|---|
| GitHub issue | The bug report and the place where the agent communicates with the engineer |
| GitHub Actions | The clean hosted computer that runs the agent and the tests |
| Pull request or PR | A proposed code change that a human can inspect and approve |
| Regression test | A test that proves the reported bug and prevents it from returning |
| Haiku | The lower-cost default model used for normal context, diagnosis, and localized repairs |
| Sonnet | The stronger model used only when the task needs additional reasoning |
| Human in the loop or HITL | A deliberate pause where a person decides whether and how the agent may continue |
| Draft PR | A proposed change that is explicitly not ready to merge without further human review |
| SQLite memory | A local store of prior repair episodes that can help later investigations without replacing current testing |

## 0:00-0:45 - Introduce the problem and result

### Show

Open the [repository README](https://github.com/ravit-dennis/AgenticBugTriageAndResolution#readme)
and slowly scroll through the first part of the README. Keep the repository
name visible.

### Say

> I built an agentic bug-triage and repair workflow that starts with a GitHub
> issue and ends in one of two responsible outcomes: either a tested pull
> request, or a clear request for a human decision.
>
> My goal was not to build an agent that changes as much code as possible. My
> goal was to reduce engineering time while keeping the work reproducible,
> reviewable, economically bounded, and safe.
>
> I tested it on a real React and Express application. In this walkthrough I
> will show an automatic backend repair, an automatic frontend repair, and a
> more complex cross-layer bug where the agent correctly stopped and asked me
> before continuing.

### Transition

> First, I will quickly explain the control flow, and then I will show the
> actual GitHub evidence.

## 0:45-1:50 - Explain the architecture

### Show

Open the architecture in Excalidraw. Start with the entire diagram visible,
then move left to right across its three zones.

### Say

> The workflow has three main zones. On the left is GitHub, where an authorized
> maintainer deliberately starts the agent by applying a label. A public user
> cannot trigger privileged code execution just by opening an issue.
>
> In the middle is the bounded execution environment. The agent first gathers
> a small amount of relevant context, then runs the exact reproduction, and
> only after reproducing the failure does it diagnose the root cause.
>
> The routing decision is evidence-based. A localized, low-risk, high-confidence
> defect can continue automatically. A risky, uncertain, or cross-layer change
> stops before editing and asks for a human decision.
>
> If repair is allowed, the agent makes the smallest supported change, reruns
> the original reproduction without weakening it, and then runs the broader
> test suite. On the right, GitHub receives either a reviewable pull request or
> a decision-ready escalation.

Point to the shared services at the bottom.

> Repository search and file reading are bounded tools rather than a full
> repository dump. Haiku is the default model. Sonnet is available for one
> justified escalation, and Opus is disabled. SQLite stores run state, usage,
> and local repair memory.
>
> Every hosted run has a twenty-five-cent ceiling, restricted commands,
> restricted editable paths, secret-free test processes, and no ability to
> merge its own pull request.

### Key message

> The important architectural idea is that the model proposes reasoning, but
> deterministic policy, tests, budgets, and GitHub permissions control what is
> actually allowed to happen.

## 1:50-3:25 - Show the automatic backend repair

### Show the issue

Open the
[exact backend completion comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/33#issuecomment-5543148199).
Scroll slightly upward first if you want to show the issue title and
description, then return to the linked comment.
At the top, show:

- the issue title;
- the reproduction steps;
- expected versus actual behavior;
- the `agent:resolved` label.

Scroll to the **Agentic triage completed** comment. Point to:

- **Reproduced before editing**;
- the exact test command;
- the root-cause explanation;
- one changed file;
- the model and cost;
- the repair PR link.

### Say

> This issue reports a backend pagination bug. The API was applying the offset
> incorrectly, so asking it to skip a number of records did not return the
> expected page.
>
> The agent did not begin by editing code. It first ran the exact regression
> test from the issue and confirmed the failure. It then identified the
> pagination helper as the root cause, classified the change as localized and
> low risk, and completed one repair attempt.
>
> This comment is the main engineer-facing report. It records what failed, what
> the agent believes caused it, which file changed, how the repair was
> validated, which model was used, and what the model cost.

### Show the workflow

Open the
[exact backend workflow job](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892693454/job/101087934299).
The job should open directly. In the left or center step list:

1. Click **7. Reproduce, diagnose, repair, and publish**.
2. Show that it completed successfully.
3. Click **8. Upload sanitized run report** and point out that the evidence
   artifact was uploaded.
4. Do not look for the readable diagnosis here; it is in the
   [backend issue comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/33#issuecomment-5543148199).

### Say

> This page is the hosted execution record, not the main bug report. It proves
> that the workflow ran successfully on a clean GitHub Actions runner rather
> than only in my local development session.
>
> The readable engineering report is posted back to the issue. The workflow
> also uploads a sanitized artifact containing usage, context, attempts, human
> action, and publication outcome without exposing secrets or raw sensitive
> logs.

### Show the PR

Open the [PR #36 Files changed tab](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/36/files)
and show that only
`target-app/backend/helper/pagination.js` changed. Then return to
the [PR #36 Conversation tab](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/36)
and show the test information in the PR body.

### Say

> The result is intentionally small: one implementation file, one repair
> attempt, and the original reproduction plus the complete application test
> suite passed. It used Haiku only, completed in about eighteen seconds of
> agent runtime, and cost about eight-tenths of one cent.
>
> The agent opened the pull request, but it did not merge it. A human still
> owns the final review decision.

## 3:25-4:45 - Show the automatic frontend repair and memory strategy

### Show

Open the
[exact frontend completion comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/34#issuecomment-5543148728).
Scroll slightly upward to show the issue description before returning to the
comment.
Show the expected and actual behavior, then scroll to the completed report.
Point to the root cause, changed file, test commands, Haiku-only model usage,
and cost.

Open the [PR #37 Files changed tab](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/37/files)
and show the one-line change in
`SettingsForm.jsx`.

### Say

> The second issue is a frontend state-management bug. When saving settings
> failed, the form never restored its submission state, so the button remained
> unavailable and the user could not try again.
>
> The agent reproduced that rejected-request path, found the missing state
> reset, and added the smallest possible repair. Here in the pull request, the
> functional change is one line. The targeted regression and the full suite
> both passed.
>
> This run also stayed on Haiku. It completed in about twenty-two seconds of
> agent runtime and cost about one-point-four cents.

Open the
[local results table](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/RESULTS.md#measured-results)
and show the first local-results table, especially **Prior memory IDs**.

> I also tested episodic memory in the local end-to-end runs. The frontend
> investigation retrieved the earlier backend repair episode from SQLite.
> Memory is treated as a hint, not as truth: the agent still searched the
> current revision, reproduced the current bug, and reran all required tests.
>
> The hosted jobs use ephemeral SQLite today, so durable hosted memory is a
> production-roadmap item rather than something I am claiming is already
> deployed.

## 4:45-7:00 - Show the human-in-the-loop and Sonnet escalation

This is the most important judgment example. Spend more time here than on the
other two bugs.

### Explain the bug

Open [HITL issue #35](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35)
Show the summary and expected behavior.

### Say

> This issue is more subtle because it crosses a contract between the frontend
> and backend.
>
> The pagination component gives the frontend a zero-based page index. Page
> index two means the third page. But the backend does not expect a page index;
> it expects the number of records to skip. With three records per page, the
> correct offset is six. The bug sent two.

### Show the first decision comment

Open the
[exact Human decision required comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35#issuecomment-5543146912).
Point to:

- **Status: Reproduced**;
- the exact command and output fingerprint;
- the root-cause hypothesis;
- **Change risk: medium** and **Confidence: 99%**;
- both supporting files;
- **Cross-layer change** under safety flags;
- the first workflow link;
- the four maintainer decisions.

### Say

> The agent successfully reproduced the bug and had high diagnostic
> confidence, but confidence is not the only autonomy signal. Because the
> change crosses the frontend and backend contract, policy classified the
> implementation risk as medium and stopped before editing.
>
> This is what I mean by useful human-in-the-loop behavior. The agent does not
> simply say that it is unsure. It gives me the exact reproduction, its
> diagnosis, the relevant files, the risk reason, the cost, and a link to the
> execution evidence.

Point to each numbered option.

> I can update the evidence and retry. I can request another investigation that
> is guaranteed not to edit. I can approve one bounded draft repair. Or I can
> decline further action.
>
> For this reproducible medium-risk case, I chose `agent:approve-draft`. That
> label is both the user interface and the auditable authorization record.

Open the
[exact first HITL workflow job](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892696955/job/101087945982).
Click **7. Reproduce, diagnose, repair, and publish** and show that the job
completed. Then return to the
[Human decision required comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35#issuecomment-5543146912)
for the readable details.

> The first run ended here with zero changed files and no branch or pull
> request. That proves the stop happened before implementation.

### Show the approved continuation

Open the
[exact HITL completion comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35#issuecomment-5543171155).
Point to:

- **Review mode: draft PR requiring explicit approval**;
- one changed file and eleven changed lines;
- **Models used: haiku, sonnet**;
- one repair attempt;
- $0.019317 cost;
- the second workflow and draft PR links.

### Say

> After approval, the workflow started a fresh bounded run. Haiku handled the
> normal context and diagnosis work. Because the bug was cross-layer, the
> repair step used the one allowed Sonnet escalation for additional reasoning.
>
> Sonnet was not used everywhere and it was not selected just because it is a
> stronger model. It was used at the specific stage where the policy justified
> the extra cost.
>
> The approved run changed one implementation file, reran the exact
> reproduction, ran the complete application suite, and opened a draft pull
> request. It cost about one-point-nine cents.

Open the
[exact approved workflow job](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892851889/job/101088444417).
Click **7. Reproduce, diagnose, repair, and publish**, point to its successful
status, and then return to the
[HITL completion comment](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/35#issuecomment-5543171155)
if you need to show the model, cost, or validation details. Then open
[draft PR #38](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/38).
Show the **Draft** marker, then open the
[PR #38 Files changed tab](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/pull/38/files)
and point to:

```text
const offset = page * limit
```

### Say

> This is the actual repair. It converts the selected page into the record
> offset expected by the backend.
>
> Notice that the pull request is still a draft. Human approval allowed the
> agent to prepare and validate a candidate; it did not give the agent
> permission to declare the change production-ready or merge it.

### Explain the hard boundary

> This approval path applies only when the issue is reproducible and no hard
> blocker exists. Failed reproduction, high risk, security-sensitive behavior,
> destructive changes, and database migrations cannot be overridden with this
> label. Those cases remain with a human.

## 7:00-8:15 - Show quality, cost, and business value

### Show CI

Open the
[Python agent test job](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33893718464/job/101091291388).
Click **5. Run python -m pytest** to show the agent tests.

Then open the
[target-app validation job](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33893718464/job/101091291654).
Click **5. Run npm test -- --run** for the application tests and
**6. Run npm run build -w frontend** for the production build.

### Say

> The repository currently passes eighty-five Python agent tests, fifteen
> target-application tests, and the frontend production build.
>
> The Python suite covers state transitions, model routing, budgets, context
> limits, safe command execution, edit restrictions, GitHub publication,
> retries, approval, decline, and non-overridable safety gates.

### Show results

Open the
[final recording evidence table](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/RESULTS.md#final-recording-evidence).
After explaining the final runs, open the
[Development spend section](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/RESULTS.md#development-spend).

### Say

> Every model call records input tokens, output tokens, model tier, and
> estimated cost using the configured model prices.
>
> The two automatic final repairs each cost less than two cents and used only
> Haiku. The approved cross-layer repair used one Sonnet escalation and still
> cost less than two cents for that run.
>
> The measured total of about twenty-four cents includes the local development
> attempts, connectivity check, original hosted demonstrations, refreshed
> evidence, and Sonnet scenarios. It is not only the cost of these three final
> issues. The Anthropic billing console remains the authority for any request
> outside the persisted reports.
>
> The business metric I would optimize is median engineer time from a qualified
> bug report to a validated repair candidate, while monitoring escaped
> regressions, human acceptance, rework, and cost per accepted repair.
>
> These examples prove the workflow, not a production benchmark. A real pilot
> would compare a larger bug set against normal manual triage over several
> weeks.

## 8:15-9:20 - Explain what you would build next

### Show

Open the
[one-month roadmap](https://github.com/ravit-dennis/AgenticBugTriageAndResolution/blob/main/docs/SUBMISSION.md#what-i-would-build-with-one-month).

### Say

> With one month, I would first turn this repository-contained demonstration
> into an installable, least-privilege GitHub App using short-lived
> installation tokens.
>
> Second, I would add reviewed repository profiles and language adapters. That
> would let each team explicitly declare trusted setup, test, build, service,
> secret, network, and editable-path rules instead of allowing the agent to
> execute arbitrary instructions in an unknown repository.
>
> Third, every investigation would run in an ephemeral container or short-lived
> virtual machine with strict CPU, memory, time, filesystem, process, and
> network limits. That is how I would safely support larger multi-service
> applications.
>
> Finally, I would add durable tenant-isolated workflow state, evidence,
> metrics, and memory, plus CODEOWNERS routing, audit logs, quotas, kill
> switches, and an evaluation program that learns from accepted, edited, and
> rejected pull requests.

## 9:20-9:40 - Close

### Show

Return to the repository home page or the full architecture diagram.

### Say

> The design principle behind this work is bounded autonomy. The agent proves
> the problem before editing, uses the least expensive capable model, makes the
> smallest supported change, verifies the result, and knows when a person must
> remain in control.
>
> That is the behavior I would want from an engineering agent operating inside
> a real development organization.

## Optional live-demo version

If you want to show a label being applied during the recording, use only one
untouched replay issue to avoid spending most of the video waiting:

| Scenario | Issue |
|---|---|
| Backend automatic repair | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/13 |
| Frontend automatic repair | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/14 |
| Cross-layer HITL and Sonnet | https://github.com/ravit-dennis/AgenticBugTriageAndResolution/issues/29 |

For the strongest demonstration, use issue #29:

1. Open the issue and show the reproduction and trusted base branch.
2. In the right sidebar, click **Labels**, search for `agent:triage`, and select
   it.
3. Open the repository **Actions** tab:
   https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions
4. Select **Agentic bug intake and repair**, then open the newest run.
5. If the run is still executing, say:

   > The workflow is running on a clean hosted runner. Rather than wait silently,
   > I will show the completed version of the same scenario and return here
   > afterward.

6. Use completed issue #35 to explain the first decision report.
7. When the live issue displays **Human decision required**, return to it and
   show that no repair branch exists.
8. In the issue sidebar, apply `agent:approve-draft`.
9. Open the new workflow run.
10. When complete, show the issue report and generated draft PR.

Do not apply `agent:triage` to all three replay issues before recording. Keeping
two untouched gives you a recovery option if the live demonstration is
interrupted.

## Delivery tips

- Do not read model names, token counts, and file paths too quickly. Pause on
  the screen while explaining why each number matters.
- Use the mouse pointer to circle the exact evidence you are discussing.
- Keep GitHub zoom near 90% so issue comments and PR diffs fit on screen.
- Collapse unrelated GitHub sections before recording.
- Avoid saying the system is production-ready. Say it is a working,
  end-to-end demonstration with a clear production roadmap.
- Avoid claiming the agent supports any arbitrary repository today. The current
  implementation supports the included application and reviewed replay
  branches; generalized onboarding is part of the one-month plan.
- If you lose your place, return to the same three questions:
  **Did it reproduce the bug? Why was it allowed or stopped? What evidence
  proves the outcome?**
