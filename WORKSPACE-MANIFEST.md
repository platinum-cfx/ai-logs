# Workspace archive manifest

Snapshot date: 2026-10-15

Files copied: 139
Copied content size: 71837498 bytes (68.51 MiB)

## Security handling

- GitHub access-token values were redacted; helper scripts now require `GH_TOKEN` from the environment.
- The masterlist ticket-signing private key was excluded.
- Local configuration and Go module caches were excluded.
- Temporary preview files were excluded.
- `nsm/releases/NSM-server-v0.8.1-localtest.zip` was not duplicated; it is already hosted as a GitHub Release asset.

## Omitted paths

- `.config` — user/tool configuration may contain credentials.
- `go` — Go module cache.
- `nsm/masterlist/ticket-signing-key.pem` — private key or credential file.
- `nsm/releases/NSM-server-v0.8.1-localtest.zip` — already published as a GitHub release asset.
- `tmp-view` — temporary preview files.
