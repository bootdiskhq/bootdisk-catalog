# ADR-006: gate hosted curation on approved-user access

Status: accepted requirement; hosted implementation pending.

Stian approved the local curation flow, but requires that nobody can curate online
without his approval. The current service stays loopback-only and curator files
remain outside the public release allowlist. Release 1.2 does not authorize opening
this service to the internet.

Before any hosted curator deployment:

- Require authentication and an explicit approved-user allowlist; initially Stian
  only. Registration must not grant access automatically.
- Enforce authorization in the service for every curator read and write endpoint,
  not merely in frontend navigation. Deny by default; support access revocation.
- Attribute decisions to the authenticated user, keep audit history and backups,
  and verify recovery. Never trust a client-supplied actor identity.
- Keep publication a separate authorized action from curation approval.
- Choose and review hosted authentication/session architecture before deployment;
  the local token is not an internet authentication system.
- Test anonymous, unapproved and revoked users, expired sessions, unauthorized
  direct API calls and cross-site requests. None may read private curator state
  or modify it. Verify an approved user can complete the intended flow.

Until this gate passes, public bootdisk.no continues to serve the static archive.
