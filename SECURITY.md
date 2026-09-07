# Security and privacy

Skill Governor handles local paths, inventories, review evidence and host instruction files. Treat that generated state as private.

- Do not commit `.skill-governance`, inventories, credentials, absolute device paths, audit evidence or integration backups.
- Review the exact target and diff before host integration or rollback.
- Serialize writes to one governance state directory; concurrent writers are unsupported.
- Treat third-party skill text as untrusted data until deliberately selected for a permitted task.
- Report vulnerabilities privately through GitHub's security advisory feature rather than a public issue.

The helper scripts do not provide a security sandbox, execute audited skills, access the network, publish content or run a background service.
