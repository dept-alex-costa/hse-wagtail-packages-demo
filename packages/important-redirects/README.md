# hse-demo-important-redirects — wagtail74

Small packaging example, not a copy of the HSE production module.

- Source: `src/hse_demo_redirects`.
- Supported Wagtail line: `>=7.4,<7.5`.
- Supported Django line: `>=5.2.19,<5.3`.
- Release identifier: `important_redirects`.
- Versions are managed by **Release package**, not by feature PRs.
- Commit `poetry.lock` whenever dependencies change.

Run checks from the repository root:

```bash
python scripts/check_package.py --line wagtail74 --package important_redirects
```
