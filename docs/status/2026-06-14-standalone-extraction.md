# SmactorIO standalone extraction

Date: 2026-06-14T01:55:52Z

## Source

- Source repo: `leonbreukelman/rtx3070-workshop-ops`
- Source worktree: `/home/leonb/projects/rtx3070-workshop-ops-kanban-p9`
- Source commit: `f07703543bc53a7c08f32bc901c25ba8fbed4869`
- Destination: `/home/leonb/projects/smactorio`

## Extraction scope

Copied tracked SmactorIO control-plane files from `signal-hub/` into the standalone project root:

- SmactorIO runtime scripts, policy, guardrails, and Hermes fork-sync checker.
- SmactorIO generated-page helpers (`scripts/page_shell.py`) and a standalone SmactorIO `pages.json` manifest.
- SmactorIO unit tests and fixtures.
- SmactorIO specs, plans, verification docs, public pages, data, and config fixtures.
- SmactorIO systemd units.

Created standalone project metadata:

- `README.md`
- `pyproject.toml`
- `.gitignore`
- `.github/workflows/smactorio-guardrails.yml`

## Path changes

- Runtime script checkout path changed from `/home/leonb/projects/rtx3070-workshop-ops/signal-hub` to `/home/leonb/projects/smactorio`.
- The default target repo root remains `/home/leonb/projects/rtx3070-workshop-ops` because the original lane still operates on that repo unless overridden.
- Systemd units now execute SmactorIO from `/home/leonb/projects/smactorio` while still granting the worker lane access to the target repos it mutates.

## Verification

Run from `/home/leonb/projects/smactorio`:

```bash
python3 -m unittest discover -s tests -q
python3 scripts/smactorio_issue_foreman.py --dry-run
python3 scripts/build_smactorio_simple_roadmap_page.py
python3 scripts/build_smactorio_full_autonomy_page.py
python3 scripts/build_smactorio_operating_contract_page.py
```
