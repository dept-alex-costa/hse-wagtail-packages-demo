"""Plan independent package releases; never push or publish from this script."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCH_RELEASES = {"main": ("wagtail74", 2), "legacy/wagtail-6-django-4": ("wagtail6", 1)}
LINES = tuple(line for line, _ in BRANCH_RELEASES.values())
PACKAGES = {
    "component_lib": "component-lib",
    "important_redirects": "important-redirects",
}
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def version_tuple(value: str) -> tuple[int, int, int]:
    if not VERSION.fullmatch(value):
        raise ValueError("Use a final version such as 1.2.3 (no prefix or prerelease).")
    return tuple(int(part) for part in value.split("."))


def next_version(current: str, bump: str, custom: str = "") -> str:
    major, minor, patch = version_tuple(current)
    if custom and bump != "custom":
        raise ValueError("custom_version can only be used with the custom bump.")
    if bump == "current":
        result = current
    elif bump == "patch":
        result = f"{major}.{minor}.{patch + 1}"
    elif bump == "minor":
        result = f"{major}.{minor + 1}.0"
    elif bump == "major":
        result = f"{major + 1}.0.0"
    elif bump == "custom":
        result = custom
    else:
        raise ValueError(f"Unknown bump: {bump}")
    if version_tuple(result) < version_tuple(current):
        raise ValueError("A release cannot lower the package version.")
    if bump != "current" and result == current:
        raise ValueError("Choose current to release the existing version.")
    return result


def package_path(package: str) -> Path:
    if package not in PACKAGES:
        raise ValueError("Unknown package.")
    return Path("packages") / PACKAGES[package]


def read_metadata(path: Path) -> dict:
    return tomllib.loads(path.read_text())["tool"]["poetry"]


def release_settings(branch: str) -> tuple[str, int]:
    if branch not in BRANCH_RELEASES:
        raise ValueError("Choose main or legacy/wagtail-6-django-4 for a release or package check.")
    return BRANCH_RELEASES[branch]


def make_plan(branch: str, package: str, bump: str, custom: str = "") -> dict:
    line, major = release_settings(branch)
    relative = package_path(package)
    current = read_metadata(ROOT / relative / "pyproject.toml")["version"]
    release = next_version(current, bump, custom.strip())
    if version_tuple(release)[0] != major:
        raise ValueError(f"{branch} releases must use {major}.x.x. Requested {release}.")
    tag = f"{package}-v{release}"
    existing = git("tag", "--list", tag)
    if existing:
        raise ValueError(f"Tag {tag} already exists; choose a new version.")
    return {
        "branch": branch,
        "line": line,
        "package": package,
        "path": relative.as_posix(),
        "current": current,
        "version": release,
        "tag": tag,
        "changed": str(current != release).lower(),
    }


def set_package_version(path: Path, version: str) -> None:
    version_tuple(version)
    text = path.read_text()
    # Only touch version in [tool.poetry], never dependency version strings.
    sections = re.split(r"(?=^\[)", text, flags=re.MULTILINE)
    for index, section in enumerate(sections):
        if section.startswith("[tool.poetry]\n"):
            sections[index], count = re.subn(
                r'^version[ \t]*=[ \t]*"[^"\n]+"[ \t]*$',
                f'version = "{version}"',
                section,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ValueError(f"Expected exactly one package version in {path}.")
            break
    else:
        raise ValueError(f"Missing [tool.poetry] in {path}.")
    path.write_text("".join(sections))


def previous_tag(plan: dict) -> str | None:
    prefix = f"{plan['package']}-v"
    major = version_tuple(plan['version'])[0]
    candidates = []
    for tag in git("tag", "--list", f"{prefix}{major}.*", "--merged", "HEAD").splitlines():
        suffix = tag.removeprefix(prefix)
        if VERSION.fullmatch(suffix) and tag != plan["tag"]:
            candidates.append((version_tuple(suffix), tag))
    return max(candidates)[1] if candidates else None


def write_notes(plan: dict, output: Path) -> None:
    package_dir = ROOT / plan["path"]
    metadata = read_metadata(package_dir / "pyproject.toml")
    lock = tomllib.loads((package_dir / "poetry.lock").read_text())
    locked_versions = {package["name"].lower(): package["version"] for package in lock["package"]}
    previous = previous_tag(plan)
    revision_range = f"{previous}..HEAD" if previous else "HEAD"
    commits = git("log", "--format=- %h %s", revision_range, "--", plan["path"])
    files = (
        git("diff", "--name-only", f"{previous}..HEAD", "--", plan["path"])
        if previous
        else git("ls-files", "--", plan["path"])
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"# {plan['line']} / {plan['package']} {plan['version']}\n\n"
        f"- Tag: `{plan['tag']}`\n"
        f"- Package path: `{plan['path']}`\n"
        f"- Source branch: `{plan['branch']}`\n"
        f"- Source commit: `{git('rev-parse', 'HEAD')}`\n"
        f"- Previous release: `{previous or 'first release'}`\n\n"
        "## Versions\n\n"
        f"- Module: `{plan['version']}`\n"
        f"- Wagtail: `{locked_versions['wagtail']}`\n"
        f"- Django: `{locked_versions['django']}`\n"
        f"- Python requirement: `{metadata['dependencies']['python']}`\n\n"
        "## Package changes\n\n"
        f"{commits or '- No package-scoped commits.'}\n\n"
        "## Package files\n\n"
        + "\n".join(f"- `{item}`" for item in files.splitlines())
        + "\n\nThe wheel and source archive are attached to this release.\n"
    )


def check_pr_versions(base: str, branch: str) -> None:
    line, _ = release_settings(branch)
    git("rev-parse", "--verify", f"{base}^{{commit}}")
    failures = []
    for package in PACKAGES:
        path = (package_path(package) / "pyproject.toml").as_posix()
        result = subprocess.run(
            ["git", "show", f"{base}:{path}"],
            cwd=ROOT, text=True, capture_output=True,
        )
        if result.returncode:
            # Compare against the old path when a PR moves a package to the root.
            result = subprocess.run(
                ["git", "show", f"{base}:{line}/{path}"],
                cwd=ROOT, text=True, capture_output=True,
            )
            if result.returncode:
                # New packages can declare their initial version in the PR.
                continue
        old = tomllib.loads(result.stdout)["tool"]["poetry"]["version"]
        new = read_metadata(ROOT / path)["version"]
        if old != new:
            failures.append(f"{path}: {old} -> {new}")
    if failures:
        raise ValueError(
            "Versions are managed by Release package. Revert manual version changes:\n"
            + "\n".join(failures)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "prepare"):
        child = commands.add_parser(command)
        child.add_argument("--branch", choices=BRANCH_RELEASES, required=True)
        child.add_argument("--package", choices=PACKAGES, required=True)
        child.add_argument("--bump", choices=("current", "patch", "minor", "major", "custom"), required=True)
        child.add_argument("--custom-version", default="")
        child.add_argument("--github-output", type=Path)
        child.add_argument("--plan-file", type=Path)
    notes = commands.add_parser("notes")
    notes.add_argument("--plan-file", type=Path, required=True)
    notes.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("check-pr")
    check.add_argument("--base", required=True)
    check.add_argument("--branch", choices=BRANCH_RELEASES, required=True)
    line = commands.add_parser("line-for-branch")
    line.add_argument("--branch", choices=BRANCH_RELEASES, required=True)
    args = parser.parse_args()
    if args.command == "check-pr":
        check_pr_versions(args.base, args.branch)
        return
    if args.command == "line-for-branch":
        print(release_settings(args.branch)[0])
        return
    if args.command == "notes":
        write_notes(json.loads(args.plan_file.read_text()), args.output)
        return
    plan = make_plan(args.branch, args.package, args.bump, args.custom_version)
    if args.command == "prepare" and plan["changed"] == "true":
        set_package_version(ROOT / plan["path"] / "pyproject.toml", plan["version"])
    if args.github_output:
        with args.github_output.open("a") as handle:
            for key, value in plan.items():
                handle.write(f"{key}={value}\n")
    if args.plan_file:
        args.plan_file.parent.mkdir(parents=True, exist_ok=True)
        args.plan_file.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Release error: {error}", file=sys.stderr)
        sys.exit(1)
