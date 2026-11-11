"""Exercise release isolation and failure cases using disposable Git repositories."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import release

LEGACY = "legacy/wagtail-6-django-4"


class VersionTests(unittest.TestCase):
    def test_supported_increments(self):
        for bump, expected in (("current", "2.3.4"), ("patch", "2.3.5"), ("minor", "2.4.0"), ("major", "3.0.0")):
            with self.subTest(bump=bump):
                self.assertEqual(release.next_version("2.3.4", bump), expected)
        self.assertEqual(release.next_version("2.3.4", "custom", "2.5.1"), "2.5.1")

    def test_invalid_or_lower_versions_are_rejected(self):
        for value in ("2.3.3", "2.3.4", "02.4.0", "v3.0.0", "3.0.0rc1", "3.0.0\nother=bad", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.next_version("2.3.4", "custom", value)
        with self.assertRaises(ValueError):
            release.next_version("2.3.4", "patch", "3.0.0")


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hse-release-tests-")
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(release, "ROOT", self.root)
        self.root_patch.start()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Demo test")
        self.git("config", "user.email", "demo@example.com")
        for package in release.PACKAGES:
            folder = self.root / release.package_path(package)
            folder.mkdir(parents=True)
            (folder / "pyproject.toml").write_text(
                f'[tool.poetry]\nname = "{package}"\nversion = "1.0.0"\n\n'
                '[tool.poetry.dependencies]\npython = ">=3.12,<3.14"\n'
            )
            (folder / "poetry.lock").write_text(
                '[[package]]\nname = "wagtail"\nversion = "6.4.2"\n\n'
                '[[package]]\nname = "django"\nversion = "4.2.30"\n'
            )
        self.commit("Initial demo")
        self.git("branch", LEGACY)
        for package in release.PACKAGES:
            manifest = self.root / release.package_path(package) / "pyproject.toml"
            release.set_package_version(manifest, "2.0.0")
        self.commit("Wagtail 7 version baseline")

    def tearDown(self):
        self.root_patch.stop()
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-c", "commit.gpgsign=false", "-c", "init.templateDir=", *args],
            cwd=self.root, text=True, stderr=subprocess.STDOUT,
        ).strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-m", message)

    def test_releasing_one_module_leaves_other_line_and_module_unchanged(self):
        self.git("switch", LEGACY)
        snapshots = {p: p.read_bytes() for p in self.root.rglob("pyproject.toml")}
        plan = release.make_plan(LEGACY, "component_lib", "minor")
        selected = self.root / plan["path"] / "pyproject.toml"
        release.set_package_version(selected, plan["version"])
        self.assertEqual(release.read_metadata(selected)["version"], "1.1.0")
        self.commit("Release first line component")
        self.git("tag", plan["tag"])
        self.assertEqual(plan["tag"], "component_lib-v1.1.0")
        for path, content in snapshots.items():
            if path != selected:
                self.assertEqual(path.read_bytes(), content)
        self.git("switch", "main")
        other = release.make_plan("main", "component_lib", "patch")
        self.assertEqual(other["current"], "2.0.0")
        self.assertEqual(other["tag"], "component_lib-v2.0.1")

    def test_duplicate_tag_is_rejected_and_other_series_can_release(self):
        self.git("switch", LEGACY)
        self.git("tag", "component_lib-v1.0.0")
        with self.assertRaisesRegex(ValueError, "already exists"):
            release.make_plan(LEGACY, "component_lib", "current")
        self.git("switch", "main")
        self.assertEqual(
            release.make_plan("main", "component_lib", "current")["tag"],
            "component_lib-v2.0.0",
        )

    def test_release_version_must_match_branch_series(self):
        self.git("switch", LEGACY)
        with self.assertRaisesRegex(ValueError, r"must use 1\.x\.x"):
            release.make_plan(LEGACY, "component_lib", "custom", "2.0.0")
        self.git("switch", "main")
        with self.assertRaisesRegex(ValueError, r"must use 2\.x\.x"):
            release.make_plan("main", "component_lib", "custom", "3.0.0")

    def test_changelog_only_uses_selected_line_and_module(self):
        self.git("switch", LEGACY)
        self.git("tag", "component_lib-v1.0.0")
        self.git("tag", "component_lib-v2.99.0")
        self.git("tag", "important_redirects-v1.99.0")
        selected = self.root / release.package_path("component_lib")
        (selected / "README.md").write_text("Selected module change")
        self.commit("Selected module change")
        other = self.root / release.package_path("important_redirects")
        (other / "README.md").write_text("Other module change")
        self.commit("Other module change")
        plan = release.make_plan(LEGACY, "component_lib", "patch")
        notes = self.root / ".release" / "notes.md"
        release.write_notes(plan, notes)
        text = notes.read_text()
        self.assertIn("Selected module change", text)
        self.assertNotIn("Other module change", text)
        self.assertIn("Previous release: `component_lib-v1.0.0`", text)
        self.assertIn(f"Source branch: `{LEGACY}`", text)
        self.assertIn("Module: `1.0.1`", text)
        self.assertIn("Wagtail: `6.4.2`", text)
        self.assertIn("Django: `4.2.30`", text)
        self.assertIn("Python requirement: `>=3.12,<3.14`", text)
        self.assertNotIn("99.0.0", text)
        self.assertIn(self.git("rev-parse", "HEAD"), text)

    def test_manual_pr_version_changes_are_rejected(self):
        base = self.git("rev-parse", "HEAD")
        release.check_pr_versions(base, "main")
        selected = self.root / release.package_path("important_redirects") / "pyproject.toml"
        release.set_package_version(selected, "2.0.1")
        with self.assertRaisesRegex(ValueError, "packages/important-redirects"):
            release.check_pr_versions(base, "main")

    def test_version_check_follows_package_moved_to_root(self):
        (self.root / "wagtail74").mkdir()
        self.git("mv", "packages", "wagtail74/packages")
        self.commit("Old package layout")
        base = self.git("rev-parse", "HEAD")
        self.git("mv", "wagtail74/packages", "packages")
        release.check_pr_versions(base, "main")
        manifest = self.root / release.package_path("component_lib") / "pyproject.toml"
        release.set_package_version(manifest, "2.0.1")
        with self.assertRaisesRegex(ValueError, "packages/component-lib"):
            release.check_pr_versions(base, "main")

    def test_invalid_branch_or_module_is_rejected(self):
        for branch, package in (("feature", "component_lib"), (LEGACY, "../../other")):
            with self.subTest(branch=branch, package=package), self.assertRaises(ValueError):
                release.make_plan(branch, package, "patch")

    def test_cli_plan_is_read_only_and_prepare_only_updates_selected_module(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "release.py").write_bytes((SCRIPTS / "release.py").read_bytes())
        args = [sys.executable, str(scripts / "release.py"), "plan", "--branch", "main",
                "--package", "important_redirects", "--bump", "patch"]
        before = self.git("diff", "--", "packages")
        plan = json.loads(subprocess.check_output(args, cwd=self.root, text=True))
        self.assertEqual(plan["path"], "packages/important-redirects")
        self.assertEqual(self.git("diff", "--", "packages"), before)
        output = self.root / ".release-output"
        args[2] = "prepare"
        subprocess.check_output(args + ["--github-output", str(output)], cwd=self.root, text=True)
        changed = self.git("diff", "--name-only").splitlines()
        self.assertEqual(changed, [plan["path"] + "/pyproject.toml"])
        self.assertEqual(release.read_metadata(self.root / plan["path"] / "pyproject.toml")["version"], "2.0.1")
        self.assertIn("tag=important_redirects-v2.0.1", output.read_text())
        self.assertIn("branch=main", output.read_text())


if __name__ == "__main__":
    unittest.main()
