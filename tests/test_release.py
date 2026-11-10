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
        for line in release.LINES:
            for package in release.PACKAGES:
                folder = self.root / release.package_path(line, package)
                folder.mkdir(parents=True)
                (folder / "pyproject.toml").write_text(
                    f'[tool.poetry]\nname = "{package}"\nversion = "1.0.0"\n\n'
                    '[tool.poetry.dependencies]\npython = ">=3.12,<3.14"\n'
                )
                (folder / "poetry.lock").write_text("# unchanged test fixture\n")
        self.commit("Initial demo")

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
        snapshots = {p: p.read_bytes() for p in self.root.rglob("pyproject.toml")}
        plan = release.make_plan("wagtail6", "component_lib", "minor")
        selected = self.root / plan["path"] / "pyproject.toml"
        release.set_package_version(selected, plan["version"])
        self.assertEqual(release.read_metadata(selected)["version"], "1.1.0")
        self.commit("Release first line component")
        self.git("tag", plan["tag"])
        self.assertEqual(plan["tag"], "wagtail6/component_lib-v1.1.0")
        for path, content in snapshots.items():
            if path != selected:
                self.assertEqual(path.read_bytes(), content)
        other = release.make_plan("wagtail74", "component_lib", "patch")
        self.assertEqual(other["current"], "1.0.0")
        self.assertEqual(other["tag"], "wagtail74/component_lib-v1.0.1")

    def test_duplicate_tag_is_rejected_but_same_version_in_other_line_is_allowed(self):
        self.git("tag", "wagtail6/component_lib-v1.0.0")
        with self.assertRaisesRegex(ValueError, "already exists"):
            release.make_plan("wagtail6", "component_lib", "current")
        self.assertEqual(
            release.make_plan("wagtail74", "component_lib", "current")["tag"],
            "wagtail74/component_lib-v1.0.0",
        )

    def test_changelog_only_uses_selected_line_and_module(self):
        self.git("tag", "wagtail6/component_lib-v1.0.0")
        self.git("tag", "wagtail74/component_lib-v99.0.0")
        self.git("tag", "wagtail6/important_redirects-v99.0.0")
        selected = self.root / release.package_path("wagtail6", "component_lib")
        (selected / "README.md").write_text("Selected module change")
        self.commit("Selected module change")
        other = self.root / release.package_path("wagtail74", "component_lib")
        (other / "README.md").write_text("Other line change")
        self.commit("Other line change")
        plan = release.make_plan("wagtail6", "component_lib", "patch")
        notes = self.root / ".release" / "notes.md"
        release.write_notes(plan, notes)
        text = notes.read_text()
        self.assertIn("Selected module change", text)
        self.assertNotIn("Other line change", text)
        self.assertIn("wagtail6/component_lib-v1.0.0", text)
        self.assertNotIn("99.0.0", text)
        self.assertIn(self.git("rev-parse", "HEAD"), text)

    def test_manual_pr_version_changes_are_rejected(self):
        base = self.git("rev-parse", "HEAD")
        release.check_pr_versions(base)
        selected = self.root / release.package_path("wagtail74", "important_redirects") / "pyproject.toml"
        release.set_package_version(selected, "2.0.0")
        with self.assertRaisesRegex(ValueError, "wagtail74/packages/important-redirects"):
            release.check_pr_versions(base)

    def test_invalid_line_or_module_cannot_escape_package_roots(self):
        for line, package in (("../wagtail6", "component_lib"), ("wagtail6", "../../other")):
            with self.subTest(line=line, package=package), self.assertRaises(ValueError):
                release.make_plan(line, package, "patch")

    def test_cli_plan_is_read_only_and_prepare_only_updates_selected_module(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "release.py").write_bytes((SCRIPTS / "release.py").read_bytes())
        args = [sys.executable, str(scripts / "release.py"), "plan", "--line", "wagtail74",
                "--package", "important_redirects", "--bump", "patch"]
        before = self.git("diff", "--", "wagtail74")
        plan = json.loads(subprocess.check_output(args, cwd=self.root, text=True))
        self.assertEqual(self.git("diff", "--", "wagtail74"), before)
        output = self.root / ".release-output"
        args[2] = "prepare"
        subprocess.check_output(args + ["--github-output", str(output)], cwd=self.root, text=True)
        changed = self.git("diff", "--name-only").splitlines()
        self.assertEqual(changed, [plan["path"] + "/pyproject.toml"])
        self.assertEqual(release.read_metadata(self.root / plan["path"] / "pyproject.toml")["version"], "1.0.1")
        self.assertIn("tag=wagtail74/important_redirects-v1.0.1", output.read_text())


if __name__ == "__main__":
    unittest.main()

