# RealityLint v0.1.3

Windows compatibility hotfix for RealityLint.

## Fixed

- Fixed `UnicodeEncodeError` on Windows runners/terminals using legacy encodings such as `cp1252`.
- Human-readable output now safely prefers UTF-8, including `✓` / `✗` status symbols.
- Added a regression test reproducing the Windows encoding failure.
- Added a smoke workflow for the public `voonterr/realitylint@v1` GitHub Action.

## Compatibility

No rule or CLI-argument behavior changed. JSON/SARIF output remains machine-readable.

Created by **[@voonterr](https://github.com/voonterr)**.
