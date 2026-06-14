# Fresh Session Prompt — Implement SmactorIO GitHub Bootstrap Phase 0

Use this prompt in a new Hermes session.

---

You are Hermes Agent working for Leon. Your task is to implement the next SmactorIO autonomy slice: **Phase 0 — bootstrap the safe Signal Hub/SmactorIO source into the private GitHub repo and open a PR**.

Do not broaden into runtime priority scoring, full Candidate automation, auto-merge, or autonomous roadmap-to-code execution in this session. This session's job is to make the current reviewed SmactorIO source versioned and reviewable through GitHub so later autonomous runtime work has a safe rollback path.

## Load these skills first

Load and follow these before acting:

- `signal-hub-operating-loop-verification`
- `disciplined-project-delivery`
- `github-pr-workflow`
- `github-repo-management`
- `requesting-code-review`
- `test-driven-development` if you change behavior/tests beyond packaging
- `systematic-debugging` if any verification fails
- `subagent-driven-development` only if you split review/inspection work into independent read-only slices

## Desired user-visible outcome

By the end of the session Leon should have:

1. A GitHub issue, unless a duplicate already exists, for Candidate:
   `bootstrap-github-backed-smactorio-source-001`
2. A branch in `leonbreukelman/rtx3070-workshop-ops`:
   `smactor/bootstrap-github-backed-autonomy`
3. A PR from that branch to `main`.
4. The PR contains the current safe Signal Hub/SmactorIO source under:
   `signal-hub/`
5. The PR does **not** include runtime state, secrets, DBs, logs, caches, backups, credential files, or broad raw data dumps.
6. A committed divergence/packaging verification note at:
   `signal-hub/docs/verification/2026-05-16-bootstrap-divergence.md`
7. Proof in the final response: issue URL, PR URL, branch name, tests run, secret scan result, and any remaining blocker.

Do **not** merge the PR. Human merge is required unless Leon separately changes that policy.

## Autonomy envelope

Proceed without routine questions. Ask Leon only for true blockers:

- missing GitHub auth that cannot be fixed with existing credentials;
- OAuth/2FA/CAPTCHA/browser-login prompts;
- destructive delete/overwrite outside the explicit branch/PR flow;
- public exposure, spend, social/public account mutation, or production deploy not already authorized;
- branch protection or repo permission issue that prevents opening a PR.

Allowed in this session:

- create one GitHub issue for the bootstrap Candidate, after searching for duplicates;
- create a feature branch;
- copy safe source into the private repo worktree;
- commit and push the feature branch;
- open a PR;
- run local tests and secret scans;
- write verification artifacts.

Not allowed in this session:

- direct push to `main`;
- self-merge;
- force-push after PR review has started;
- `rsync --delete` into the GitHub worktree;
- copying runtime `state/`, DBs, logs, caches, backups, `.env*`, credentials, token files, account manifests, or other secrets;
- creating a duplicate scheduler/cron job;
- deploying live `/srv` changes unless needed only to correct a verification artifact and explicitly safe.

## Current verified state as of 2026-05-16T02:17Z

Re-verify this at the start because state may have changed.

Local/live Signal Hub source:

- Local source path: `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`
- rtx3070 live source path: `/home/leonb/projects/leon-signal-hub`
- Live LAN URL: `http://192.168.30.10:8765/`
- Both local and live source paths were observed as `NO_GIT`.
- Local and rtx3070 matched for the authoritative full-autonomy docs/reviews/generator/cockpit data.
- `public/smactorio_full_autonomy.html` hash can differ only because generated timestamps differ; content markers matched.
- Local targeted tests passed: `python3 -m unittest tests.test_full_autonomy_fsm tests.test_page_manifest_and_navigation` → 41/41 OK.
- rtx3070 targeted tests passed with the same command → 41/41 OK.

Private GitHub repo:

- Repo: `leonbreukelman/rtx3070-workshop-ops`
- Visibility: private
- Local checkout: `/home/leonb/projects/rtx3070-workshop-ops`
- Current branch at last check: `main`
- Remote: `git@github.com:leonbreukelman/rtx3070-workshop-ops.git`
- Worktree was clean at last check.
- It already has a `signal-hub/` subtree, but it is stale and missing the new SmactorIO docs/pages/runner files.
- No SmactorIO issue/PR existed at last check.

## Source-of-truth documents to read first

From `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`, read:

- `docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
- `docs/verification/2026-05-16-smactorio-github-backed-full-autonomy-spec-opus-review.md`
- `docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md`
- `docs/verification/2026-05-16-smactorio-github-backed-full-autonomy-plan-opus-review.md`
- `data/project_homepages/smactorio.json`
- `scripts/build_smactorio_full_autonomy_page.py`
- `scripts/smactorio_improvement_runner.py`
- `scripts/run_operating_loop.py`
- `tests/test_smactorio_improvement_runner.py`
- `tests/test_full_autonomy_fsm.py`
- `tests/test_page_manifest_and_navigation.py`

The authoritative plan for this session is Phase 0 in:

`docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md`

Important plan decisions:

- GitHub Issues are the canonical backlog path.
- Normal rollback is git-native: branch/PR/revert/tag. Tarballs are not normal version control.
- Direct push to `main` is not allowed.
- Human merge is required.
- Runtime state, logs, DBs, caches, broad raw `data/` dumps, and credentials are never committed.
- Current slice is docs/site/bootstrap only. Runtime FSM automation is a later Candidate after safe source packaging lands.

## Phase A — Preflight, do not mutate yet

1. Confirm date/time:
   `date -u`
2. Inspect local source:
   - path exists;
   - git status or `NO_GIT`;
   - key docs exist;
   - targeted tests still pass if practical.
3. Inspect GitHub worktree:
   ```bash
   cd /home/leonb/projects/rtx3070-workshop-ops
   git rev-parse --show-toplevel
   git status --short
   git branch --show-current
   git remote -v
   gh repo view leonbreukelman/rtx3070-workshop-ops --json nameWithOwner,visibility,defaultBranchRef,url
   gh issue list --repo leonbreukelman/rtx3070-workshop-ops --search 'smactorio in:title,body' --json number,title,state,labels,updatedAt --limit 20
   gh pr list --repo leonbreukelman/rtx3070-workshop-ops --search 'smactor' --json number,title,state,headRefName,updatedAt --limit 20
   ```
4. Check branch protection on `main`. If absent/404, record it as a blocker for future autonomous runtime phases, but continue this PR-based bootstrap slice:
   ```bash
   gh api repos/leonbreukelman/rtx3070-workshop-ops/branches/main/protection || true
   ```
5. If the GitHub worktree is dirty, classify changes before touching anything. Do not overwrite unrelated work.

## Phase B — Create/reuse GitHub issue

Search for an existing issue containing either:

- `bootstrap-github-backed-smactorio-source-001`
- `smactor:dedup=bootstrap-github-backed-smactorio-source-001`

If none exists, create exactly one issue in `leonbreukelman/rtx3070-workshop-ops`.

Suggested title:

`Bootstrap SmactorIO/Signal Hub source into GitHub-backed autonomy`

Issue body must include:

```text
Candidate: bootstrap-github-backed-smactorio-source-001
Purpose: package the current safe Signal Hub/SmactorIO source into the existing private GitHub repo without committing runtime state or clobbering unrelated ops files.

<!-- smactor:dedup=bootstrap-github-backed-smactorio-source-001 -->
```

Also include concise acceptance criteria:

- safe source imported under `signal-hub/`;
- no runtime state/secrets/DB/log/cache/backups committed;
- divergence audit committed;
- tests and secret scan pass;
- PR opened, not merged.

Apply labels if they exist. If labels do not exist and creating labels is permitted by auth, create/apply only these low-risk labels:

- `smactorio`
- `type:ops`
- `autonomy:ready`
- `risk:low`

If label creation fails, continue and document it; do not block the bootstrap.

## Phase C — Branch and divergence audit

1. In `/home/leonb/projects/rtx3070-workshop-ops`, fetch and create branch from `origin/main`:
   ```bash
   git fetch origin
   git checkout main
   git pull --ff-only origin main
   git checkout -B smactor/bootstrap-github-backed-autonomy origin/main
   ```
2. Audit current `signal-hub/` subtree before copying:
   - list files currently in GitHub worktree;
   - list files in local source matching the allowlist below;
   - identify local-only, remote-only, and conflicting paths.
3. Write the audit after copying/verification, but collect the before-state now.

## Phase D — Copy only safe allowlisted source

Allowed source mapping from local source to GitHub worktree:

| Local source | GitHub target |
| --- | --- |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/docs/**` | `signal-hub/docs/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/scripts/**` | `signal-hub/scripts/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/tests/**` | `signal-hub/tests/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/public/**` | `signal-hub/public/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/pages.json` | `signal-hub/pages.json` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/data/project_homepages/smactorio.json` | `signal-hub/data/project_homepages/smactorio.json` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/data/smactorio/*.json` | `signal-hub/data/smactorio/*.json` |

Do not copy anything outside this table unless you first write a note explaining why it is required and verify it is safe.

Use add/update only. Do **not** delete remote-only files. Do **not** use `--delete`.

Exclude at minimum:

```text
__pycache__/
*.pyc
state/
logs/
cache/
backups/
*.db
*.sqlite
*.sqlite3
*.db-wal
*.db-shm
.env
.env.*
*credential*
*token*
```

Be careful with the scanner source file `scan_for_secrets.py`: if it is already tracked or needed, inspect content and secret-scan it rather than blindly excluding all safety tooling. The denylist is intended to stop secret-bearing/runtime artifacts, not to remove the scanner from an existing safe source tree.

Recommended copy shape from repo root:

```bash
SRC=/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub
DST=/home/leonb/projects/rtx3070-workshop-ops/signal-hub
mkdir -p "$DST"
rsync -av "$SRC/docs/" "$DST/docs/" --exclude='__pycache__/' --exclude='*.pyc' --exclude='state/' --exclude='logs/' --exclude='cache/' --exclude='backups/' --exclude='*.db' --exclude='*.sqlite' --exclude='*.sqlite3' --exclude='*.db-wal' --exclude='*.db-shm' --exclude='.env' --exclude='.env.*'
rsync -av "$SRC/scripts/" "$DST/scripts/" --exclude='__pycache__/' --exclude='*.pyc'
rsync -av "$SRC/tests/" "$DST/tests/" --exclude='__pycache__/' --exclude='*.pyc'
rsync -av "$SRC/public/" "$DST/public/" --exclude='__pycache__/' --exclude='*.pyc'
install -D -m 0644 "$SRC/pages.json" "$DST/pages.json"
install -D -m 0644 "$SRC/data/project_homepages/smactorio.json" "$DST/data/project_homepages/smactorio.json"
mkdir -p "$DST/data/smactorio"
cp -p "$SRC"/data/smactorio/*.json "$DST/data/smactorio/"
```

After copy, inspect actual git diff. If the copy introduced unsafe files, remove them before staging.

## Phase E — Write divergence/packaging verification artifact

Create:

`/home/leonb/projects/rtx3070-workshop-ops/signal-hub/docs/verification/2026-05-16-bootstrap-divergence.md`

It must include:

- timestamp;
- source path and target repo/path;
- issue number and branch name;
- local-only files selected for import;
- remote-only files preserved untouched;
- conflicting files and disposition;
- staged allowlist;
- explicit statement: no remote-only file deletions in this slice;
- branch protection finding;
- verification commands/results;
- secret scan result;
- rollback path: close PR/delete branch before merge; after merge, revert through a new branch + PR.

## Phase F — Verify before commit

From `/home/leonb/projects/rtx3070-workshop-ops`:

1. Inspect status/diff:
   ```bash
   git status --short
   git diff --stat
   git diff --check
   git diff --name-status -- signal-hub
   ```
2. Confirm no denied runtime paths are staged/tracked in the new diff:
   ```bash
   git diff --name-only -- signal-hub | python3 - <<'PY'
import sys, fnmatch
bad = ['state/*','logs/*','cache/*','backups/*','*.db','*.sqlite','*.sqlite3','*.db-wal','*.db-shm','.env','.env.*','*credential*','*token*']
paths = [p.strip() for p in sys.stdin if p.strip()]
violations = [p for p in paths if any(fnmatch.fnmatch(p.split('signal-hub/',1)[-1], pat) for pat in bad)]
if violations:
    print('\n'.join(violations))
    raise SystemExit(1)
print('denylist check ok')
PY
   ```
3. Run tests from the packaged worktree:
   ```bash
   cd /home/leonb/projects/rtx3070-workshop-ops/signal-hub
   python3 -m unittest tests.test_full_autonomy_fsm tests.test_page_manifest_and_navigation tests.test_smactorio_improvement_runner
   python3 -m unittest discover -s tests -q
   ```
   If the full suite is too slow or fails because of unrelated existing baseline drift, debug root cause and at minimum run all SmactorIO/page/FSM/security tests, documenting any skipped/unrelated cases.
4. Run secret scan from repo root or signal-hub root. Preferred from repo root:
   ```bash
   cd /home/leonb/projects/rtx3070-workshop-ops
   python3 signal-hub/scripts/scan_for_secrets.py signal-hub/docs signal-hub/data/project_homepages signal-hub/data/smactorio signal-hub/public signal-hub/scripts signal-hub/tests
   ```
5. If tests regenerate public HTML timestamps, inspect and keep only intentional generated diffs.
6. Run an independent review before commit. If using subagent, ask it to review only the diff and report safety/packaging issues. Verify its claims yourself.

## Phase G — Commit, push, open PR

Stage explicit pathspecs only. Do not use `git add -A` from the repo root.

Recommended from `/home/leonb/projects/rtx3070-workshop-ops`:

```bash
git add \
  signal-hub/docs \
  signal-hub/scripts \
  signal-hub/tests \
  signal-hub/public \
  signal-hub/pages.json \
  signal-hub/data/project_homepages/smactorio.json \
  signal-hub/data/smactorio

git status --short
git diff --cached --name-status
git diff --cached --check
```

Before committing, inspect `git diff --cached --name-only` against the allowed mapping. Abort if runtime/secret paths appear.

Commit message:

`chore(smactorio): bootstrap github-backed autonomy source`

Use the repo's configured identity unless a local bot identity is already configured. Do not change global git config. If you intentionally set a local bot identity, document it in the divergence note.

Push:

```bash
git push -u origin smactor/bootstrap-github-backed-autonomy
```

Open PR with `gh pr create`. PR body must include:

- issue link / `Closes #N` if appropriate;
- Candidate id;
- what was imported;
- what was intentionally excluded;
- tests run;
- secret scan result;
- divergence artifact path;
- no-main-push / no-self-merge note;
- rollback instructions.

Do not merge.

## Phase H — Final verification and handoff

After PR creation:

1. Fetch the PR metadata:
   ```bash
   gh pr view --repo leonbreukelman/rtx3070-workshop-ops --json number,title,url,state,headRefName,baseRefName,mergeable,statusCheckRollup
   ```
2. Verify GitHub branch exists:
   ```bash
   git ls-remote --heads origin smactor/bootstrap-github-backed-autonomy
   ```
3. Confirm local worktree state. It may be clean or only contain intentional post-PR generated timestamp drift; classify it clearly.
4. Final response to Leon must start with one of:
   - `Implemented and PR opened.`
   - `Partially implemented; blocked only by ...`

Final response must include, in plain English:

- issue URL;
- PR URL;
- branch name;
- what is now GitHub-backed;
- tests/secret scan results;
- whether anything was intentionally excluded;
- whether merge is still waiting for Leon;
- exact blocker if not complete.

Do not end with routine next steps if you can complete them with tools. Stop only after the PR exists or a true blocker is recorded.
