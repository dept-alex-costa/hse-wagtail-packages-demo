# Development and workflow details

[Back to the quick start](../README.md).

## Running locally

Use Python 3.12 and Poetry **2.2.1**, the same Poetry version pinned in CI.

```bash
python3.12 -m venv /tmp/hse-demo-tools
/tmp/hse-demo-tools/bin/python -m pip install poetry==2.2.1
export PATH="/tmp/hse-demo-tools/bin:$PATH"
export POETRY_VIRTUALENVS_IN_PROJECT=true

python -m unittest discover -s tests -v
```

On `main`, use `--line wagtail74`. On `legacy-main`, use `--line wagtail6`.
Run the command once for `component_lib` and once for `important_redirects`.

```bash
python scripts/check_package.py --line wagtail74 --package component_lib
```

Each package check validates its lock, synchronises its environment, runs
`pip check`, builds wheel/sdist, installs the wheel and checks its imports and
the actual Django/Wagtail versions. It restores the editable installation at
the end. Release-control tests only create tags/commits in disposable local
repositories; they never publish anything.

Inspect a proposed release locally without changing a version or creating a tag:

```bash
python scripts/release.py plan \
  --branch main --package component_lib --bump patch
```

When changing dependencies, run `poetry lock` inside the selected module and
commit both its `pyproject.toml` and `poetry.lock`. Do not manually bump an
existing module's version in a feature PR. A package's own lock makes its CI
reproducible; consumers still need their own lockfiles.

## GitHub setup

This directory is a standalone repository scaffold. To run its workflows, its
contents must be at the **root of its own GitHub repository**, with `main` as
the default branch. Workflows inside a subdirectory of another repository do
not activate.

The release job uses the repository's `GITHUB_TOKEN` with `contents: write`;
it does not need a PAT or publish to PyPI. Repository/organisation settings and
rulesets must permit that workflow to push its version-bump commit and tags.
If direct pushes to the release branch are prohibited, the release process needs to be
adapted to a version-bump PR; do not disable the ruleset to make the demo run.

To require CI before merging, configure `Release controls` and the two package
checks for the corresponding Wagtail line on each branch.

## Reference

- Original pattern: `HSEIreland/hse-wagtail-packages`, manual **Release package** workflow.
- [Poetry lockfile guidance](https://python-poetry.org/docs/basic-usage/#committing-your-poetrylock-file-to-version-control).
- [Wagtail compatibility matrix](https://docs.wagtail.org/en/stable/releases/upgrading.html#compatible-django-python-versions).

## Release recovery

If the tag was pushed but GitHub Release creation failed, inspect the run and
create the missing Release against the existing tag, attaching the matching
artifacts. Do not move the tag or increment the version just to recover it.

The workflow pushes the version commit to the selected branch and its tag in
one atomic operation. Git rejects a push when that branch has advanced beyond
the release commit. Release notes include changes for the selected module and line.

The release job builds and publishes in one workflow because tags pushed with
GITHUB_TOKEN normally do not trigger another workflow. See
[GitHub workflow triggering rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
