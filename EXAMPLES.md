# Skill Governor examples

These copy-paste scenarios show when the Skill adds value and what a useful result should expose. They are illustrative, not claims about a particular user's environment.

## Read-only library audit

```text
Use $skill-governor to audit only the skill roots my host already exposes. Do not modify files. Identify duplicate names, overlapping triggers, required reading, missing tool prerequisites, and skills that are unnecessary for ordinary tasks.
```

A useful result names the inspected roots and limits, distinguishes discovery from source review, and returns scoped overlap findings without claiming to know which skills are useful from filenames alone.

## Select the smallest sufficient workflow

```text
Use $skill-governor for this task: compare the applicable skills, respect any explicit user or project requirement, and choose the smallest sufficient set. Include a no-extra-skill option when one obvious workflow is enough.
```

The result should state why each selected Skill is necessary now, which required documents must be read, which tools and permissions are actually available, and why excluded candidates add no current value.

## Review before installation

```text
Use $skill-governor to review this repository before installing its skill. Verify provenance, license, package boundaries, dependencies, overlap, host compatibility and rollback. Do not install until the review is complete and the requested write is authorized.
```

An illustrative evidence table may contain:

```text
installed: no
discovered: yes
source reviewed: yes, commit <sha>
tools ready: partial
executed: no
verified: no
selection rule: use only for cross-project release audits
rollback: remove the exact authorized copy after checking no policy depends on it
```

## Cross-device reconciliation

```text
Use $skill-governor to reconcile this device with my approved policy. Re-discover paths and tools locally, compare source fingerprints, keep personal evidence private, and do not copy absolute paths or trust decisions from another host.
```
