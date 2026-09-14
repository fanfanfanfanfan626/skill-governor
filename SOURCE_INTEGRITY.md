# Source integrity

`SHA256SUMS` is a deterministic checksum manifest for the current repository source tree. It helps reviewers detect accidental byte changes between two copies of the same revision; it is not a substitute for Git signatures, security review, or compatibility testing.

The published `1.0.0` release package is intentionally unchanged. Its immutable archive checksum remains in `dist/skill-governor-1.0.0.zip.sha256`.

Regenerate and verify the source manifest with:

```bash
python tools/build_source_manifest.py
python tools/build_source_manifest.py --check
```
