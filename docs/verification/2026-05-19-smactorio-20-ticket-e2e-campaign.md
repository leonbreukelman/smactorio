# SmactorIO 20-Ticket E2E Campaign Verification

Date: 2026-05-19
Repo: `leonbreukelman/rtx3070-workshop-ops`
Runtime host: `rtx3070`

## Result

- Total real GitHub tickets processed: 20
- Passed terminal outcomes: 20
- Failed terminal outcomes: 0
- Manual issue closures counted as passes: 0
- Campaign execution mode: one real GitHub issue at a time, deterministic foreman invocation with the production SmactorIO worker contract and GitHub PR/merge flow.
- Raw campaign ledger: `state/runtime evidence on rtx3070: smactorio/e2e/2026-05-19-smactorio-20-ticket-e2e-campaign.jsonl`

The campaign initially exposed a worker/foreman contract loop on CASE-01. That root cause was fixed in PR #46 before the campaign continued. CASE-01 was then rerun through SmactorIO and reached a passing terminal merged-PR outcome.

## Pass Criteria Applied

A case counted as passed only when all of the following were true:

1. A real GitHub issue was opened or selected.
2. SmactorIO claimed or otherwise processed the issue.
3. The issue reached a terminal success outcome: merged PR closing the issue, or structured already-satisfied close with evidence and no artifact-only PR.
4. The final issue state was closed with `smactorio:done`.
5. No final issue retained `smactorio:blocked` or `smactorio:claimed`.
6. No supervising-agent manual closure was used as a pass.

## Case Matrix

| Case | Issue | Expected behavior | Worker claim evidence | PR | Merge commit | Final state / labels | Logs / evidence | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CASE-01 | [#45](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/45) | normal low-risk docs change closes through PR; also exercised stale blocked recovery after hardening | Foreman status `merged`; issue comments: 5 | [47](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/47) | `041911d6ae4b` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-45-20260519t0.md` | PASS |
| CASE-02 | [#48](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/48) | normal low-risk test fixture change | Foreman status `merged`; run `20260519T052223-18b0dffff9d8c168`; issue comments: 2 | [49](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/49) | `b9a81557319d` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-48-20260519t0.md` | PASS |
| CASE-03 | [#50](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/50) | generated verification command run_tests default | Foreman status `merged`; run `20260519T052423-18b0e01be1c17d01`; issue comments: 2 | [51](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/51) | `4a619d94acd1` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-50-20260519t0.md` | PASS |
| CASE-04 | [#52](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/52) | verification command verbose flag | Foreman status `merged`; run `20260519T052603-18b0e03334b3f1a8`; issue comments: 2 | [53](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/53) | `f6d5366bc163` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-52-20260519t0.md` | PASS |
| CASE-05 | [#54](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/54) | pytest selector translation | Foreman status `merged`; run `20260519T052759-18b0e04e3e1a25ac`; issue comments: 2 | [55](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/55) | `7d2770958be6` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-54-20260519t0.md` | PASS |
| CASE-06 | [#56](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/56) | directory selector verification | Foreman status `merged`; run `20260519T052955-18b0e0692d8e0f8b`; issue comments: 2 | [57](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/57) | `87850dfc3786` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-56-20260519t0.md` | PASS |
| CASE-07 | [#58](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/58) | ambiguous selector handling note | Foreman status `merged`; run `20260519T053251-18b0e09256c41146`; issue comments: 2 | [59](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/59) | `2b7820819a99` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-58-20260519t0.md` | PASS |
| CASE-08 | [#60](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/60) | generated public drift cleanup note | Foreman status `merged`; run `20260519T053502-18b0e0b0c68f8369`; issue comments: 2 | [61](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/61) | `2834c1a1ac45` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-60-20260519t0.md` | PASS |
| CASE-09 | [#62](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/62) | diff check whitespace auto repair note | Foreman status `merged`; run `20260519T053636-18b0e0c69b31b7cd`; issue comments: 2 | [63](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/63) | `d4f3cc4a4a73` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-62-20260519t0.md` | PASS |
| CASE-10 | [#64](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/64) | unknown source change correction note | Foreman status `merged`; run `20260519T053840-18b0e0e37fd4e92c`; issue comments: 2 | [65](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/65) | `24903227cbbb` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-64-20260519t0.md` | PASS |
| CASE-11 | [#66](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/66) | new executable script bit | Foreman status `merged`; run `20260519T054035-18b0e0fe30d623bb`; issue comments: 2 | [67](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/67) | `e2b02b558647` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-66-20260519t0.md` | PASS |
| CASE-12 | [#68](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/68) | outside scope corrected to allowed docs | Foreman status `merged`; run `20260519T054228-18b0e118856cfc5d`; issue comments: 2 | [69](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/69) | `512b2e48a912` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-68-20260519t0.md` | PASS |
| CASE-13 | [#70](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/70) | guardrail failure remediation note | Foreman status `merged`; run `20260519T054419-18b0e1327afb2d6c`; issue comments: 2 | [71](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/71) | `64c1e28c8705` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-70-20260519t0.md` | PASS |
| CASE-14 | [#72](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/72) | review comment amendment note | Foreman status `merged`; run `20260519T054608-18b0e14bdc28b990`; issue comments: 2 | [73](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/73) | `a23a8b3823ef` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-72-20260519t0.md` | PASS |
| CASE-15 | [#74](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/74) | branch protection update note | Foreman status `merged`; run `20260519T054753-18b0e1645cdd2e00`; issue comments: 2 | [75](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/75) | `58e972ba900d` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-74-20260519t0.md` | PASS |
| CASE-16 | [#76](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/76) | open duplicate already satisfied | Foreman status `already_satisfied`; run `20260519T054942-18b0e17d9158a410`; issue comments: 2 | none - structured already-satisfied close | none | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `issue terminal comment + foreman run ledger` | PASS |
| CASE-17 | [#77](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/77) | closed duplicate already satisfied | Foreman status `already_satisfied`; run `20260519T055019-18b0e1862bfe3dda`; issue comments: 2 | none - structured already-satisfied close | none | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `issue terminal comment + foreman run ledger` | PASS |
| CASE-18 | [#78](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/78) | already satisfied no artifact PR | Foreman status `already_satisfied`; run `20260519T055102-18b0e19053812865`; issue comments: 2 | none - structured already-satisfied close | none | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `issue terminal comment + foreman run ledger` | PASS |
| CASE-19 | [#79](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/79) | stale blocked label recovery | Foreman status `merged`; run `20260519T055146-18b0e19a72ba62aa`; issue comments: 3 | [80](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/80) | `efbcf6aff033` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-79-20260519t0.md` | PASS |
| CASE-20 | [#81](https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/81) | restart recovery note | Foreman status `merged`; run `20260519T055503-18b0e1c8636603df`; issue comments: 2 | [82](https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/82) | `9f76e619001e` | CLOSED / `smactorio`, `autonomy:ready`, `risk:low`, `smactorio:done`, `smactorio:e2e` | `signal-hub/docs/verification/2026-05-19-smactorio-issue-81-20260519t0.md` | PASS |

## Campaign Notes

- Cases 01-15 and 19-20 exercised merged-PR terminal outcomes.
- Cases 16-18 exercised the structured already-satisfied path with no PR and no artifact-only commit.
- CASE-19 was seeded with a stale `smactorio:blocked` label and passed only after SmactorIO recovered it and completed the ticket.
- All 20 final issues are closed and have `smactorio:done`; none retain `smactorio:blocked` or `smactorio:claimed`.
- The generated verification artifacts are repo-relative and intentionally exclude credentials or raw token-bearing output.

## Root-Cause Fix Provenance Used During Campaign

- PR #46 fixed retryable blocked-label recovery and worker structured-outcome parsing after CASE-01 exposed the failure loop.
- Codex focused re-review verdict for PR #46: ACCEPT.
- PR #47 reran CASE-01 through SmactorIO successfully after PR #46 landed.
