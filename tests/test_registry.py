import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("registry", Path(__file__).resolve().parents[1] / "skills/skill-governor/scripts/registry.py")
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root / "skills"
        self.path = self.skills / "fixture" / "SKILL.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text("---\nname: fixture\ndescription: Fixture skill for behavior checks.\n---\nRead references/contract.md before edits.\n", encoding="utf-8")
        self.contract = self.path.parent / "references/contract.md"
        self.contract.parent.mkdir()
        self.contract.write_text("Preserve the saved identifier.\n", encoding="utf-8")
        self.evidence = self.root / "review.md"
        self.evidence.write_text("Fixture review evidence\n", encoding="utf-8")
        self.entry = {"id": "fixture", "path": str(self.path), "domain": "coding", "role": "specialist",
                      "review": {"fingerprint": registry.fingerprint(self.path.parent)[0], "reviewer": "fixture",
                                 "timestamp": registry.now(), "scope": "fixture source review",
                                 "evidence_path": str(self.evidence), "evidence_sha256": registry.sha(self.evidence),
                                 "entrypoint_sha256": registry.sha(self.path)}}
        self.sources = {"schema_version": 1, "entries": [self.entry], "local_roots": [str(self.skills)], "plugin_bundles": []}
        self.save()

    def save(self):
        registry.write_json(self.root / "sources.json", self.sources)

    def issues(self):
        return {x["kind"] for x in registry.scan(self.root)["issues"]}

    def record(self):
        return {"schema_version": 1, "selections": [{"id": "fixture", "stage": "plan", "reason": "Inspect contract",
                    "required_paths": [str(self.contract)], "requires_execution": False}],
                "reads": [{"id": "fixture", "path": str(path), "sha256": registry.sha(path), "event": "content_emitted", "timestamp": registry.now()}
                          for path in (self.path, self.contract)], "executions": [], "verifications": [], "limitations": []}

    def test_modified_review_evidence_invalidates_review(self):
        self.evidence.write_text("Contradictory review\n")
        self.assertIn("review_evidence_changed", self.issues())

    def test_deleted_review_evidence_invalidates_review(self):
        self.evidence.unlink()
        self.assertIn("review_evidence_invalid", self.issues())

    def test_null_prereads_returns_validation_error(self):
        record = self.record()
        record["selections"][0]["required_paths"] = None
        self.assertTrue(registry.verify_record(self.root, record))

    def test_missing_arrays_rejected(self):
        record = self.record()
        del record["executions"]
        self.assertTrue(registry.verify_record(self.root, record))

    def test_blank_stage_rejected(self):
        record = self.record()
        record["selections"][0]["stage"] = "  "
        self.assertTrue(registry.verify_record(self.root, record))

    def test_missing_timestamp_rejected(self):
        record = self.record()
        del record["reads"][0]["timestamp"]
        self.assertTrue(registry.verify_record(self.root, record))

    def test_missing_observed_bundle_reported(self):
        self.sources["plugin_bundles"] = [{"id": "lost", "container": str(self.root / "absent"), "observed_version": "1.0"}]
        self.save()
        self.assertIn("observed_plugin_version_missing", self.issues())

    def test_unchanged_reviewed_source(self):
        self.assertEqual(self.issues(), set())

    def test_reference_change_invalidates_review(self):
        self.contract.write_text("Contract changed\n", encoding="utf-8")
        self.assertIn("changed_requires_review", self.issues())

    def test_entrypoint_change_invalidates_review(self):
        self.path.write_text(self.path.read_text() + "New prerequisite.\n")
        self.assertIn("changed_requires_review", self.issues())

    def test_refresh_does_not_approve_change(self):
        self.contract.write_text("New rule\n")
        registry.refresh(self.root)
        registry.refresh(self.root)
        self.assertIn("changed_requires_review", self.issues())

    def test_missing_skill_reported(self):
        self.path.unlink()
        self.assertIn("missing_or_invalid", self.issues())

    def test_new_skill_requires_registration(self):
        other = self.skills / "new" / "SKILL.md"
        other.parent.mkdir()
        other.write_text("---\nname: new\ndescription: New skill\n---\n")
        self.assertIn("unregistered_local", self.issues())

    def test_duplicate_identity_detected(self):
        self.sources["entries"].append(dict(self.entry))
        self.save()
        self.assertIn("duplicate_id", self.issues())

    def test_unknown_companion_detected(self):
        self.entry["companions"] = ["absent"]
        self.save()
        self.assertIn("unknown_companion", self.issues())

    def test_plugin_cache_version_not_silently_selected(self):
        container = self.root / "cache/plugin"
        skill = container / "2.0/skills/sample/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: sample\ndescription: A skill\n---\n")
        self.sources["plugin_bundles"] = [{"id": "plugin", "container": str(container), "observed_version": "1.0"}]
        self.save()
        self.assertIn("plugin_version_candidate", self.issues())
        self.assertEqual(len(registry.scan(self.root)["entries"]), 1)

    def test_bad_metadata_not_assumed_valid(self):
        self.path.write_text("No frontmatter\n")
        self.assertIn("missing_or_invalid", self.issues())

    def test_read_emits_full_content_and_records_hash(self):
        record_path = self.root / "run.json"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            registry.emit_read(self.root, "fixture", self.path, record_path)
        self.assertIn(self.path.read_text(), output.getvalue())
        record = registry.read_json(record_path)
        self.assertEqual(record["reads"][0]["sha256"], registry.sha(self.path))
        self.assertNotIn("comprehended", record["reads"][0])

    def test_planning_record_needs_no_fake_execution(self):
        self.assertEqual(registry.verify_record(self.root, self.record()), [])

    def test_missing_preread_rejected(self):
        record = self.record()
        record["reads"] = record["reads"][:1]
        self.assertTrue(registry.verify_record(self.root, record))

    def test_stale_read_rejected(self):
        record = self.record()
        self.contract.write_text("Changed while task ran\n")
        self.assertTrue(registry.verify_record(self.root, record))

    def test_other_skill_read_cannot_satisfy_contract(self):
        record = self.record()
        record["reads"][1]["id"] = "another-skill"
        self.assertTrue(registry.verify_record(self.root, record))

    def test_execution_claim_needs_evidence_file(self):
        record = self.record()
        record["selections"][0]["requires_execution"] = True
        self.assertTrue(registry.verify_record(self.root, record))
        for key in ("executions", "verifications"):
            record[key] = [{"id": "fixture", "stage": "plan", "status": "passed", "summary": "Fixture check",
                            "evidence_path": str(self.root / "does-not-exist.log")}]
        self.assertTrue(registry.verify_record(self.root, record))

    def test_failed_check_not_erased_by_earlier_pass(self):
        record = self.record()
        record["selections"][0]["requires_execution"] = True
        event = {"id": "fixture", "stage": "plan", "status": "passed", "summary": "Ran fixture", "evidence_path": str(self.evidence)}
        record["executions"] = [event]
        record["verifications"] = [event, dict(event, status="failed")]
        self.assertTrue(registry.verify_record(self.root, record))

    def test_consistent_record_is_not_behavior_certification(self):
        record = self.record()
        record["selections"][0]["requires_execution"] = True
        event = {"id": "fixture", "stage": "plan", "status": "passed", "summary": "Fixture evidence", "evidence_path": str(self.evidence)}
        record["executions"] = [event]
        record["verifications"] = [event]
        self.assertEqual(registry.verify_record(self.root, record), [])
        self.assertEqual(registry.inspect_entry(self.entry)["behavior_validation"], "not_inferred")


if __name__ == "__main__":
    unittest.main()
