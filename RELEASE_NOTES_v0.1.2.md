# RealityLint v0.1.2 — README drift detection without an LLM

RealityLint by [@voonterr](https://github.com/voonterr) checks locally verifiable README claims against repository facts without executing documentation commands or sending source code to an AI service.

## Highlights

- deterministic checks for package scripts, local links/images, environment templates and package-manager lockfiles;
- Python entrypoint, Make target, pinned-version, license and repository-path checks;
- malformed metadata is reported instead of crashing the scanner;
- monorepo-aware working-directory handling (`cd`, `npm --prefix`, `yarn --cwd`, `pnpm -C/--dir`, `bun --cwd`, `make -C`);
- text, JSON, Markdown and SARIF output;
- hardened GitHub annotations and a composite GitHub Action;
- no API key, no LLM, no network access required by the scanner itself.

## Try it

```bash
git clone https://github.com/voonterr/realitylint.git
cd realitylint
python -m pip install -e .
realitylint examples/broken-project --fail-on never
```

## Русский

RealityLint проверяет, не устарели ли проверяемые инструкции из README относительно реального содержимого репозитория. Команды из документации **не выполняются**, исходный код никуда не отправляется, API-ключи и LLM не нужны.

В `v0.1.2` доступны проверки package scripts, локальных ссылок, `.env`-шаблонов, lock-файлов, Python entrypoint'ов, Make targets, версий, лицензии и путей к файлам, а также JSON/Markdown/SARIF и GitHub Action.

Created by **[@voonterr](https://github.com/voonterr)**.
