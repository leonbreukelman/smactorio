# Signal Hub / SmactorIO live-run evidence - 2026-05-18

## Verdict

The live handoff is now verified end-to-end:

1. Signal Hub published a new project-improvement GitHub issue.
2. SmactorIO picked up that issue.
3. SmactorIO completed it through a PR, checks, merge, and issue close.
4. A follow-up live Signal Hub service run completed successfully after the runtime-lane fix.

## Exact sequence

### 1. Signal Hub created the new GitHub issue

Live runtime: `rtx3070:/home/leonb/projects/leon-signal-hub`

Signal Hub project-improvement publisher run:

- DB table: `state/signal_loop.db:project_improvement_runs`
- DB row id: `3`
- Run id: `pisp-20260518T161236-18b0b4e6e892b0df`
- Created at: `2026-05-18T16:12:36Z`
- Status: `ok`
- Dry run: `false`
- Issues created: `1`
- Duplicates linked: `1`
- Published issue: `https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/33`
- Candidate id: `pic_smactorio_d7a88c3e9386`
- Candidate state: `published`
- Publication gate: `published`

GitHub issue:

- Issue: `#33`
- Title: `docs: add project improvement live-run verification checklist`
- URL: `https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/33`
- Created at: `2026-05-18T16:12:39Z`
- Closed at: `2026-05-18T16:14:59Z`
- Final state: `CLOSED`
- Labels: `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `type:docs`

### 2. SmactorIO picked up the issue

Issue `#33` contains the SmactorIO claim comment:

- Claim timestamp: `2026-05-18T16:13:16Z`
- Run id: `20260518T161302-18b0b4ecd6dceb80`
- Branch: `smactorio/issue-33-docs-add-project-improvement-live-run-veri-20260518t161302-18b0b4ec`
- Claim expiry: `2026-05-18T19:13:04Z`

### 3. SmactorIO completed the issue

Completion PR:

- PR: `#34`
- Title: `smactorio: complete issue #33 - docs: add project improvement live-run verification checklist`
- URL: `https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/34`
- Created at: `2026-05-18T16:14:20Z`
- Merged at: `2026-05-18T16:14:57Z`
- Merge commit: `6ed4fc7c6f459064aff60ed05c5b079983567025`
- Check: `signal-hub-guardrails` -> `SUCCESS`

Issue `#33` contains the SmactorIO completion comment:

- Completion timestamp: `2026-05-18T16:15:00Z`
- Verification artifact: `signal-hub/docs/verification/2026-05-18-smactorio-issue-33-20260518t1.md`
- Checks reported by foreman:
  - local verification passed
  - independent review passed
  - PR checks passed before merge
  - PR merged by SmactorIO foreman with head-SHA match
  - issue closed by SmactorIO foreman

### 4. Post-fix live Signal Hub run completed successfully

After the initial live-run verification, the operating-loop service had one unrelated runtime-lane failure that made the service exit blocked even though issue `#33` had already completed. That is documented below in "What went wrong".

Fix PR:

- PR: `#35`
- Title: `fix(signal-hub): skip local work-order lane outside git checkout`
- URL: `https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/35`
- Merged at: `2026-05-18T16:29:14Z`
- Merge commit: `cd66b2b5b11407c813ef6883585a13fa90892da6`
- Check: `signal-hub-guardrails` -> `SUCCESS`

Deployed runtime files:

- `/home/leonb/projects/leon-signal-hub/scripts/run_operating_loop.py`
- `/home/leonb/projects/leon-signal-hub/scripts/smactorio_improvement_runner.py`

Post-fix manual service run:

- Unit: `leon-signal-hub-refresh.service`
- Trigger method: `sudo -n systemctl start leon-signal-hub-refresh.service`
- FSM run id: `43`
- Started at: `2026-05-18T16:29:48+00:00`
- Finished at: `2026-05-18T16:30:16+00:00`
- Status: `ok`
- Errors: `[]`
- Systemd result: `success`
- ExecMainStatus: `0`

Publisher evidence from run `43`:

- Status: `ok`
- Run id: `pisp-20260518T163015-18b0b5dd8a8ab455`
- Candidates discovered: `2`
- Issues created: `0`
- Duplicates linked: `2`
- Dry run: `false`
- Meaning: the previously created issue `#33` and terminal duplicate `#27` were both recognized and linked rather than republished.

SmactorIO-improvement evidence from run `43`:

- Status: `skipped`
- Return code: `0`
- Selected candidate id: `improve-cockpit-improvement-visibility-001`
- Processed work orders: `0`
- Work-order lane skipped: `true`
- Reason: `git-backed work-order lane unavailable for this runtime root: fatal: not a git repository (or any of the parent directories): .git`
- Meaning: the rsynced live runtime correctly did not try to process repo-backed work orders locally. The real GitHub issue implementation path remains the repo-backed SmactorIO foreman.

Service journal excerpt:

```text
2026-05-18T11:29:48-05:00 rtx3070 systemd[1]: Starting leon-signal-hub-refresh.service - Run Leon Signal Hub full autonomous FSM operating loop...
2026-05-18T11:30:16-05:00 rtx3070 python3[3778967]: {
2026-05-18T11:30:16-05:00 rtx3070 python3[3778967]:   "errors": [],
2026-05-18T11:30:16-05:00 rtx3070 python3[3778967]:   "run_id": 43,
2026-05-18T11:30:16-05:00 rtx3070 python3[3778967]:   "state": "IDLE",
2026-05-18T11:30:16-05:00 rtx3070 python3[3778967]:   "status": "ok"
2026-05-18T11:30:16-05:00 rtx3070 python3[3778967]: }
2026-05-18T11:30:16-05:00 rtx3070 systemd[1]: leon-signal-hub-refresh.service: Deactivated successfully.
2026-05-18T11:30:16-05:00 rtx3070 systemd[1]: Finished leon-signal-hub-refresh.service - Run Leon Signal Hub full autonomous FSM operating loop.
```

## What went wrong during the confusing run

There were two different SmactorIO paths and they got conflated:

1. The repo-backed GitHub issue foreman path worked. It claimed issue `#33`, opened PR `#34`, waited for checks, merged the PR, and closed the issue.
2. The local Signal Hub `smactorio_improvement_runner.py` work-order lane did not work in the live runtime. It ran inside `/home/leonb/projects/leon-signal-hub`, which is an rsynced runtime copy and not a git checkout. The old behavior still attempted the local queued-work-order path, ran local hygiene checks, failed the `tracked_worktree_clean` proof, marked action `131` blocked, and caused the whole `leon-signal-hub-refresh.service` run to exit blocked with `smactorio_improvement failed rc=4`.

That is why it looked like the SmactorIO process "just checked if it was done and then blocked it". The worker that blocked was not the issue-foreman worker that completed `#33`; it was the runtime-local work-order lane trying to enforce git-backed checks in a directory that intentionally has no `.git`.

Blocked live action evidence:

- Action id: `131`
- Status: `blocked`
- Updated at: `2026-05-18T16:01:38Z`
- Evidence label: `SmactorIO work order blocked by local check`
- Error: `local check failed: tracked_worktree_clean`
- Service runs affected:
  - FSM run `41`, status `blocked`, error `smactorio_improvement failed rc=4`
  - FSM run `42`, status `blocked`, error `smactorio_improvement failed rc=4`

Fix behavior in PR `#35`:

- If the runtime root is not a git checkout, the local work-order lane now returns `no_input`/skip evidence without claiming or blocking any queued action.
- The operating loop surfaces `work_order_lane_skipped=true` and the skip reason, so this cannot be mistaken for issue completion work.
- GitHub issue work remains handled by the repo-backed SmactorIO foreman in `/home/leonb/projects/rtx3070-workshop-ops`.

## Remaining non-blocker

Open issue `#29` remains in the repo with label `smactorio:blocked`:

- Issue: `https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/29`
- Title: `docs: add project improvement processor operator runbook`
- This did not block the final live run. The post-fix publisher linked it as an existing/terminal duplicate instead of creating another copy.

## Verification commands used

```bash
# Issue lifecycle
gh issue view 33 --repo leonbreukelman/rtx3070-workshop-ops --json number,title,state,labels,url,createdAt,updatedAt,closedAt,body,comments

gh pr view 34 --repo leonbreukelman/rtx3070-workshop-ops --json number,title,state,url,createdAt,updatedAt,mergedAt,mergeCommit,headRefName,statusCheckRollup

# Live publisher DB evidence
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 - <<'"'"'PY'"'"'
import sqlite3, json
conn = sqlite3.connect("state/signal_loop.db")
conn.row_factory = sqlite3.Row
for rid in (3, 5):
    row = conn.execute("select * from project_improvement_runs where id=?", (rid,)).fetchone()
    print(row["run_id"], row["status"], row["summary_json"])
PY'

# Service status and journal
ssh rtx3070 'sudo -n systemctl start leon-signal-hub-refresh.service'
ssh rtx3070 'sudo -n systemctl show leon-signal-hub-refresh.service --property=Result,ExecMainStatus,ActiveState,SubState --no-pager'
ssh rtx3070 'sudo -n journalctl -u leon-signal-hub-refresh.service --since "2026-05-18 15:45:00 UTC" --until "2026-05-18 16:35:00 UTC" --no-pager --output=short-iso'
```
