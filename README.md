<div align="center">

<img src="docs/assets/banner.svg" alt="RealityLint — documentation drift detector" width="100%" />

# RealityLint

**Your docs describe the project. RealityLint checks the claims the repository can actually prove.**

Static, deterministic documentation-vs-repository verification — **no command execution, no LLM, no API key, no code upload.**

**by [@voonterr](https://github.com/voonterr)**

[English](README.md) · [Русский](README.ru.md)

[![CI](https://github.com/voonterr/realitylint/actions/workflows/ci.yml/badge.svg)](https://github.com/voonterr/realitylint/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/realitylint.svg?logo=pypi&logoColor=white)](https://pypi.org/project/realitylint/)
[![License: MIT](https://img.shields.io/badge/license-MIT-7C3AED.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/voonterr/realitylint?style=flat)](https://github.com/voonterr/realitylint/stargazers)

`local-first` · `deterministic` · `multi-doc` · `Docker` · `Go` · `Rust` · `CI-ready`

</div>

---

## Why this exists

Documentation drifts because code changes faster than prose.

A script is renamed, a path moves, `.env.example` stops matching reality, a Docker Compose service disappears, or a Cargo feature is removed — while the setup guide still looks perfectly valid.

Markdown linters validate Markdown. RealityLint validates a different thing:

> **Do the concrete claims in the documentation still match repository facts?**

RealityLint deliberately stays conservative. If a claim cannot be verified deterministically from local files, it is skipped instead of guessed.

## 30-second demo

<p align="center">
  <img src="docs/assets/demo.gif" alt="RealityLint demo" width="900" />
</p>

```bash
python -m pip install realitylint
realitylint .
```

For a broader project scan:

```bash
realitylint . --all-docs
```

## v0.5: Project Truth

RealityLint v0.5 expands from a README checker into a project-wide documentation drift engine.

Highlights:

- **multi-document scanning** for `README*.md`, `docs/**/*.md`, `CONTRIBUTING.md`, and custom globs;
- **Docker Compose drift**: Compose-file availability, documented services, missing `env_file` paths, profiles, and nearby localhost-port mismatches;
- **environment-variable drift** between docs, `.env.example` / `.env.sample`, and common source-code access patterns;
- **Go checks** for local `go run` targets and Go-version claim drift;
- **Rust/Cargo checks** for manifests, `--bin`, `--features`, and MSRV claim drift;
- **inline ignore directives** for intentionally broken examples;
- optional **`.realitylint.toml`** rule severity and docs configuration;
- **baseline mode** for adopting RealityLint in an existing repository without fixing every old finding first;
- `realitylint init`, `realitylint rules`, and `realitylint explain RLxxx`;
- **JUnit XML** in addition to text, JSON, Markdown, and SARIF;
- **pre-commit** integration;
- richer GitHub Action inputs for all-docs/custom-doc scans.

See [RELEASE_NOTES_v0.5.0.md](RELEASE_NOTES_v0.5.0.md) for the release overview.

## What it checks

| Rule | Verification |
|---|---|
| `RL000` | Repository/document scan preconditions are safe and readable |
| `RL001` | npm/pnpm/yarn/bun package scripts exist |
| `RL002` | Relative Markdown links/images point to real local paths |
| `RL003` | Documented `.env.example` / `.env.sample` copy sources exist |
| `RL004` | Package-manager commands agree with the lockfile family |
| `RL005` | Python entry-file commands point to real files |
| `RL006` | Documented Make targets exist |
| `RL007` | Pinned self-install versions match `pyproject.toml` |
| `RL008` | A claimed common license has a real LICENSE/COPYING file |
| `RL009` | Obvious inline repository paths still exist *(notice)* |
| `RL010` | Malformed/unreadable metadata is reported safely |
| `RL011` | A documented Docker Compose command has a readable Compose file |
| `RL012` | Docker Compose services named in docs actually exist |
| `RL013` | Compose `env_file` paths exist |
| `RL014` | Explicitly documented environment variables exist in env templates |
| `RL015` | Local `go run` targets exist and contain Go source |
| `RL016` | Documented Cargo commands have a readable `Cargo.toml` |
| `RL017` | `cargo run --bin NAME` points to a defined binary |
| `RL018` | Cargo features named in docs exist in `[features]` |
| `RL019` | Docker Compose profiles named with `--profile` are declared |
| `RL020` | Nearby documented localhost ports match Compose-published host ports |
| `RL021` | Human-readable Go version claims stay aligned with `go.mod` |
| `RL022` | Human-readable Rust version claims stay aligned with Cargo `rust-version` |

List rules from the installed CLI:

```bash
realitylint rules
realitylint explain RL012
```

## Scan one document or the project

Primary README only (backward compatible):

```bash
realitylint .
```

Common project documentation:

```bash
realitylint . --all-docs
```

Custom documentation globs:

```bash
realitylint . --docs "README*.md,docs/**/*.md"
```

The original document-relative behavior is preserved: local links inside nested docs are resolved relative to that document.

## Configuration

RealityLint remains zero-config by default. For larger repositories, add `.realitylint.toml`:

```toml
[realitylint]
docs = ["README*.md", "docs/**/*.md"]
exclude = ["docs/vendor/**"]

[severity]
RL009 = "off"
RL014 = "warning"
```

Valid severity values are `error`, `warning`, `notice`, and `off`.

Bootstrap a repository with a config and a GitHub Actions workflow:

```bash
realitylint init
```

## Intentional examples / ignore directives

Documentation sometimes contains deliberately invalid examples. Suppress only the relevant line instead of disabling a rule globally:

```text
<!-- realitylint-ignore-next-line RL012 -->
<an intentionally invalid Compose example>
```

Block-level directives are also supported:

```text
<!-- realitylint-disable RL014 -->
...
<!-- realitylint-enable RL014 -->
```

## Baseline mode

Large established repositories can adopt RealityLint incrementally.

Create a baseline from current findings:

```bash
realitylint . --all-docs --write-baseline
```

The generated `.realitylint-baseline.json` is automatically used on later scans. Existing findings are suppressed; new documentation drift still fails CI.

Disable automatic baseline use when needed:

```bash
realitylint . --no-baseline
```

## GitHub Actions

```yaml
name: Documentation reality check
on: [pull_request]

permissions:
  contents: read

jobs:
  realitylint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: voonterr/realitylint@v1
        with:
          all-docs: "true"
          fail-on: error
```

The Action emits inline annotations and a Markdown job summary. Inputs are passed through environment variables rather than interpolated directly into shell commands.

## pre-commit

```yaml
repos:
  - repo: https://github.com/voonterr/realitylint
    rev: v0.5.0
    hooks:
      - id: realitylint
```

## Output formats

```bash
realitylint . --format text
realitylint . --format json
realitylint . --format markdown
realitylint . --format sarif
realitylint . --format junit
```

CI policy:

```bash
realitylint . --fail-on error
realitylint . --fail-on warning
realitylint . --fail-on never
```

Machine-readable formats keep stdout clean.

## Safety model

RealityLint is a **static checker**, not a sandbox.

- Documentation commands are parsed, **never executed**.
- No LLM is used as the source of truth.
- No API key or external service is required for scanning.
- Source code and docs remain local.
- Repository path containment and file-size limits are enforced by the legacy/core rules.
- Ambiguous claims are skipped rather than invented.
- GitHub workflow annotations escape workflow-command control characters.
- Third-party Actions used by this repository are pinned to immutable commit SHAs.

Found a security issue? Please read [SECURITY.md](SECURITY.md).

## Philosophy

1. **Evidence over vibes.** Every finding should be backed by repository evidence.
2. **No arbitrary execution.** Docs can contain hostile commands; RealityLint never runs them.
3. **Prefer silence to false certainty.** A deterministic checker should not pretend to understand what it cannot prove.
4. **Zero-config first, configurable when needed.** Small repos should work immediately; larger repos can tune severity and scope.
5. **Rules stay isolated and testable.** New ecosystems should be easy to add without turning the scanner into a shell interpreter.

See [ROADMAP.md](ROADMAP.md) for what comes next.

## Contributing

Bug reports, rule ideas, false-positive reports and pull requests are welcome.

```bash
python -m unittest discover -s tests -v
```

Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

RealityLint v0.5 is **beta software**. The project intentionally covers a finite set of deterministic claims instead of trying to understand arbitrary natural language.

## Author

Created and maintained by **[@voonterr](https://github.com/voonterr)**.

If RealityLint catches real documentation drift in your project, ⭐ starring the repository helps other developers discover it.

## License

MIT License. Copyright © 2026 voonterr. See [LICENSE](LICENSE).
