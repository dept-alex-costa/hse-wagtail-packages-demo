# Wagtail packages: two lines, independent releases

A small demo showing how to keep **Wagtail 6** and **Wagtail 7.4** packages in
one repository, with a separate version and release for every module.

[Releases](https://github.com/dept-alex-costa/hse-wagtail-packages-demo/releases) · [GitHub Actions](https://github.com/dept-alex-costa/hse-wagtail-packages-demo/actions) · [Validation results](VALIDATION.md)

## 1. Choose your line

| Folder | Wagtail | Django | component_lib | important_redirects |
| --- | --- | --- | --- | --- |
| `wagtail6` | 6.4.x | 4.2.x | 1.0.1 | 1.0.0 |
| `wagtail74` | 7.4.x | 5.2.x | 1.1.0 | 1.0.0 |

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
  "hse-demo-component-lib @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail6/component_lib-v1.0.1#subdirectory=wagtail6/packages/component-lib" \
  "hse-demo-important-redirects @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail6/important_redirects-v1.0.0#subdirectory=wagtail6/packages/important-redirects"
```

**Wagtail 7.4 / Django 5.2:**

```bash
python -m pip install \
  "hse-demo-component-lib @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail74/component_lib-v1.1.0#subdirectory=wagtail74/packages/component-lib" \
  "hse-demo-important-redirects @ git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail74/important_redirects-v1.0.0#subdirectory=wagtail74/packages/important-redirects"
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
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail6/component_lib-v1.0.1#subdirectory=wagtail6/packages/component-lib" \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail6/important_redirects-v1.0.0#subdirectory=wagtail6/packages/important-redirects"
```

**Wagtail 7.4 / Django 5.2:**

```bash
poetry add \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail74/component_lib-v1.1.0#subdirectory=wagtail74/packages/component-lib" \
  "git+https://github.com/dept-alex-costa/hse-wagtail-packages-demo.git@wagtail74/important_redirects-v1.0.0#subdirectory=wagtail74/packages/important-redirects"
```

`poetry add` updates your project's `pyproject.toml` and `poetry.lock` and installs
the packages. Commit both files. Use Poetry 2.2.1 to match this demo's tooling.

**How the version is selected:** `@wagtail6/component_lib-v1.0.1` selects the
release; `#subdirectory=wagtail6/packages/component-lib` selects the module.
The tag and folder must belong to the same line. Use tags instead of `main`.

**About locks:** Poetry uses the consuming project's lockfile. pip does not read
`poetry.lock`. Neither installer adopts a dependency package's own lockfile;
those files make this repository's package checks reproducible.

## 3. Create a new release

1. Change the desired module and merge the PR into `main`.
2. Open [Actions → Release package](https://github.com/dept-alex-costa/hse-wagtail-packages-demo/actions/workflows/release-package.yml).
3. Click **Run workflow**, keep branch **main**, and choose:

| Input | What to choose |
| --- | --- |
| `line` | `wagtail6` or `wagtail74` |
| `package` | `component_lib` or `important_redirects` |
| `bump` | `patch`, `minor`, `major`, `current` or `custom` |
| `custom_version` | Only for `custom`, e.g. `2.3.1` |

The Action validates and builds the selected module, updates its version when
needed, commits the change and creates a **tag + GitHub Release**, with a wheel
and source archive attached. Merging a PR alone does not publish a release.

| Increment | Example |
| --- | --- |
| `patch` | `1.0.1` → `1.0.2` |
| `minor` | `1.0.1` → `1.1.0` |
| `major` | `1.0.1` → `2.0.0` |
| `current` | Releases the existing version if its tag does not exist yet |
| `custom` | Uses a final `X.Y.Z` version greater than the current version |

Do not manually change an existing module's version in a feature PR: the
release Action manages it. Existing tags are never overwritten.

The increment applies to the **selected module's version**, not to Wagtail or
Django. For example, releasing `wagtail6/component_lib-v1.0.2` does not change
`wagtail74/component_lib-v1.1.0` or either `important_redirects` module.

## Repository layout

```text
wagtail6/packages/
  component-lib/
  important-redirects/
wagtail74/packages/
  component-lib/
  important-redirects/
.github/workflows/
  ci.yml
  release-package.yml
```

Every module has its own `pyproject.toml`, `poetry.lock`, `README.md` and `src/`.
The `main` branch contains both lines. These folders are ordinary Python packages,
not Git submodules. Only modules receive release versions; the whole repository
has no shared version.

For local checks and workflow configuration, see [Development](docs/DEVELOPMENT.md).
For the tested stacks and successful release runs, see [Validation](VALIDATION.md).
