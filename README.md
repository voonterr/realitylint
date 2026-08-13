<div align="center">

<img src="docs/assets/banner.svg" alt="RealityLint — README drift detector" width="100%" />

# RealityLint

**Your README says it works. RealityLint checks if it actually does.**

Static, deterministic README-vs-repository verification — **without executing README commands, without an LLM, and without sending your code anywhere.**

**by [@voonterr](https://github.com/voonterr)**

[English](README.md) · [Русский](README.ru.md)

[![CI](https://github.com/voonterr/realitylint/actions/workflows/ci.yml/badge.svg)](https://github.com/voonterr/realitylint/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-7C3AED.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/voonterr/realitylint?style=flat)](https://github.com/voonterr/realitylint/stargazers)

`local-first` · `no API key` · `no LLM` · `CI-ready` · `safe static analysis`

</div>

---

## The problem

README files drift.

A command gets renamed. A file moves. `.env.example` disappears. The project switches from Yarn to npm. AI-generated documentation confidently describes a script that never existed.

Most Markdown linters can tell you whether the document is formatted correctly. RealityLint asks a different question:

> **Do the locally verifiable claims in this README still match the repository?**

It stays deliberately conservative: if a claim cannot be proven from local repository evidence, RealityLint skips it instead of guessing.

## 30-second demo

<p align="center">
  <img src="docs/assets/demo.gif" alt="RealityLint terminal demo" width="900" />
</p>

```bash
realitylint examples/broken-project --fail-on never
```

```text
RealityLint v0.1.2 — by @voonterr
RealityLint score: 34/100

✗ README.md:3 ERROR   RL002 Documented local link target "docs/setup.md" does not exist.
! README.md:6 WARNING RL004 README uses yarn, but the repository has only an npm lockfile.
✗ README.md:7 ERROR   RL001 Documented package script "dev" is not defined in package.json.
✗ README.md:8 ERROR   RL003 Documented environment template ".env.example" does not exist.
✗ README.md:9 ERROR   RL005 Documented Python entry file "scripts/start.py" does not exist.

4 error(s), 1 warning(s), 0 notice(s).
```

## Why RealityLint?

| | RealityLint |
|---|---|
| **Deterministic** | Same repository → same result. No model randomness. |
| **Safe by design** | Parses commands from docs but never executes them. |
| **Private** | Your repository never leaves the machine. |
| **CI-friendly** | Text, JSON, Markdown and SARIF output. |
| **Low false-positive bias** | Ambiguous claims are skipped instead of guessed. |
| **Monorepo-aware** | Understands common working-directory forms such as `cd frontend && ...`. |

## What it checks

| Rule | Verification |
|---|---|
| `RL000` | Repository/README scan preconditions are safe and readable |
| `RL001` | npm/pnpm/yarn/bun package scripts exist in the relevant `package.json` |
| `RL002` | Relative Markdown links and images point to real local paths |
| `RL003` | Documented `.env.example` / `.env.sample` files exist |
| `RL004` | Package-manager commands agree with the detected lockfile family |
| `RL005` | Python entry-file commands point to real files |
| `RL006` | Documented Make targets exist in GNUmakefile/makefile/Makefile |
| `RL007` | Pinned self-install versions agree with `[project].version` |
| `RL008` | A claimed common license has a real LICENSE/COPYING file |
| `RL009` | Obvious inline repository paths still exist *(notice)* |
| `RL010` | Malformed/unreadable package metadata is reported instead of crashing |

RealityLint also understands common `cd subdir && ...` flows, `npm --prefix`, `yarn --cwd`, `pnpm --dir` / `pnpm -C`, `bun --cwd`, `make -C`, nested README link bases, Windows-style path separators/prompts, backtick/tilde shell fences and inline shell commands.

## Quick start

**Requires Python 3.10+.**

```bash
git clone https://github.com/voonterr/realitylint.git
cd realitylint
python -m pip install -e .
realitylint .
```

Or run it from the source checkout without installing the console script:

```bash
python -m realitylint /path/to/repository
```

Try the intentionally broken fixture:

```bash
realitylint examples/broken-project --fail-on never
```

## GitHub Actions

Add this to `.github/workflows/realitylint.yml` in another repository:

```yaml
name: README reality check
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
          fail-on: error
```

The action emits inline annotations and a Markdown job summary.

> **Note:** `voonterr/realitylint@v1` becomes usable after the first `v1` tag is published. See [PUBLISH.md](PUBLISH.md) for the release checklist.

## Output formats

```bash
realitylint . --format text
realitylint . --format json
realitylint . --format markdown
realitylint . --format sarif
```

CI failure policy:

```bash
realitylint . --fail-on error
realitylint . --fail-on warning
realitylint . --fail-on never
```

Machine-readable formats keep stdout clean — the `by @voonterr` banner does not corrupt JSON or SARIF output.

## Security model

RealityLint is intentionally a **static checker**, not a sandbox.

- README commands are parsed, **never executed**.
- `--readme` cannot escape the repository root.
- Symlink/path resolution is contained before files are read.
- README and metadata files have size limits to reduce memory/regex abuse.
- GitHub Action inputs are passed through environment variables instead of direct shell interpolation.
- GitHub annotations escape workflow-command control characters.
- Third-party Actions used by this repository are pinned to immutable commit SHAs.
- No network access is required for the scanner itself.

Found a security issue? Please read [SECURITY.md](SECURITY.md) instead of opening a public exploit report.

## Project philosophy

1. **Evidence over vibes.** Every finding should point to repository evidence.
2. **No arbitrary execution.** Documentation commands are parsed, never run.
3. **Prefer silence to a false accusation.** Ambiguous syntax is skipped.
4. **Local-first.** Source code and docs stay on the user's machine.
5. **Small rules, easy contributions.** Ecosystem checks should remain isolated and testable.

## Roadmap

Near-term priorities:

- [ ] Go: `go run`, module path and toolchain claims
- [ ] Rust: `cargo run --bin`, features and MSRV claims
- [ ] Docker Compose service/port verification
- [ ] `.env` variable drift: code ↔ template ↔ docs
- [ ] pre-commit hook
- [ ] ignore directives for intentional examples
- [ ] CLI flag verification from generated `--help` snapshots

See the detailed [ROADMAP.md](ROADMAP.md).

## Contributing

Bug reports, rule ideas and pull requests are welcome.

```bash
python -m unittest discover -s tests -v
```

Start with [CONTRIBUTING.md](CONTRIBUTING.md). New contributors can also open a rule request using the repository issue template.

## Status

RealityLint is currently **alpha software**. Its checks are intentionally narrow and deterministic. It will not understand every shell expression or every documentation style — and it should not pretend to.

## Author

Created and maintained by **[@voonterr](https://github.com/voonterr)**.

If RealityLint saves you from a broken README, consider ⭐ starring the repository — it helps other developers discover the project.

## License

MIT License. Copyright © 2026 voonterr. See [LICENSE](LICENSE).
