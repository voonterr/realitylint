# GitHub setup / Настройка GitHub

This repository is already prepared for `https://github.com/voonterr/realitylint`.

## 1. Repository About

**Description**

> 🔍 Detect when your README drifts away from your real project. Static, deterministic documentation consistency checker.

**Topics**

`python` `cli` `developer-tools` `documentation` `readme` `lint` `static-analysis` `github-actions` `opensource` `ci` `automation`

Website can stay empty until a dedicated project page exists.

### Русский

В блоке **About** справа на странице репозитория укажите описание выше и добавьте topics. Английское описание лучше оставить основным — так проект легче находят международные пользователи.

## 2. Social preview

Upload this prepared image as the repository social preview:

`docs/assets/social-preview.png`

Source SVG is also included:

`docs/assets/social-preview.svg`

### Русский

В настройках репозитория найдите **Social preview** и загрузите `docs/assets/social-preview.png`. Эта карточка будет использоваться при публикации ссылки на RealityLint в соцсетях и мессенджерах.

## 3. Recommended repository features

Enable:

- Issues;
- Discussions;
- Private vulnerability reporting;
- Dependabot alerts/security updates where available.

Keep GitHub Actions workflow permissions read-only unless a future workflow genuinely needs write access.

After the repository starts receiving outside contributions, protect `main` and require CI before merge.

### Русский

Рекомендуется включить **Issues**, **Discussions**, **Private vulnerability reporting** и Dependabot. Защиту `main` имеет смысл включить после появления первых внешних pull request, чтобы обязательный CI не мешал первоначальной настройке проекта.

## 4. First release

Create tag/release `v0.1.2` and use:

`RELEASE_NOTES_v0.1.2.md`

as the release description.

Then create/move the major Action tag:

```bash
git tag v0.1.2
git push origin v0.1.2
git tag -f v1 v0.1.2
git push -f origin v1
```

`voonterr/realitylint@v1` becomes usable by other repositories after the `v1` tag exists.

## 5. Suggested first issues

Good public roadmap issues:

1. `rule: verify Go go run/module claims`
2. `rule: verify Rust cargo run --bin claims`
3. `rule: verify Docker Compose services and ports`
4. `feature: add ignore directives for intentional examples`
5. `feature: add pre-commit integration`

Mark a genuinely beginner-friendly scoped item as `good first issue`; do not manufacture meaningless issues only to make the repository look active.

## 6. Launch text

### English

> I built RealityLint because README examples often survive longer than the code they describe. It checks locally provable README claims against the repository itself: package scripts, links, `.env` templates, lockfiles, Python entrypoints, Make targets, pinned versions, licenses, and paths. It is deterministic, local-first, needs no API key, and never executes README commands. Built by @voonterr.

### Русский

> Сделал RealityLint — локальный инструмент, который проверяет, не разошёлся ли README с реальным проектом. Он сверяет scripts, ссылки, `.env`-шаблоны, lock-файлы, Python entrypoint'ы, Make targets, версии, лицензии и пути. Без API-ключей, без LLM и без выполнения команд из README. Проект: @voonterr.
