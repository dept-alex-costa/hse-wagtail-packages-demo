"""Build a selected demo module and validate its installed wheel in isolation."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

from release import LINES, PACKAGES, ROOT, package_path

SMOKE = r'''
import django
import wagtail
from django.conf import settings
settings.configure(
    USE_I18N=False,
    SECRET_KEY="demo-checks-only",
    STATIC_URL="/static/",
    WAGTAILADMIN_STATIC_FILE_VERSION_STRINGS=False,
)
django.setup()
if "component" in PACKAGE:
    from hse_demo_components.blocks import DemoCardBlock
    block = DemoCardBlock()
    assert "title" in block.child_blocks
    assert "body" in block.child_blocks
else:
    from hse_demo_redirects import normalise_path
    assert normalise_path(" news ") == "/news"
    assert normalise_path("/") == "/"
    assert normalise_path("/about/") == "/about/"
    for invalid in ("//example.com", "https://example.com", "/a\nb"):
        try:
            normalise_path(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted an external or invalid path: {invalid!r}")
assert wagtail.VERSION[:2] == WAGTAIL
assert django.VERSION[:2] == DJANGO
print(f"Installed wheel OK: {PACKAGE}; Wagtail {wagtail.__version__}; Django {django.get_version()}")
'''


def run(*command: str, cwd: Path, env: dict | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def check(line: str, package: str) -> None:
    folder = ROOT / package_path(package)
    run("poetry", "check", "--lock", cwd=folder)
    run("poetry", "sync", "--no-interaction", cwd=folder)
    run("poetry", "run", "python", "-m", "pip", "check", cwd=folder)
    run("poetry", "build", "--clean", cwd=folder)
    wheels = list((folder / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"Expected exactly one wheel in {folder / 'dist'}")
    # Remove Poetry's editable install first. The smoke test must exercise the wheel.
    distribution = tomllib.loads((folder / "pyproject.toml").read_text())["tool"]["poetry"]["name"]
    run("poetry", "run", "python", "-m", "pip", "uninstall", "-y", distribution, cwd=folder)
    run("poetry", "run", "python", "-m", "pip", "install", "--no-deps", str(wheels[0]), cwd=folder)
    python = subprocess.check_output(
        ["poetry", "env", "info", "--executable"], cwd=folder, text=True,
    ).strip()
    wagtail, django = ((6, 4), (4, 2)) if line == "wagtail6" else ((7, 4), (5, 2))
    code = f"PACKAGE = {package!r}\nWAGTAIL = {wagtail!r}\nDJANGO = {django!r}\n" + SMOKE
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="hse-package-check-") as temporary:
        run(python, "-I", "-c", code, cwd=Path(temporary), env=clean_env)
    # Leave the workspace ready for local development after checking the wheel.
    run("poetry", "sync", "--no-interaction", cwd=folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line", choices=LINES, required=True)
    parser.add_argument("--package", choices=PACKAGES, required=True)
    args = parser.parse_args()
    check(args.line, args.package)

