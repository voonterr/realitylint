<div align="center">

<img src="docs/assets/banner.svg" alt="RealityLint — проверка рассинхронизации документации" width="100%" />

# RealityLint

**Документация описывает проект. RealityLint проверяет те утверждения, которые репозиторий может доказать.**

Статическая и детерминированная проверка документации относительно репозитория — **без выполнения команд, без LLM, без API-ключа и без отправки кода наружу.**

**by [@voonterr](https://github.com/voonterr)**

[English](README.md) · [Русский](README.ru.md)

[![CI](https://github.com/voonterr/realitylint/actions/workflows/ci.yml/badge.svg)](https://github.com/voonterr/realitylint/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/realitylint.svg?logo=pypi&logoColor=white)](https://pypi.org/project/realitylint/)
[![License: MIT](https://img.shields.io/badge/license-MIT-7C3AED.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/voonterr/realitylint?style=flat)](https://github.com/voonterr/realitylint/stargazers)

`local-first` · `deterministic` · `multi-doc` · `Docker` · `Go` · `Rust` · `CI-ready`

</div>

---

## Зачем это нужно

Документация устаревает, потому что код меняется быстрее текста.

Команду переименовали, файл перенесли, `.env.example` перестал соответствовать конфигурации, Docker Compose-сервис удалили, Cargo feature переименовали — а инструкция запуска всё ещё выглядит корректно.

Markdown-линтер проверит разметку. RealityLint задаёт другой вопрос:

> **Совпадают ли конкретные проверяемые утверждения документации с фактами внутри репозитория?**

RealityLint намеренно консервативен: если утверждение нельзя детерминированно доказать локальными файлами, инструмент его пропускает, а не угадывает.

## Демо за 30 секунд

<p align="center">
  <img src="docs/assets/demo.gif" alt="Демонстрация RealityLint" width="900" />
</p>

```bash
python -m pip install realitylint
realitylint .
```

Проверить больше документации проекта:

```bash
realitylint . --all-docs
```

## v0.5: Project Truth

Версия v0.5 превращает RealityLint из README-чекера в движок поиска documentation drift по проекту.

Главные изменения:

- **multi-doc**: `README*.md`, `docs/**/*.md`, `CONTRIBUTING.md` и свои glob-паттерны;
- **Docker Compose**: наличие Compose-файла, сервисов, `env_file`, profiles и расхождений localhost-портов;
- **переменные окружения**: сравнение явных упоминаний в документации с `.env.example` / `.env.sample` и типичными обращениями из исходного кода;
- **Go**: проверка локальных целей `go run` и drift версии Go;
- **Rust/Cargo**: `Cargo.toml`, `--bin`, `--features` и drift MSRV;
- **ignore directives** для намеренно неправильных примеров;
- необязательный **`.realitylint.toml`** для scope и severity правил;
- **baseline mode** для постепенного внедрения в старые репозитории;
- команды `realitylint init`, `realitylint rules`, `realitylint explain RLxxx`;
- **JUnit XML** плюс прежние text/JSON/Markdown/SARIF;
- интеграция с **pre-commit**;
- расширенный GitHub Action.

Подробности: [RELEASE_NOTES_v0.5.0.md](RELEASE_NOTES_v0.5.0.md).

## Правила

| Rule | Что проверяется |
|---|---|
| `RL000` | Репозиторий и документ можно безопасно прочитать |
| `RL001` | npm/pnpm/yarn/bun scripts существуют |
| `RL002` | Локальные Markdown-ссылки ведут на существующие пути |
| `RL003` | Упомянутые `.env.example` / `.env.sample` существуют |
| `RL004` | Package manager совпадает с lock-файлом |
| `RL005` | Python entry-файлы существуют |
| `RL006` | Make targets существуют |
| `RL007` | Версия pinned self-install совпадает с `pyproject.toml` |
| `RL008` | Заявленная лицензия имеет LICENSE/COPYING-файл |
| `RL009` | Очевидные inline-пути существуют *(notice)* |
| `RL010` | Сломанные metadata обрабатываются без падения |
| `RL011` | Для docker compose-команды существует читаемый Compose-файл |
| `RL012` | Упомянутый Docker Compose service существует |
| `RL013` | Пути Compose `env_file` существуют |
| `RL014` | Явно упомянутые env-переменные присутствуют в env templates |
| `RL015` | Локальная цель `go run` существует и содержит Go-код |
| `RL016` | Для Cargo-команды существует читаемый `Cargo.toml` |
| `RL017` | `cargo run --bin NAME` ссылается на определённый binary |
| `RL018` | Cargo features из документации существуют в `[features]` |
| `RL019` | Docker Compose profiles из `--profile` объявлены в сервисах |
| `RL020` | Документированные рядом localhost-порты совпадают с published host ports Compose |
| `RL021` | Версия Go в документации согласована с `go.mod` |
| `RL022` | Версия Rust в документации согласована с Cargo `rust-version` |

Посмотреть правила:

```bash
realitylint rules
realitylint explain RL012
```

## Один README или вся документация

Совместимый со старыми версиями режим:

```bash
realitylint .
```

Типовая документация проекта:

```bash
realitylint . --all-docs
```

Свои glob-паттерны:

```bash
realitylint . --docs "README*.md,docs/**/*.md"
```

Относительные ссылки внутри вложенного Markdown-файла по-прежнему проверяются относительно директории этого файла.

## Конфигурация

По умолчанию ничего настраивать не нужно. Для крупных проектов можно создать `.realitylint.toml`:

```toml
[realitylint]
docs = ["README*.md", "docs/**/*.md"]
exclude = ["docs/vendor/**"]

[severity]
RL009 = "off"
RL014 = "warning"
```

Допустимые значения severity: `error`, `warning`, `notice`, `off`.

Создать конфиг и GitHub Actions workflow автоматически:

```bash
realitylint init
```

## Ignore directives

Для учебных и намеренно неправильных примеров можно отключать точечную проверку:

```text
<!-- realitylint-ignore-next-line RL012 -->
<намеренно неправильный Compose-пример>
```

Или блок:

```text
<!-- realitylint-disable RL014 -->
...
<!-- realitylint-enable RL014 -->
```

## Baseline mode

Для старого репозитория не обязательно исправлять десятки накопленных проблем перед включением CI.

Создать baseline:

```bash
realitylint . --all-docs --write-baseline
```

`.realitylint-baseline.json` затем применяется автоматически: старые находки подавляются, новые продолжают обнаруживаться.

Отключить baseline для конкретного запуска:

```bash
realitylint . --no-baseline
```

## GitHub Actions

```yaml
name: Documentation reality check
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
          all-docs: "true"
          fail-on: error
```

Action добавляет inline annotations и Markdown Job Summary.

## pre-commit

```yaml
repos:
  - repo: https://github.com/voonterr/realitylint
    rev: v0.5.0
    hooks:
      - id: realitylint
```

## Форматы вывода

```bash
realitylint . --format text
realitylint . --format json
realitylint . --format markdown
realitylint . --format sarif
realitylint . --format junit
```

Политика завершения CI:

```bash
realitylint . --fail-on error
realitylint . --fail-on warning
realitylint . --fail-on never
```

## Модель безопасности

RealityLint — **статический анализатор**, а не sandbox.

- Команды из документации **никогда не выполняются**.
- LLM не используется как источник истины.
- Для сканирования не нужен API-ключ или внешний сервис.
- Исходники и документация остаются локально.
- Неоднозначные случаи лучше пропустить, чем выдать выдуманную ошибку.
- Сохраняются проверки containment путей и ограничения размеров файлов.
- GitHub annotations экранируют управляющие символы workflow-команд.
- Сторонние GitHub Actions в самом репозитории закреплены immutable commit SHA.

О проблемах безопасности: [SECURITY.md](SECURITY.md).

## Философия проекта

1. **Факты вместо догадок.** Finding должен подтверждаться содержимым репозитория.
2. **Никакого произвольного выполнения.** Документация может содержать опасные команды — RealityLint их не запускает.
3. **Лучше промолчать, чем уверенно ошибиться.**
4. **Zero-config сначала, настройки при необходимости.**
5. **Небольшие изолированные правила.** Новые экосистемы должны добавляться без превращения RealityLint в shell-интерпретатор.

Дальнейшие планы: [ROADMAP.md](ROADMAP.md).

## Участие в разработке

Баг-репорты, идеи правил, сообщения о false positive и pull requests приветствуются.

```bash
python -m unittest discover -s tests -v
```

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## Статус

RealityLint v0.5 — **beta**. Проект намеренно проверяет ограниченный набор детерминированных утверждений и не пытается «понимать» произвольный естественный язык.

## Автор

Создан и поддерживается **[@voonterr](https://github.com/voonterr)**.

Если RealityLint поймал реальный documentation drift в вашем проекте, ⭐ репозитория поможет другим разработчикам его найти.

## Лицензия

MIT License. Copyright © 2026 voonterr. См. [LICENSE](LICENSE).
