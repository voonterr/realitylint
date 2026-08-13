# Contributing to RealityLint

RealityLint is created and maintained by **[@voonterr](https://github.com/voonterr)**.

RealityLint is deliberately conservative: a false positive is usually worse than skipping an ambiguous claim.

## Good first contributions

- Add a new deterministic rule with fixtures and tests.
- Improve Windows/path edge cases.
- Add support for another manifest or toolchain.
- Improve SARIF or GitHub annotation output.

## Development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
python -m compileall -q realitylint scripts tests
python -m unittest discover -s tests -v
python -m realitylint . --fail-on error
```

Every new rule should include passing, failing, malformed-input, and false-positive regression tests when applicable.

## Rule requirements

A rule should be deterministic, avoid executing repository code, keep all file reads inside the repository root, and fail safely on malformed input. If syntax is ambiguous, prefer skipping it over guessing.

## Русский

Можно открывать issue и pull request на русском или английском. Для нового правила желательно приложить:

- реальный пример строки из README;
- локальный файл/metadata, по которому утверждение можно проверить;
- положительный и отрицательный тест;
- пример неоднозначного случая, который лучше пропустить, чем считать ошибкой.

Главное требование остаётся тем же: RealityLint не должен выполнять код проверяемого репозитория и не должен выходить за его корневую директорию при чтении файлов.
