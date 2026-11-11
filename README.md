# Wagtail package release strategy

One repository with a shared `packages/` layout and separate release series.
`legacy-main` carries Wagtail 6 and Django 4 releases in `1.x.x`. `main` carries
Wagtail 7 and Django 5 releases in `2.x.x`.

[Releases](https://github.com/dept-alex-costa/hse-wagtail-packages-demo/releases) · [GitHub Actions](https://github.com/dept-alex-costa/hse-wagtail-packages-demo/actions) · [Validation results](VALIDATION.md)

## 1. Choose your line

| Branch | Wagtail | Django | Release series | component_lib | important_redirects |
| --- | --- | --- | --- | --- | --- |
| `main` | 7.4.x | 5.2.x | `2.x.x` | 2.0.0 | 2.0.0 |
| `legacy-main` | 6.4.x | 4.2.x | `1.x.x` | 1.0.4 | 1.0.3 |

Use **Python 3.12** for the examples below. The packages accept Python
`>=3.12,<3.14`; CI uses Python 3.12.
Choose the line that matches your consuming project. Try the two lines in
separate environments: they declare different Django/Wagtail requirements.

These are small example modules, not the production HSE packages. The legacy
line demonstrates compatibility and releases; it is not a recommendation for
a new production site.

## 2. Install the packages

Choose **pip or Poetry** below. All examples install directly from GitHub using
an existing tag and the module's subdirectory. You need Git installed. The
repository is public, so these HTTPS URLs do not need a GitHub token or SSH key.
The packages have not been published to PyPI.

### With pip

Run inside your project's virtual environment. For a fresh test environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Wagtail 6 / Django 4.2:**

```bash
python -m pip install \
  "hse-demo-component-lib @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@component_lib-v1.0.4#subdirectory=packages/component-lib" \
  "hse-demo-important-redirects @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@important_redirects-v1.0.3#subdirectory=packages/important-redirects"
```

**Wagtail 7.4 / Django 5.2:**

```bash
python -m pip install \
  "hse-demo-component-lib @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@component_lib-v2.0.0#subdirectory=packages/component-lib" \
  "hse-demo-important-redirects @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@important_redirects-v2.0.0#subdirectory=packages/important-redirects"
```

Keep only the package you need if you do not want both. These commands also
install the compatible Django/Wagtail dependencies and may update existing
packages in that environment. The same requirement lines can go in a
`requirements.txt` file, without the command, quotes or continuation characters.

### With Poetry

Run inside your consuming project, where its `pyproject.toml` is located.
For a fresh test project, create an empty directory and initialise it first:

```bash
poetry init --name hse-demo-consumer --python ">=3.12,<3.14" --no-interaction
poetry env use python3.12
```

**Wagtail 6 / Django 4.2:**

```bash
poetry add \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@component_lib-v1.0.4#subdirectory=packages/component-lib" \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@important_redirects-v1.0.3#subdirectory=packages/important-redirects"
```

**Wagtail 7.4 / Django 5.2:**

```bash
poetry add \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@component_lib-v2.0.0#subdirectory=packages/component-lib" \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@important_redirects-v2.0.0#subdirectory=packages/important-redirects"
```

`poetry add` updates your project's `pyproject.toml` and `poetry.lock` and installs
the packages. Commit both files. Use Poetry 2.2.1 to match this demo's tooling.

The tag selects an exact release commit. `#subdirectory=packages/component-lib`
selects the module within that commit. Choose a tag in the major series for your
Wagtail line.

Use the following Poetry dependency for `important_redirects` on the legacy stack.

```toml
[tool.poetry.dependencies]
hse-demo-important-redirects = { git = "https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git", tag = "important_redirects-v1.0.3", subdirectory = "packages/important-redirects" }
```

Use this dependency for the same module on Wagtail 7 and Django 5.

```toml
[tool.poetry.dependencies]
hse-demo-important-redirects = { git = "https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git", tag = "important_redirects-v2.0.0", subdirectory = "packages/important-redirects" }
```

**About locks:** Poetry uses the consuming project's lockfile. pip does not read
`poetry.lock`. Neither installer adopts a dependency package's own lockfile;
those files make this repository's package checks reproducible.

## 3. Create a new release

1. Open and merge a PR into `main` for Wagtail 7.4 or `legacy-main` for Wagtail 6.4.
2. Open [Actions → Release package](https://github.com/dept-alex-costa/hse-wagtail-packages-demo/actions/workflows/release-package.yml).
3. Click **Run workflow** and select the same branch. The branch determines the compatibility line and release series.
4. Select the module and version increment.

| Input | What to choose |
| --- | --- |
| `package` | `component_lib` or `important_redirects` |
| `bump` | `patch`, `minor`, `current` or `custom` |
| `custom_version` | Only for `custom`, e.g. `2.3.1` |

The Action validates and builds the selected module, commits any version bump
to the selected branch and creates a **tag and GitHub Release** with a wheel
and source archive. Tags use the repository-wide format
`<package_name>-v<version>` and point to the exact release commit. The tag
annotation and release notes list the module version, the locked Wagtail and
Django versions, and the Python requirement.

| Increment | Example |
| --- | --- |
| `patch` | `2.0.0` → `2.0.1` |
| `minor` | `2.0.0` → `2.1.0` |
| `current` | Releases the existing version if its tag does not exist yet |
| `custom` | Uses a higher final version within the branch’s major series |

Keep version bumps in the release Action. It checks the branch's major series
and rejects a tag name that already exists.

For a fix to `important_redirects` on `legacy-main`, run the Action with
`package=important_redirects` and `bump=patch` after merging the fix. Starting
from `1.0.3`, this creates `important_redirects-v1.0.4`.

For a feature in `component_lib` on `main`, use `package=component_lib` and
`bump=minor` after merging the change. Starting from `2.0.0`, this creates
`component_lib-v2.1.0`.

## Repository layout

Both branches use `packages/` at the repository root.

```text
packages/
  component-lib/
  important-redirects/
```

Every module has its own `pyproject.toml`, `poetry.lock`, `README.md` and `src/`.
Both branches carry the CI and release workflows. CI checks the two modules
in the branch targeted by the PR or push.

For local checks and workflow configuration, see [Development](docs/DEVELOPMENT.md).
For the tested stacks and successful release runs, see [Validation](VALIDATION.md).
