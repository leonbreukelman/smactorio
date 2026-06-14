# Model/backend discovery — SmactorIO reliability hardening — 2026-05-19

## Scope

Discovery for the required model ensemble before writing the SmactorIO hardening spec/plan.

## Installed/configured tools found

- Gemini CLI: `/home/leonb/.nvm/versions/node/v24.13.1/bin/gemini`, version `0.42.0`.
  - Health probe: succeeded.
  - Observed default model in probe stats: `gemini-3.1-pro-preview`.
  - Used for broad research/synthesis in `2026-05-19-smactorio-model-research-gemini.md`.
- GitHub Copilot CLI: `/home/leonb/.nvm/versions/node/v24.13.1/bin/copilot`, version `1.0.48`.
  - Health probe: succeeded.
  - CLI did not surface exact model name.
  - stdin-context probe timed out; fallback used a read-only prompt that asked Copilot to read `/tmp/smactorio-phase2/model-context.md` with tools.
  - Used for PR/workflow/branch-protection review in `2026-05-19-smactorio-model-audit-copilot.md`.
- Claude Code CLI: `/home/leonb/.local/bin/claude`, version `2.1.143`.
  - Health probe with `--model opus --effort max --tools ''` succeeded.
  - Used as Claude Opus adversarial pre-spec reviewer in `2026-05-19-smactorio-opus-spec-review.md`.
- Codex CLI: `/home/leonb/.nvm/versions/node/v24.13.1/bin/codex`, version `0.131.0`.
  - Requested `gpt-5.1-codex-mini` probe failed: unsupported for this ChatGPT-account Codex configuration.
  - Fallback default Codex CLI model succeeded: `gpt-5.5`, provider `openai`, read-only sandbox.
  - Used for implementation hazard/test-gap audit in `2026-05-19-smactorio-model-audit-codex.md`.

## Not found / not used

- `opencode`, `aider`, `goose`, `amp`, `qwen`, `openai`, and `cursor` were not present on PATH during discovery.
- `ollama` was not present on PATH and no Ollama model list was available.
- Local ports showed unrelated listeners and no confirmed local LLM backend was selected.
- OpenRouter was not used.

## Credential handling

Discovery recorded credential presence only when command output exposed environment names. Secret values were not copied into these docs and must be represented as `[REDACTED]` if encountered.
