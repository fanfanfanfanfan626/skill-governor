"""Exercise the portable-only verification path without installing a skill."""
from pathlib import Path
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ReleaseInstallDocs(unittest.TestCase):
    def test_extracted_release_has_a_self_contained_read_only_audit(self):
        version = (ROOT/'VERSION').read_text().strip()
        docs = (ROOT/'AI_INSTALL.md').read_text(encoding='utf-8')
        self.assertIn('python skill-governor/scripts/audit_bundle.py skill-governor', docs)
        self.assertIn(f'skill-governor-v{version}.zip.sha256', docs)
        self.assertIn('### Source checkout', docs)
        self.assertIn('### Portable release ZIP only', docs)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            # A clean checkout has no ignored dist/ assets. Build in memory only.
            spec = importlib.util.spec_from_file_location('governor_release_docs', ROOT/'tools/build_release.py')
            builder = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(builder)
            built_version, payload = builder.build()
            self.assertEqual(built_version, version)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                archive.extractall(destination)
            before = {p.relative_to(destination).as_posix():p.read_bytes() for p in destination.rglob('*') if p.is_file()}
            run = subprocess.run([sys.executable, '-S', '-B', 'skill-governor/scripts/audit_bundle.py', 'skill-governor'],
                                 cwd=destination, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)['conforms'])
            self.assertFalse((destination/'tests').exists())
            self.assertTrue((destination/'skill-governor/requirements.txt').is_file())
            self.assertEqual(before, {p.relative_to(destination).as_posix():p.read_bytes() for p in destination.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
