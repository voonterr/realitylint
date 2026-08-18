# RealityLint roadmap

> [English](README.md) · [Русский](README.ru.md)

RealityLint grows through **small deterministic rules** rather than trying to become a general-purpose shell or natural-language interpreter.

## v0.5 — Project Truth

- [x] Multi-document scanning.
- [x] Docker Compose file/service/env-file/profile/nearby-port verification.
- [x] Environment-variable documentation drift.
- [x] Go `go run` local-target and version-claim checks.
- [x] Rust/Cargo manifest, binary, feature and MSRV-claim checks.
- [x] `.realitylint.toml` docs/severity configuration.
- [x] Ignore directives for intentional examples.
- [x] Baseline mode for incremental adoption.
- [x] `init`, `rules`, `explain` CLI commands.
- [x] pre-commit metadata.
- [x] JUnit output.

## v0.6 — Deeper ecosystem facts

- Go module-path claims and deeper workspace/module discovery.
- Rust workspace-aware package resolution and target discovery.
- Docker Compose dynamic/interpolated port and multi-file merge verification.
- Environment-variable ownership by service/subproject instead of project-wide union.
- Better monorepo package discovery.

## v0.7 — Developer workflow

- CLI flag verification using generated `--help` snapshots.
- Richer SARIF rule help and end-column locations.
- Optional changed-files mode for very large repositories.
- Rule documentation pages with good/bad examples.
- Baseline pruning/refresh commands.

## v1.0 criteria

- Stable rule IDs and config schema.
- Cross-platform CI coverage on supported Python versions.
- Low false-positive rate validated on a representative public-repository fixture set.
- Stable GitHub Action and pre-commit contracts.
- Clear migration policy for rule behavior changes.

## Non-goals

- Executing arbitrary commands from documentation.
- Using an LLM as the source of truth for findings.
- Claiming a project "works" based only on documentation text.
- Replacing ecosystem-specific linters or test suites.
