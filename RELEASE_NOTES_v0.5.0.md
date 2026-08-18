# RealityLint v0.5.0 — Project Truth

RealityLint v0.5 is the first project-wide documentation drift release.

The original rules remain deterministic and backward compatible, while the new engine can scan multiple docs and verify additional ecosystems without executing documentation commands.

## Major additions

- Multi-document scan engine: `--all-docs` and custom `--docs` globs.
- Docker Compose rules: Compose file, documented services, `env_file` paths, profiles, and nearby localhost-port drift.
- Environment-variable drift across explicit documentation mentions, env templates, and common source access patterns.
- Go `go run` local-target verification and Go-version claim drift against `go.mod`.
- Rust/Cargo manifest, binary, feature, and MSRV claim verification.
- `.realitylint.toml` docs scope and severity overrides.
- Inline ignore/disable/enable directives.
- Baseline generation and automatic baseline filtering.
- `realitylint init`, `rules`, and `explain` commands.
- JUnit XML output.
- pre-commit hook metadata.
- Expanded GitHub Action inputs and project-wide Job Summary.

## New rules

- `RL011` Docker Compose file exists/readable.
- `RL012` documented Docker Compose service exists.
- `RL013` Compose `env_file` exists.
- `RL014` documented environment variable exists in env templates.
- `RL015` local `go run` target exists.
- `RL016` Cargo manifest exists/readable.
- `RL017` Cargo binary exists.
- `RL018` Cargo feature exists.
- `RL019` Docker Compose profile exists.
- `RL020` documented localhost port matches Compose host ports.
- `RL021` Go version claim matches `go.mod`.
- `RL022` Rust version claim matches Cargo MSRV.

## Adoption workflow

New repository:

```bash
realitylint init
realitylint . --all-docs
```

Existing repository with historical findings:

```bash
realitylint . --all-docs --write-baseline
realitylint . --all-docs
```

## Safety remains unchanged

RealityLint still does **not** execute commands from documentation, use an LLM as the source of truth, upload source code, or require a network service for scanning.
