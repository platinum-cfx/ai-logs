# Latest status — 2026-10-15 (UTC)

## Server package
- Server CI run `38795556491` on commit `3562e833` succeeded.
- `NSM-server-v0.8.1-localtest.zip` was validated and uploaded to the NSM release: https://github.com/platinum-cfx/NSM-FIVEM/releases/download/nsm-v0.2-preview/NSM-server-v0.8.1-localtest.zip
- Static packaging checks passed; runtime boot/list verification remains pending.

## Client diagnostic package
- Client CI run `38801965172` on commit `904bb01b` ended `failure` in the upstream packaging step. MSBuild completed; the packer expected `FiveM_Diag.exe`, but this rebranded build output contains `NSM_Diag.exe`.
- The uploaded CI artifact still contained the compiled client files. Its `sticky.dll` matched the release cache copy and contained six `NSM launch diagnostic` markers.
- The client package builder replaced 406 files from the artifact and passed its checks. The local-test patcher also passed all checks (including no VPS URLs and Steam app ID 218); the final zip CRC passed.
- Uploaded diagnostic-only asset (233,521,719 bytes): https://github.com/platinum-cfx/NSM-FIVEM/releases/download/nsm-v0.2-preview/NSM-client-v0.7.4-diagnostic-localtest.zip
- This is not a final client fix. Runtime testing with Steam GTA is still required.

## Workspace archive
- Private repo: https://github.com/platinum-cfx/ai-logs (138 sanitized files at initial upload).
- GitHub access-token values and the masterlist signing key were excluded from the archive. The completed server zip is stored as a release asset, not duplicated in the repo.
- Removed the local server-zip duplicate and build caches; the remaining workspace is about 69 MB. User asked to wait for the client diagnostic upload before further cleanup.
