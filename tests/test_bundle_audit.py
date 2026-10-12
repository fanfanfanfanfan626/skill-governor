import sys
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile
import os
import io
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/skill-governor/scripts'))
from audit_bundle import audit_bundle, linked

SKILL='---\nname: fixture\ndescription: Inspect a test fixture.\n---\nDo the requested test.\n'
class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
    def zip(self,entries):
        target=self.root/'test.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                for name,value in entries:
                    # ZipInfo normally replaces Windows backslashes; preserve adversarial names.
                    info = name if isinstance(name,zipfile.ZipInfo) else zipfile.ZipInfo('placeholder')
                    if isinstance(name,str): info.filename=name; info.orig_filename=name
                    archive.writestr(info,value)
        return target
    def test_directory_is_read_only(self):
        target=self.root/'fixture'; target.mkdir(); manifest=target/'SKILL.md';manifest.write_text(SKILL)
        before=manifest.read_bytes();self.assertTrue(audit_bundle(target)['conforms']);self.assertEqual(before,manifest.read_bytes())
    def test_zip_and_lowercase_manifest(self):
        target=self.zip([('fixture/skill.md',SKILL)])
        self.assertTrue(audit_bundle(target)['conforms']);self.assertFalse((self.root/'fixture').exists())
    def test_rejects_case_ambiguity_and_duplicates(self):
        for name in ['fixture/SKILL.md','fixture/skill.md']:
            report=audit_bundle(self.zip([('fixture/SKILL.md',SKILL),(name,SKILL)]))
            self.assertFalse(report['conforms'])
    def test_rejects_traversal_absolute_backslash_and_multiple_roots(self):
        for name in ['../escape','/outside','C:/outside','fixture\\x','other/x']:
            self.assertFalse(audit_bundle(self.zip([('fixture/SKILL.md',SKILL),(name,'x')]))['conforms'],name)
    def test_symlink(self):
        info=zipfile.ZipInfo('fixture/link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
        report=audit_bundle(self.zip([('fixture/SKILL.md',SKILL),(info,'outside')]))
        self.assertIn('symlink-entry',[x['code'] for x in report['issues']])
    def test_size_and_count_limits_with_small_fixtures(self):
        target=self.zip([('fixture/SKILL.md',SKILL),('fixture/payload','x'*200)])
        for kw in [dict(max_zip=1),dict(max_file=100),dict(max_files=1)]:self.assertFalse(audit_bundle(target,**kw)['conforms'])
    def test_501_files_rejected(self):
        target=self.zip([('fixture/SKILL.md',SKILL)]+[(f'fixture/{i}.txt','x') for i in range(500)])
        self.assertIn('file-count-limit',[x['code'] for x in audit_bundle(target)['issues']])
    def test_manifest_at_root_and_correct_identity(self):
        for name,value in [('fixture/nested/SKILL.md',SKILL),('wrong/SKILL.md',SKILL),('fixture/SKILL.md','no frontmatter')]:self.assertFalse(audit_bundle(self.zip([(name,value)]))['conforms'])
    def test_missing_and_corrupt_target(self):
        self.assertFalse(audit_bundle(self.root/'missing')['conforms']); target=self.root/'bad.zip';target.write_bytes(b'bad');self.assertFalse(audit_bundle(target)['conforms'])
    def test_directory_entries_cannot_bypass_path_checks(self):
        for extra in [[('../escape/','')],[('fixture/x/',''),('fixture/x/','')],[('fixture/x/',''),('fixture/x','x')],[('fixture/CON','x')],[('fixture/x.','x')],[('fixture/é','x'),('fixture/e\u0301','x')]]:
            self.assertFalse(audit_bundle(self.zip([('fixture/SKILL.md',SKILL)]+extra))['conforms'])
        link=zipfile.ZipInfo('fixture/link/');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        self.assertIn('symlink-entry',[x['code'] for x in audit_bundle(self.zip([('fixture/SKILL.md',SKILL),(link,'')]))['issues']])
    def test_windows_reparse_points_are_detected_without_new_python_api(self):
        with patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=1024)):
            self.assertTrue(linked(self.root/'junction'))
    def test_directory_metadata_count_is_bounded(self):
        target=self.root/'fixture';target.mkdir();(target/'SKILL.md').write_text(SKILL)
        for i in range(20):(target/str(i)).mkdir()
        report=audit_bundle(target,max_files=2)
        self.assertIn('entry-count-inspection-limit',[x['code'] for x in report['issues']])
    def test_broken_manifest_stream_returns_a_report(self):
        target=self.zip([('fixture/SKILL.md',SKILL)])
        with patch.object(zipfile.ZipExtFile,'read',side_effect=EOFError):
            self.assertIn('inspection-incomplete',[x['code'] for x in audit_bundle(target)['issues']])
    @unittest.skipIf(os.name=='nt','Windows itself rejects reserved directory names')
    def test_reserved_root_names(self):
        for name in ('con','com1'):
            target=self.root/name;target.mkdir();(target/'SKILL.md').write_text(SKILL.replace('fixture',name))
            self.assertIn('nonportable-windows-path',[x['code'] for x in audit_bundle(target)['issues']])
    def test_missing_target_has_specific_code(self):
        self.assertIn('target-missing',[x['code'] for x in audit_bundle(self.root/'missing')['issues']])
    def test_release_uses_posix_lexical_order(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
        from build_release import build
        _,data=build()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names=archive.namelist();self.assertEqual(names,sorted(names))
            self.assertFalse(any('__pycache__' in name for name in names))
