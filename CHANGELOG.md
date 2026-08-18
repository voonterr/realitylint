# Changelog

## 0.5.0

- Add project-wide multi-document scanning with `--all-docs` and custom documentation globs.
- Add Docker Compose drift checks (`RL011`-`RL013`, `RL019`-`RL020`) for files, services, env files, profiles and nearby documented host ports.
- Add documented environment-variable drift (`RL014`).
- Add Go `go run` local-target and Go-version claim checks (`RL015`, `RL021`).
- Add Rust/Cargo manifest, binary, feature, and MSRV claim checks (`RL016`-`RL018`, `RL022`).
- Add `.realitylint.toml` docs scope and severity overrides.
- Add inline ignore/disable/enable directives for intentional examples.
- Add baseline generation and automatic baseline filtering.
- Add `realitylint init`, `realitylint rules`, and `realitylint explain` commands.
- Add JUnit XML output and pre-commit hook metadata.
- Expand GitHub Action inputs for project-wide scans.
- Promote package metadata from alpha to beta.

## 0.1.3

- Fix Windows/GitHub Actions CLI crashes when the console uses a legacy code page such as cp1252.
- Force UTF-8 safely for stdout/stderr when the Python stream supports reconfiguration.
- Add a regression test for legacy Windows stdout encoding.
- Add an external `voonterr/realitylint@v1` smoke-test workflow.

## 0.1.2

- Branded package, CLI, GitHub Action, metadata, license, and repository links as **@voonterr**.
- Added CLI author banner while keeping JSON/SARIF machine-readable.
- Added author/repository metadata to JSON and SARIF output.
- Hardened Markdown job-summary rendering against raw HTML from untrusted findings.
- Added package-manager working-directory support for `npm --prefix`, `yarn --cwd`, `pnpm --dir` / `pnpm -C`, and `bun --cwd`.
- Added `make -C` / `make --directory` target verification.
- Improved common Windows CMD and POSIX shell-prompt parsing.
- Added metadata/branding regression tests and CODEOWNERS.

## 0.1.1

- Hardened README path containment and symlink handling.
- Prevented shell injection through composite Action inputs.
- Escaped GitHub workflow annotations safely.
- Added README/metadata size limits and fail-safe parsing.
- Fixed `yarn run <script>` parsing and missing-package-script edge cases.
- Added monorepo-aware `cd` command context.
- Fixed nested README relative links, URL-encoded paths, link titles, and parentheses.
- Added `bun.lock`, `GNUmakefile`, and lowercase `makefile` support.
- Replaced regex-based pyproject metadata extraction with TOML parsing.
- Added malformed metadata diagnostics (`RL010`).
- Expanded regression/security test suite and packaging verification.
