#!/usr/bin/env python3
"""Read-only Skill directory/ZIP preflight. Never extract, execute, install or upload."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
import zipfile
import zlib

from audit_skills import parse_frontmatter, NAME_RE

SOURCE = 'https://developers.openai.com/api/docs/guides/tools-skills'
MAX_ZIP = 50_000_000
MAX_FILE = 25_000_000
MAX_FILES = 500
MAX_MANIFEST = 1_000_000  # Local inspection guard, not an API limit.

def linked(path):
    info=path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info,'st_file_attributes',0) & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024))

def audit_bundle(target: Path, *, max_zip=MAX_ZIP, max_file=MAX_FILE, max_files=MAX_FILES):
    path = Path(target).absolute()
    issues, entries = [], []
    report = {'schema_version':1, 'target':str(path), 'conforms':False,
              'source':SOURCE, 'checked_on':'2026-10-12', 'file_count':0, 'issues':issues,
              'limits':{'zip_bytes':max_zip,'file_bytes':max_file,'files':max_files,'manifest_inspection_bytes':MAX_MANIFEST,'inspection_entries':max_files*4},
              'limitations':['Structural preflight only, not source trust, safety, behavior, host compatibility or API acceptance.',
                             'No extraction, execution, network, upload, installation or governance-state writes.',
                             'Documented MB thresholds are conservatively interpreted as decimal bytes. ZIP payloads other than the bounded manifest are not decompressed or CRC-tested.']}
    def issue(code, name=''):
        issues.append({'code':code,'path':name})
    inspected=0
    seen=set()
    def check_name(name,directory=False):
        canonical=name[:-1] if directory and name.endswith('/') else name
        parts=canonical.split('/')
        if chr(92) in canonical or chr(0) in canonical or re.match(r'^[A-Za-z]:',canonical) or any(p in ('','.','..') for p in parts): issue('unsafe-path',name)
        for part in parts:
            if part.endswith(('.', ' ')) or any(ord(c)<32 or c in '<>:"|?*' for c in part) or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part):
                issue('nonportable-windows-path',name);break
        folded=unicodedata.normalize('NFC',canonical).casefold()
        if folded in seen: issue('duplicate-or-case-colliding-path',name)
        seen.add(folded)
    def scan(folder):
        nonlocal inspected
        pending=[folder]
        while pending:
            with os.scandir(pending.pop()) as children:
                for item in children:
                    inspected+=1
                    if inspected>max_files*4: issue('entry-count-inspection-limit');return
                    child=Path(item.path);name=child.relative_to(path).as_posix()
                    check_name(name)
                    if linked(child): issue('symlink-or-junction',name)
                    elif child.is_dir(): pending.append(child)
                    elif child.is_file(): entries.append((name,child.stat().st_size,child,False))
                    else: issue('non-regular-file',name)
                    if len(entries)>max_files:return
    archive = None
    try:
        if linked(path): issue('symlink-or-junction',str(path)); return report
        if path.is_dir():
            kind='directory';folder_name=path.name
            check_name(folder_name);seen.clear();scan(path)
        elif path.is_file():
            kind='zip'
            if path.stat().st_size>max_zip: issue('zip-size-limit'); return report
            archive=zipfile.ZipFile(path)
            infos=archive.infolist()
            # Bound pathological directory-heavy ZIP metadata too.
            if len(infos)>max_files*4: issue('entry-count-inspection-limit'); return report
            roots=set()
            for info in infos:
                linked_entry=stat.S_ISLNK(info.external_attr>>16)
                # orig_filename preserves unsafe separators that ZipInfo normalizes on Windows.
                raw_name=info.orig_filename
                check_name(raw_name,info.is_dir())
                roots.add(raw_name.split('/')[0])
                if linked_entry: issue('symlink-entry',raw_name)
                if info.flag_bits&1: issue('encrypted-entry',raw_name)
                mode=stat.S_IFMT(info.external_attr>>16)
                if mode not in (0,stat.S_IFREG,stat.S_IFDIR,stat.S_IFLNK): issue('non-regular-entry',raw_name)
                if info.is_dir():continue
                entries.append((raw_name,info.file_size,info,linked_entry or bool(info.flag_bits&1)))
            folder_name=next(iter(roots)) if len(roots)==1 else ''
            if len(roots)!=1: issue('single-top-level-folder-required')
        else: issue('target-missing'); return report
        report['kind']=kind; report['file_count']=len(entries)
        if len(entries)>max_files: issue('file-count-limit')
        manifests=[]
        for name,size,entry,blocked in entries:
            parts=name.split('/')
            if size>max_file: issue('file-size-limit',name)
            if parts[-1].casefold()=='skill.md': manifests.append((name,size,entry,blocked))
        if len(manifests)!=1: issue('exactly-one-manifest-required')
        else:
            name,size,entry,blocked=manifests[0]
            expected=f'{folder_name}/skill.md' if kind=='zip' else 'skill.md'
            if name.casefold()!=expected.casefold(): issue('manifest-not-at-root',name)
            if size>MAX_MANIFEST: issue('manifest-inspection-limit',name)
            elif not blocked and not issues:
                stream=archive.open(entry) if archive else entry.open('rb')
                with stream: raw=stream.read(min(MAX_MANIFEST,max_file)+1)
                if len(raw)>min(MAX_MANIFEST,max_file): issue('manifest-read-limit',name)
                else:
                    metadata,errors=parse_frontmatter(raw.decode('utf-8-sig'))
                    for error in errors: issue(error,name)
                    skill_name=metadata.get('name','')
                    description=metadata.get('description','')
                    if not skill_name or len(skill_name)>64 or not NAME_RE.fullmatch(skill_name): issue('invalid-name',name)
                    elif skill_name!=folder_name: issue('folder-name-mismatch',name)
                    if not description or len(description)>1024: issue('invalid-description',name)
                    report['name']=skill_name
    except FileNotFoundError:
        issue('target-missing')
    except (OSError,ValueError,RuntimeError,UnicodeError,zipfile.BadZipFile,zipfile.LargeZipFile,NotImplementedError,EOFError,zlib.error) as exc:
        issue('inspection-incomplete',type(exc).__name__)
    finally:
        if archive: archive.close()
    issues.sort(key=lambda item:(item['code'],item['path']))
    report['conforms']=not issues
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',type=Path)
    parser.add_argument('--compact',action='store_true')
    args=parser.parse_args(); result=audit_bundle(args.target)
    print(json.dumps(result,ensure_ascii=False,indent=None if args.compact else 2))
    return 0 if result['conforms'] else 2 if any(x['code'] in ('inspection-incomplete','target-missing') for x in result['issues']) else 1

if __name__=='__main__': raise SystemExit(main())
