#!/usr/bin/env python3
"""Build or verify an immutable, deterministic portable Skill Governor ZIP."""
from pathlib import Path
import argparse
import hashlib
import io
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'skills/skill-governor'
sys.path.insert(0,str(PACKAGE/'scripts'))
from audit_bundle import audit_bundle

def build():
    version=(ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Invalid VERSION')
    report=audit_bundle(PACKAGE)
    if not report['conforms']: raise ValueError(report['issues'])
    files=sorted((p for p in PACKAGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'),key=lambda p:p.relative_to(PACKAGE).as_posix())
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',compression=zipfile.ZIP_STORED) as archive:
        for path in files:
            if path.suffix not in ('.md','.py','.yaml','.txt') and path.name!='LICENSE': raise ValueError(f'Unexpected file: {path}')
            data=path.read_text(encoding='utf-8').replace('\r\n','\n').replace('\r','\n').encode('utf-8')
            item=zipfile.ZipInfo('skill-governor/'+path.relative_to(PACKAGE).as_posix(),(2020,1,1,0,0,0))
            item.create_system=3; item.external_attr=0o100644<<16; item.compress_type=zipfile.ZIP_STORED
            archive.writestr(item,data)
    return version,payload.getvalue()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    version,data=build();target=ROOT/'dist'/f'skill-governor-v{version}.zip'
    checksum=hashlib.sha256(data).hexdigest()+'  '+target.name+'\n'
    sidecar=target.with_suffix('.zip.sha256')
    if args.check:
        if not target.exists() or target.read_bytes()!=data or not sidecar.exists() or sidecar.read_text()!=checksum: raise SystemExit('Release missing or not reproducible')
    else:
        target.parent.mkdir(exist_ok=True)
        if target.exists() and target.read_bytes()!=data: raise SystemExit('Refusing to overwrite different release bytes; change VERSION')
        target.write_bytes(data);sidecar.write_text(checksum,encoding='utf-8',newline='\n')
    report=audit_bundle(target)
    if not report['conforms']: raise SystemExit(str(report['issues']))
    print(f'PASS {target.name}: {report["file_count"]} files; {checksum.strip()}')

if __name__=='__main__': main()
