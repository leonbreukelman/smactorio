# SmactorIO

SmactorIO is Leon's bounded-autonomy GitHub issue runtime. It was extracted from `leonbreukelman/rtx3070-workshop-ops` into this standalone checkout so the control plane can evolve independently from the rtx3070 workshop repository.

## What is in this repo

- `scripts/smactorio_issue_foreman.py` — issue claim, worker launch, verification, PR, merge, and issue-completion lifecycle.
- `scripts/smactorio_policy.py` — repo-specific safety policy for the rtx3070 workshop lane; unsupported repositories fail closed.
- `scripts/check_path_scope.py` and `scripts/scan_for_secrets.py` — trusted guardrails used before worker changes are accepted.
- `scripts/page_shell.py` and `pages.json` — local shell/manifest support for the extracted SmactorIO generated pages.
- `infra/systemd/` — rtx3070 service/timer units updated to run from `/home/leonb/projects/smactorio`.
- `docs/`, `public/`, `data/`, `config/` — extracted SmactorIO specs, plans, evidence, generated pages, and runtime configuration fixtures.

The default target repo remains `leonbreukelman/rtx3070-workshop-ops`; the runtime checkout is now separate. The former Hermes fork-sync lane has been retired, so SmactorIO no longer publishes or processes `leonbreukelman/hermes-agent` fork-sync tickets.

## Local verification

```bash
python3 -m unittest discover -s tests -q
```

Dry-run the foreman against the default target repo:

```bash
python3 scripts/smactorio_issue_foreman.py --dry-run
```

Regenerate the extracted SmactorIO HTML pages:

```bash
python3 scripts/build_smactorio_simple_roadmap_page.py
python3 scripts/build_smactorio_full_autonomy_page.py
python3 scripts/build_smactorio_operating_contract_page.py
```

Override the target repo/checkouts when needed:

```bash
SMACTORIO_REPO=owner/repo \
SMACTORIO_REPO_ROOT=/path/to/target/repo \
python3 scripts/smactorio_issue_foreman.py --dry-run
```

## rtx3070 service install

The install script uses this standalone checkout for unit files and scripts:

```bash
SMACTORIO_HOME=/home/leonb/projects/smactorio scripts/install_smactorio_service.sh
```

That script writes the dedicated SmactorIO env under `/home/leonb/.config/smactorio`, installs `/etc/systemd/system/smactorio.service`, and enables `smactorio.timer`.

## Provenance

Initial extraction source:

- Repo: `leonbreukelman/rtx3070-workshop-ops`
- Worktree: `/home/leonb/projects/rtx3070-workshop-ops-kanban-p9`
- Commit: `f07703543bc53a7c08f32bc901c25ba8fbed4869`
- Extracted at: `2026-06-14T01:55:52Z`
