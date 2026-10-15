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

## Client crash log and source fix — 2026-10-15
- User's diagnostic log ended with `Could not load v2/CitizenFX.NSM.NativeImpl.dll.`
- Verified: the diagnostic package contained `CitizenFX.FiveM.NativeImpl.dll` but not the requested NSM-named DLL. The compiled Mono host requested the NSM name; the v0.7.4 baseline requested FiveM instead.
- Root cause: `MonoComponentHostShared.h` set the GTA V Mono `PRODUCT_NAME` to `NSM`, but Premake still builds `CitizenFX.FiveM.NativeImpl.dll`. This also broke the user's required `CitizenFX.*` compatibility.
- Fix pushed in commit `f52d3d5c99d21230de82e9cf19b0dbee6b43ab6c`: Mono assembly loading again uses the upstream `FiveM` namespace; visible launcher branding remains NSM.
- Fixed the client packer mismatch too: it now accepts the source-rebranded `NSM_Diag.exe` and stores it under the upstream cache filename expected by the packaging overlay.
- New Windows client build run `38819701247` is in progress. The next diagnostic package will be uploaded only after validation. Runtime confirmation is still required.
