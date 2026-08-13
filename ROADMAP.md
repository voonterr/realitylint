# RealityLint roadmap

> [English](README.md) · [Русский](README.ru.md)

RealityLint grows by adding **small, deterministic checks** rather than trying to become a general-purpose shell interpreter.

## v0.2 — More ecosystems

- Go: `go run`, module path and toolchain claims.
- Rust: `cargo run --bin`, features and MSRV claims.
- Docker Compose: documented services and ports.
- Better monorepo package discovery.

## v0.3 — Documentation drift

- `.env` variable drift across source, templates and docs.
- CLI flag verification using generated `--help` snapshots.
- Ignore directives for intentionally broken examples.
- Config file for rule severity and exclusions.

## v0.4 — Developer workflow

- pre-commit integration.
- Baseline files for incremental adoption.
- Improved SARIF locations and GitHub code scanning examples.
- Rule documentation pages with good/bad examples.

## Non-goals

- Executing arbitrary commands from README files.
- Using an LLM as the source of truth for findings.
- Claiming that a project "works" based only on documentation text.
- Becoming a replacement for ecosystem-specific linters or test suites.

## Русский

RealityLint будет развиваться через **небольшие детерминированные проверки**, а не через попытку интерпретировать любой shell-код.

Ближайшие цели: Go, Rust, Docker Compose, проверка `.env`, pre-commit, конфигурация правил и более удобная интеграция с SARIF/GitHub Code Scanning.

Главный принцип остаётся прежним: команды из README не выполняются, LLM не используется как источник истины, неоднозначные случаи лучше пропустить, чем выдать ложную ошибку.
