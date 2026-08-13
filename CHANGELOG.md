# Changelog

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
