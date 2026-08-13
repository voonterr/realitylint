# Publish RealityLint / Публикация RealityLint

Repository owner: **[@voonterr](https://github.com/voonterr)**  
Repository: `https://github.com/voonterr/realitylint`

The repository already exists, so this package is intended to become its first source commit.

## 1. Verify locally / Локальная проверка

```bash
python -m compileall -q realitylint scripts tests
python -m unittest discover -s tests -v
python -m realitylint . --fail-on error
python -m realitylint . --readme README.ru.md --fail-on error
python -m realitylint --version
```

Expected: both README scans are `100/100`, tests pass, and the CLI identifies `by @voonterr`.

## 2. Push to the empty GitHub repository / Загрузка в GitHub

Open a terminal in the extracted project folder:

```bash
git init
git add .
git commit -m "feat: initial RealityLint v0.1.2 release"
git branch -M main
git remote add origin https://github.com/voonterr/realitylint.git
git push -u origin main
```

If `origin` already exists, use:

```bash
git remote set-url origin https://github.com/voonterr/realitylint.git
git push -u origin main
```

## 3. Finish the GitHub page / Оформление страницы

Follow [GITHUB_SETUP.md](GITHUB_SETUP.md):

- set the repository description and topics;
- upload `docs/assets/social-preview.png` as Social Preview;
- enable Issues and Discussions;
- enable private vulnerability reporting and Dependabot security features where available.

## 4. First release / Первый релиз

```bash
git tag v0.1.2
git push origin v0.1.2
git tag -f v1 v0.1.2
git push -f origin v1
```

Create GitHub Release **`RealityLint v0.1.2 — README drift detection without an LLM`** and paste the contents of [RELEASE_NOTES_v0.1.2.md](RELEASE_NOTES_v0.1.2.md).

Use `v0.1.2` as the immutable release tag. The moving `v1` tag is the stable major tag consumed by GitHub Action users.

## 5. Security / Безопасность

- Keep workflow permissions read-only unless a workflow genuinely needs more.
- Third-party Actions in this repository are pinned to full commit SHAs.
- Enable **Private vulnerability reporting**.
- Protect `main` and require CI once external contributions start arriving.

## 6. PyPI later / PyPI позже

Do not add a PyPI badge until the package is actually published. When you decide to publish, build from a clean checkout and upload the signed/reviewed release artifacts using your normal trusted PyPI workflow.
