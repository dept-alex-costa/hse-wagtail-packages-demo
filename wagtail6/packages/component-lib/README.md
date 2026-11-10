# hse-demo-component-lib — wagtail6

Small packaging example, not a copy of the HSE production module.

- Source: `src/hse_demo_components`.
- Supported Wagtail line: `>=6.4,<6.5`.
- Supported Django line: `>=4.2.26,<4.3`.
- Release identifier: `component_lib`.
- Versions are managed by **Release package**, not by feature PRs.
- Commit `poetry.lock` whenever dependencies change.

Run checks from the repository root:

```bash
python scripts/check_package.py --line wagtail6 --package component_lib
```
