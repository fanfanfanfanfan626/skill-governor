"""Portable integration tests using only isolated, explicitly supplied paths."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/skill-governor/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("govern_under_test", SCRIPTS / "govern.py")
govern = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(govern)
registry = govern.registry


class GovernTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-governor-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root / "input-skills"
        self.skill = self.make_skill(self.skills / "fixture")
        self.state = self.root / "private-state"
        self.host = self.root / "host" / "AGENTS.md"

    def make_skill(self, folder, name="fixture"):
        folder.mkdir(parents=True)
        path = folder / "SKILL.md"
        path.write_text("---\nname: " + name + "\ndescription: Test fixture only.\n---\nPreserve user scope.\n", encoding="utf-8")
        return path

    def initialize(self):
        return govern.initialize(self.state, ["local=" + str(self.skills)])

    def ready(self, raw=b"Existing host instructions.\n"):
        self.initialize()
        (self.state / "POLICY.md").write_text("# Reviewed fixture policy\nUse only relevant skills.\n", encoding="utf-8")
        if raw is not None:
            self.host.parent.mkdir(parents=True)
            self.host.write_bytes(raw)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest("Host does not allow fixture symlinks: " + str(error))

    def interrupt_final_record(self, operation):
        original = registry.write_json
        calls = 0

        def fail_second_write(path, value):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated final transaction record write failure")
            return original(path, value)

        with mock.patch.object(registry, "write_json", side_effect=fail_second_write):
            with self.assertRaises(OSError):
                operation()
        self.assertEqual(calls, 2)

    def fail_host_replace(self, operation):
        original = govern.os.replace

        def fail_selected_host(source, destination):
            if registry.path_key(destination) == registry.path_key(self.host):
                raise OSError("Simulated host atomic replacement failure")
            return original(source, destination)

        with mock.patch.object(govern.os, "replace", side_effect=fail_selected_host):
            with self.assertRaises(OSError):
                operation()

    def test_init_explicit_root_is_private_unreviewed_and_does_not_edit_skills(self):
        original = self.skill.read_bytes()
        result = self.initialize()
        self.assertEqual(result["status"], "draft_unreviewed")
        self.assertFalse(result["host_modified"])
        self.assertEqual(self.skill.read_bytes(), original)
        entry = registry.load_sources(self.state)["entries"][0]
        self.assertEqual(entry["id"], "local:fixture")
        self.assertIsNone(entry["review"])
        self.assertEqual(registry.inspect_entry(entry)["review_state"], "not_reviewed")
        self.assertEqual((self.state / ".gitignore").read_text(), "*\n!.gitignore\n")
        self.assertFalse(self.host.exists())

    def test_single_skill_directory_is_supported(self):
        result = govern.initialize(self.state, ["single=" + str(self.skill.parent)])
        self.assertEqual(result["entries"], 1)
        self.assertEqual(registry.load_sources(self.state)["local_roots"], [str(self.skill.parent.resolve())])

    def test_duplicate_roots_rejected_before_writes(self):
        with self.assertRaises(ValueError):
            govern.initialize(self.state, ["local=" + str(self.skills), "other=" + str(self.skills)])
        self.assertFalse(self.state.exists())

    def test_duplicate_names_in_one_namespace_rejected_before_writes(self):
        self.make_skill(self.skills / "second", name="fixture")
        with self.assertRaises(ValueError):
            self.initialize()
        self.assertFalse(self.state.exists())

    def test_identical_names_in_distinct_namespaces_are_distinct(self):
        other = self.root / "other-skills"
        self.make_skill(other / "fixture")
        result = govern.initialize(self.state, ["first=" + str(self.skills), "second=" + str(other)])
        self.assertEqual(result["entries"], 2)
        self.assertEqual({x["id"] for x in registry.load_sources(self.state)["entries"]}, {"first:fixture", "second:fixture"})

    def test_invalid_frontmatter_rejected_without_partial_state(self):
        self.skill.write_text("---\nname: fixture\n---\nMissing description.\n", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.initialize()
        self.assertEqual(self.snapshot(), before)

    def test_invalid_namespace_rejected_without_partial_state(self):
        with self.assertRaises(ValueError):
            govern.initialize(self.state, ["../../unsafe=" + str(self.skills)])
        self.assertFalse(self.state.exists())

    def test_state_inside_skill_rejected(self):
        nested = self.skill.parent / "private-state"
        with self.assertRaises(ValueError):
            govern.initialize(nested, ["local=" + str(self.skills)])
        self.assertFalse(nested.exists())

    def test_nonempty_state_is_not_overwritten(self):
        self.state.mkdir()
        (self.state / "important.txt").write_bytes(b"preserve")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.initialize()
        self.assertEqual(self.snapshot(), before)

    def test_classification_does_not_certify_source_review(self):
        self.initialize()
        govern.classify(self.state, "local:fixture", "coding", ["Fixture work"], ["Unrelated work"], "conditional", "Fixture evidence only")
        entry = registry.entry_for(self.state, "local:fixture")
        self.assertIsNone(entry["review"])
        self.assertEqual(registry.inspect_entry(entry)["review_state"], "not_reviewed")

    def test_integration_requires_policy_before_mutation(self):
        self.initialize()
        before = self.snapshot()
        with self.assertRaises(ValueError):
            govern.integrate(self.state, self.host)
        self.assertEqual(self.snapshot(), before)

    def test_integrate_dry_run_has_no_mutations(self):
        self.ready(raw=None)
        before = self.snapshot()
        result = govern.integrate(self.state, self.host, dry_run=True)
        self.assertTrue(result["changed"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.host.exists())
        self.assertFalse((self.state / "integrations").exists())

    def test_rollback_dry_run_has_no_mutations(self):
        self.ready()
        govern.integrate(self.state, self.host)
        before = self.snapshot()
        result = govern.rollback(self.state, self.host, dry_run=True)
        self.assertTrue(result["changed"])
        self.assertEqual(self.snapshot(), before)

    def test_integration_is_byte_idempotent(self):
        self.ready()
        govern.integrate(self.state, self.host)
        before = self.snapshot()
        self.assertFalse(govern.integrate(self.state, self.host)["changed"])
        self.assertEqual(self.snapshot(), before)

    def test_no_tail_newline_exact_rollback(self):
        original = b"Original without final newline"
        self.ready(original)
        govern.integrate(self.state, self.host)
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original)

    def test_crlf_exact_integration_and_rollback(self):
        original = b"Original\r\nSecond line\r\n"
        self.ready(original)
        govern.integrate(self.state, self.host)
        integrated = self.host.read_bytes()
        self.assertEqual(integrated.replace(b"\r\n", b""), integrated.replace(b"\r\n", b"").replace(b"\n", b""))
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original)

    def test_external_suffix_is_preserved(self):
        original = b"Original\n\n"
        suffix = b"Later unrelated instructions.\n"
        self.ready(original)
        govern.integrate(self.state, self.host)
        self.host.write_bytes(self.host.read_bytes() + suffix)
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original + suffix)

    def test_selective_rollback_removes_owned_separator_without_tail_newline(self):
        original = b"Original without final newline"
        prefix = b"Later unrelated heading\n"
        self.ready(original)
        govern.integrate(self.state, self.host)
        self.host.write_bytes(prefix + self.host.read_bytes())
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), prefix + original)

    def test_selective_rollback_removes_owned_crlf_separator(self):
        original = b"Original\r\n"
        prefix = b"Later unrelated heading\r\n"
        self.ready(original)
        govern.integrate(self.state, self.host)
        self.host.write_bytes(prefix + self.host.read_bytes())
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), prefix + original)

    def test_rollback_restores_original_file_absence(self):
        self.ready(raw=None)
        govern.integrate(self.state, self.host)
        govern.rollback(self.state, self.host)
        self.assertFalse(self.host.exists(), "Rollback should restore absence when integration created the unchanged host")

    def test_changed_block_refuses_rollback_and_reintegration(self):
        self.ready()
        govern.integrate(self.state, self.host)
        self.host.write_bytes(self.host.read_bytes().replace(b"## Skill governance", b"## User modified governance"))
        before = self.snapshot()
        with self.assertRaises(ValueError):
            govern.rollback(self.state, self.host)
        with self.assertRaises(ValueError):
            govern.integrate(self.state, self.host)
        self.assertEqual(self.snapshot(), before)

    def test_changed_backup_refuses_rollback(self):
        self.ready()
        govern.integrate(self.state, self.host)
        _, backup = govern.integration_paths(self.state, self.host)
        backup.write_bytes(b"Tampered backup")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            govern.rollback(self.state, self.host)
        self.assertEqual(self.snapshot(), before)

    def test_unowned_markers_are_not_adopted(self):
        self.ready((govern.START + "\nUser content\n" + govern.END + "\n").encode())
        before = self.snapshot()
        with self.assertRaises(ValueError):
            govern.integrate(self.state, self.host)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_sources_cli_fails_without_host_mutation(self):
        self.ready()
        (self.state / "sources.json").write_text("[]", encoding="utf-8")
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(SCRIPTS / "govern.py"), "--state", str(self.state), "integrate", "--host-file", str(self.host)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_failed_ownership_record_write_does_not_leave_host_modified(self):
        original = b"Original\n"
        self.ready(original)
        with mock.patch.object(registry, "write_json", side_effect=OSError("Simulated ownership record write failure")):
            with self.assertRaises(OSError):
                govern.integrate(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original)

    def test_final_integration_record_failure_recovers_after_state(self):
        original = b"Original\n"
        self.ready(original)
        self.interrupt_final_record(lambda: govern.integrate(self.state, self.host))
        record_path, _ = govern.integration_paths(self.state, self.host)
        self.assertIn("pending", registry.read_json(record_path))
        installed_bytes = self.host.read_bytes()
        self.assertIn(govern.START.encode(), installed_bytes)
        self.assertFalse(govern.integrate(self.state, self.host)["changed"])
        self.assertEqual(self.host.read_bytes(), installed_bytes)
        self.assertTrue(registry.read_json(record_path)["active"])
        self.assertNotIn("pending", registry.read_json(record_path))
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original)

    def test_failed_host_replace_recovers_before_state_and_retries(self):
        original = b"Original\n"
        self.ready(original)
        self.fail_host_replace(lambda: govern.integrate(self.state, self.host))
        record_path, _ = govern.integration_paths(self.state, self.host)
        self.assertIn("pending", registry.read_json(record_path))
        self.assertEqual(self.host.read_bytes(), original)
        self.assertEqual(list(self.host.parent.glob(".skill-governor-*")), [])
        self.assertTrue(govern.integrate(self.state, self.host)["changed"])
        self.assertTrue(registry.read_json(record_path)["active"])
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original)

    def test_pending_dry_run_refuses_without_writing(self):
        self.ready()
        self.interrupt_final_record(lambda: govern.integrate(self.state, self.host))
        before = self.snapshot()
        for operation in (govern.integrate, govern.rollback):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(ValueError, "Pending"):
                    operation(self.state, self.host, dry_run=True)
                self.assertEqual(self.snapshot(), before)

    def test_external_edit_during_pending_refuses_recovery_without_writing(self):
        self.ready()
        self.interrupt_final_record(lambda: govern.integrate(self.state, self.host))
        self.host.write_bytes(self.host.read_bytes() + b"Later external edit\n")
        before = self.snapshot()
        for operation in (govern.integrate, govern.rollback):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(ValueError, "Host changed"):
                    operation(self.state, self.host)
                self.assertEqual(self.snapshot(), before)

    def test_final_rollback_record_failure_recovers_completed_rollback(self):
        original = b"Original\n"
        self.ready(original)
        govern.integrate(self.state, self.host)
        self.interrupt_final_record(lambda: govern.rollback(self.state, self.host))
        self.assertEqual(self.host.read_bytes(), original)
        result = govern.rollback(self.state, self.host)
        self.assertEqual(result["status"], "already_rolled_back")
        record_path, _ = govern.integration_paths(self.state, self.host)
        self.assertFalse(registry.read_json(record_path)["active"])

    def test_failed_rollback_host_replace_recovers_and_retries(self):
        original = b"Original\n"
        self.ready(original)
        govern.integrate(self.state, self.host)
        installed = self.host.read_bytes()
        self.fail_host_replace(lambda: govern.rollback(self.state, self.host))
        self.assertEqual(self.host.read_bytes(), installed)
        govern.rollback(self.state, self.host)
        self.assertEqual(self.host.read_bytes(), original)

    def test_new_host_removal_recovers_after_final_record_failure(self):
        self.ready(raw=None)
        govern.integrate(self.state, self.host)
        self.interrupt_final_record(lambda: govern.rollback(self.state, self.host))
        self.assertFalse(self.host.exists())
        self.assertEqual(govern.rollback(self.state, self.host)["status"], "already_rolled_back")
        self.assertFalse(self.host.exists())

    def test_malformed_pending_is_rejected_without_destroying_journal(self):
        self.ready()
        govern.integrate(self.state, self.host)
        record_path, _ = govern.integration_paths(self.state, self.host)
        pending = {"pending": {"before_sha256": "not-current", "after_sha256": registry.sha(self.host),
                               "before_record": None, "after_record": []}}
        registry.write_json(record_path, pending)
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(SCRIPTS / "govern.py"), "--state", str(self.state), "rollback", "--host-file", str(self.host)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr + "\nJournal after attempted recovery: " + record_path.read_text())
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_resolved_child_escape_guard_without_symlink_privilege(self):
        outside = self.root / "outside" / "SKILL.md"
        original = Path.resolve

        def redirect_fixture(path, *args, **kwargs):
            if Path(path).name == self.skill.name and Path(path).parent.name == self.skill.parent.name:
                return outside
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", redirect_fixture):
            with self.assertRaisesRegex(ValueError, "leaves the explicit source root"):
                self.initialize()
        self.assertFalse(self.state.exists())

    def test_host_link_guard_without_symlink_privilege(self):
        self.ready()
        before = self.snapshot()
        original = Path.is_symlink

        def linked_host(path):
            return path == self.host or original(path)

        with mock.patch.object(Path, "is_symlink", linked_host):
            with self.assertRaisesRegex(ValueError, "symlink"):
                govern.integrate(self.state, self.host)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_host_is_rejected(self):
        self.ready()
        link = self.root / "linked-AGENTS.md"
        self.symlink(link, self.host)
        original = self.host.read_bytes()
        with self.assertRaises(ValueError):
            govern.integrate(self.state, link)
        self.assertEqual(self.host.read_bytes(), original)

    def test_child_symlink_outside_explicit_root_is_not_discovered(self):
        outside = self.make_skill(self.root / "not-authorized" / "external", "external")
        link = self.skills / "linked-external"
        self.symlink(link, outside.parent, directory=True)
        with self.assertRaises(ValueError):
            self.initialize()
        self.assertFalse(self.state.exists())

    def test_external_resource_symlink_is_not_fingerprinted(self):
        outside = self.root / "private.txt"
        outside.write_text("Private unrelated data", encoding="utf-8")
        link = self.skill.parent / "external.txt"
        self.symlink(link, outside)
        with self.assertRaises(ValueError):
            registry.fingerprint(self.skill.parent)


if __name__ == "__main__":
    unittest.main()
