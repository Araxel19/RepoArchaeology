# Caveman Mode — Level: Lite

Default Intensity Level: **lite**

## Rules
- Remove filler words, hedging, and conversational fluff.
- Keep articles (a/an/the) and full sentence structures.
- Maintain professional, direct, and 100% technically precise explanations and code.
- Examples:
  - Normal: "You should probably sanitize the path before passing it to git subprocess to avoid issues."
  - Lite: "Sanitize path before git subprocess. Prevents path traversal."

## Verification Rule
- Always execute `pytest` and verify that all unit tests pass with 0 errors before completing any task.
- Run `python3 -m py_compile` on all modified Python files to ensure 0 syntax errors.

## Test Layout Rule

**Never drop a test file in `tests/` root without purpose.** Tests live in a folder structure that mirrors the code under test:

| Test Folder | Covers |
| :--- | :--- |
| `tests/core/` | `repoarchaeology/core/` — security, configuration, models |
| `tests/engines/` | `repoarchaeology/engines/` — git mining, AST parser, AI synthesizer |
| `tests/cli/` | `repoarchaeology/cli/` — command entrypoints and options |
| `tests/exporters/` | `repoarchaeology/exporters/` — markdown, html, json generators |

**What earns a test:**
- Core git mining logic, churn formulas, coupling co-occurrence metrics.
- Security routines: path traversal sanitization, secret/token redaction.
- AI engine fallbacks: graceful degradation when offline or when Ollama/APIs fail.
- Subprocess execution safety: timeouts, non-zero exit codes, detached HEAD states.

## Security & Subprocess Rule

1. **Never execute shell commands with `shell=True`.** All calls to `git` or external binaries must pass argument lists (`['git', '-C', repo, 'log', ...]`) to prevent command injection.
2. **Every subprocess call must define a strict `timeout`** (default 45s). Hanging git processes on corrupted repos or locks must never hang the CLI.
3. **Always pass raw text through `redact_secrets()` before rendering or exporting.** Commits containing API keys (`AIza...`, `ghp_...`, `sk-...`, `Bearer...`) must be masked unconditionally.
4. **All paths must be validated with `sanitize_path()`.** User inputs like `--path` or file arguments must be resolved against real directory boundaries.

## Git & Mining Performance Rule

1. **Never load the entire git log into memory at once on huge repositories.** Use batching and limit queries (`-n <max_commits>`).
2. **Handle empty or freshly initialized repositories gracefully.** A repository with 0 commits or 1 commit must not throw an unhandled `IndexError` or division by zero.
3. **Filter merge commits where appropriate.** Merge commits inflate churn counts without adding domain code modifications unless specifically inspecting integration branches.

## AI Engine & Offline-First Invariant

1. **RepoArchaeology must work 100% offline out of the box.** The `DeterministicHeuristicEngine` is the baseline guarantee: if Ollama is down and no API keys exist, all commands (`doctor`, `churn`, `coupling`, `lore`, `scan`) must deliver complete, useful, formatted analysis without crashing.
2. **Default lightweight model:** When local AI is enabled, the recommended standard model is `qwen2.5-coder:1.5b` (ultra-fast, ~980MB RAM footprint, excellent code comprehension).
3. **Structured Outputs:** When calling remote LLMs (Gemini / OpenAI), enforce JSON Schema / Structured Outputs to avoid hallucinations in quantitative metrics.

## Documentation Integrity & Sync Rule

Whenever you implement significant logic updates, new CLI subcommands, or engine capabilities:
1. **Update affected documentation files immediately**: `README.md`, `CONTRIBUTING.md`, `docs/`, and `CHANGELOG.md`.
2. **Never leave obsolete descriptions as truth**: Keep option flags, default model names, and command examples 100% aligned with the actual Python codebase.
