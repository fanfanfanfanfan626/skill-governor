# Changelog

All notable changes to Skill Governor are documented here.

## 1.1.0 - 2026-10-12

- Add a read-only directory/ZIP preflight for portable skill bundles, with bounded manifest inspection, path and duplicate checks, and machine-readable findings.
- Document current OpenAI Skills API package constraints separately from local inspection guards. Passing is not a security or compatibility certification.
- Add adversarial ZIP fixtures and reproducible release packaging; preserve existing private-state formats and routing behavior.

- Add examples, compatibility guidance, contribution and support paths, and community health templates.
- Improve GitHub Pages metadata, machine-readable discovery links, social preview support, and crawlability.
- Refresh GitHub Actions dependencies and add monthly Dependabot checks.
- Document and automate the repository-source checksum manifest without changing the stable `1.0.0` package.

## 1.0.0 - 2026-09-07

- Publish the first stable, portable `skill-governor` package.
- Separate installed, discovered, reviewed, tool-ready, executed and verified states.
- Add private governance state, source fingerprints, evidence records and reversible host integration.
- Add minimum-sufficient skill selection, including an explicit no-extra-skill route.
- Add normalization, acquisition, lifecycle, cross-device and host compatibility guidance.
- Add a read-only structural and routing audit CLI.
- Validate governance and rollback behavior with 63 unit tests.
