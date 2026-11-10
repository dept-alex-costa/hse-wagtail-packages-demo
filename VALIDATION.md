# Local validation

Validated on 10 November 2026 with Python 3.12.11 and Poetry 2.2.1.

## Resolved stacks

Both modules in each line have their own committed-ready `poetry.lock`.

| Line | Wagtail | Django | Module checks |
| --- | --- | --- | --- |
| `wagtail6` | 6.4.2 | 4.2.30 | Both passed |
| `wagtail74` | 7.4.4 | 5.2.19 | Both passed |

For all four modules, local checks passed for lock consistency, dependency
installation, `pip check`, wheel/sdist builds, and import/behaviour checks against
the installed wheel. The checks also verified the actual Django and Wagtail
versions in each environment.

Poetry reports deprecation warnings for the legacy `[tool.poetry]` metadata
layout retained from the reference project. These did not fail validation.

## Release controls

- All eight release-control tests passed using disposable Git repositories.
- `actionlint` 1.7.7 passed for both GitHub Actions workflows.
- A local flow using a temporary bare Git remote created and atomically pushed
  `wagtail6/component_lib-v1.0.1` and `wagtail74/component_lib-v1.1.0`.
- The line versions remained independent; both `important_redirects` module
  versions remained `1.0.0` during that simulation.
- The release notes identified the final source commit and scoped changes to
  the selected line/module.
- A temporary real module version bump to `1.0.1` still passed `poetry check
  --lock`, confirming a package-version-only bump does not invalidate its lock.

The simulation did not change the four scaffold versions, which remain `1.0.0`.
Tags/commits created by tests exist only in disposable repositories.

## Not executed

The project has not been pushed to GitHub. No real GitHub Actions run or GitHub
Release has been created. Running the remote release flow requires publishing
this directory as the root of its own repository and permitting the release job
to push its version commit and tag under that repository's rulesets.

