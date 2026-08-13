# Security policy

RealityLint by **[@voonterr](https://github.com/voonterr)** is designed to scan untrusted repositories without executing commands found in their documentation.

## Supported version

Security fixes are applied to the latest release line.

## Reporting a vulnerability

Please do not open a public issue containing exploit details. Prefer GitHub Private Vulnerability Reporting for `voonterr/realitylint` after it is enabled. If that is unavailable, contact **@voonterr** privately through the contact method listed on the GitHub profile.

Useful reports should include the affected version, a minimal reproduction, impact, and whether the issue requires a malicious README/repository.

## Security boundaries

RealityLint reads the selected README plus a small set of repository metadata files. Repository-relative paths are resolved and contained within the repository root before reading. It does not run README commands, invoke package managers, import code from the scanned repository, or make network requests during a scan.

## Русский

Не публикуйте детали потенциально опасной уязвимости в открытом issue. После включения GitHub Private Vulnerability Reporting используйте его; если функция недоступна, свяжитесь с **@voonterr** приватно через контакты в профиле GitHub.

Особенно важны отчёты о выходе за корень репозитория, чтении через symlink, command/workflow injection, неожиданном выполнении кода и отказе в обслуживании на специально подготовленных README/metadata.
