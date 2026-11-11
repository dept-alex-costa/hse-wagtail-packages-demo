# hse-demo-important-redirects

Demo module in the `legacy-main` release series `1.x.x`.

| Dependency | Supported versions |
| --- | --- |
| Python | `>=3.12,<3.14` |
| Wagtail | `>=6.4,<6.5` |
| Django | `>=4.2.26,<4.3` |

## Install this release

```bash
python -m pip install "hse-demo-important-redirects @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@important_redirects-v1.0.3#subdirectory=packages/important-redirects"
```

For a Poetry project, add this entry under `[tool.poetry.dependencies]`.

```toml
[tool.poetry.dependencies]
hse-demo-important-redirects = { git = "https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git", tag = "important_redirects-v1.0.3", subdirectory = "packages/important-redirects" }
```

Run `poetry lock` and `poetry install` in the consuming project.

## Release and test

Merge changes into `legacy-main` and select that branch with `package=important_redirects`
in the **Release package** Action. The Action assigns the module version and
creates a package tag such as `important_redirects-v1.0.3`.

Run the package checks from the repository root.

```bash
python scripts/check_package.py --line wagtail6 --package important_redirects
```

See the [repository README](../../README.md) for the two release series and the
release workflow.
