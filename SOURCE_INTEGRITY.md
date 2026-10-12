# Source integrity

`SHA256SUMS` is a deterministic checksum manifest for the current repository source tree. It helps reviewers detect accidental byte changes between two copies of the same revision; it is not a substitute for Git signatures, security review, or compatibility testing.

The published `1.0.0` release is immutable and unchanged. New versions are built by `python tools/build_release.py` and independently rebuilt with `--check`. The builder normalizes text to LF, sorts entries, fixes ZIP timestamps/permissions, excludes caches, and refuses to overwrite different existing release bytes. Each release publishes `skill-governor-vVERSION.zip` and its SHA-256 sidecar. Source checksums and package checksums cover different scopes.

Regenerate and verify the source manifest with:

```bash
python tools/build_source_manifest.py
python tools/build_source_manifest.py --check
```
