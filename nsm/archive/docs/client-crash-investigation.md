# Client crash 0xC0000005 — full mechanism (Wine-validated, 2026-10-13)

## Proven launch-time flow (real client 16.3.7, real packs, exact production cmdline)

NSM writes `altv.toml` into targetDir (connect.cpp:1524 `Load config.dll and generate altv.toml`)
— includes `gtapath` from NSM `.config` `gta_path`, `gtaPlatform = 'steam'`, `cachePath = <baseDir>\cache`.

altv.exe then:
1. Boots RML UI (fonts ~1 s), fetches skin index from global CDN (3 retries ≈ 6 s, 404 today),
   checks its own update via local proxy (`proxy\update_release_modified.json`, works offline).
2. Runs its own local HTTP proxy on 127.0.0.1:9988 (NSM binds the external adapter → no conflict).
   The `-customui http://127.0.0.1:9988/ui/index.html` target is served by the client's own proxy
   from `targetDir\ui\index.html` (shipped in packs).
3. **Platform validation of `gtapath`** (file-based, NO registry):
   - forbidden-file checklist in GTA dir: `7launcher\`, `7lcfg_gtav.ini`, `Run_GTAV.exe`,
     `commandline.txt`, `d3d11.dll`, `dinput8.dll`, `dsound.dll`, `dxgi.dll`, `socialclub.ini`,
     `steam000.wow`, `steam001.wow`, `steam_api.ini`
   - if no usable GTA5.exe at gtapath → `[error] Selected platform (steam) is invalid` →
     `Restarting as admin` → elevated relaunch with `-changegamepath -skipprocessconfirmation`
     (game-path picker UI; in Wine never crashes, just spins ~114% CPU).
4. **Game-file hash validation + backup repair** (Steam platform, with real GTA5.exe present):
   `[error] Source file steam_api64.dll doesn't match the expected hash` →
   `Unexpected error: Failed to copy game backup files (0x30,032)` →
   `Source file is invalid: steam_api64.dll`
   → client wants to copy pristine game files from `targetDir\backup\` into the GTA folder.
   **Our packs ship `backup\GTA5.exe` (58,082,288 B) but NOT `backup\steam_api64.dll`** —
   repair is impossible. Hashes are baked into altv-client.dll (PicoSHA2, binary blobs).
5. Fork's own release notes (game-packs): "Without libs\libce2.dll the client exits with code
   0xC0000005 before starting GTA V" — the fork KNOWS this crash code; user has libce2.dll
   (94-file verification passed at 13:49 and 14:12) → user's crash is a SECOND cause in the
   same pre-game-start window.

## Timing match

User: altv.exe exits 3221225477 at ~6–7 s (00:17, 13:49, 14:12 runs — all identical).
My rig: skin retries finish ≈6 s; platform check + hash validation + repair attempt ≈6–8 s.
→ user's crash is inside step 3/4 (or the game-start step right after). In Wine both failure
paths are graceful (error UI / picker), no crash — real Windows diverges.

## Eliminated hypotheses

- discord_rpc wrapper/forwarder: client has NO discord_rpc import (uses libs\discord_game_sdk.dll).
- Missing libce2.dll alone: crash persists with all 94 files verified (user 13:49 + 14:12).
- Port conflict on 9988: NSM binds external adapter, client proxy binds 127.0.0.1 — coexist.
- libce2/discord/bass missing system deps: all imports are stock Windows DLLs (checked PE
  import tables; no VC++ runtime needed by libce2).
- Registry-based Steam detection: +reg trace shows ZERO Steam/Valve/Rockstar registry reads.

## FIX SHIPPED: packfix4 (main 10c98a5beb, 2026-10-13)

User's launcher log (14:12) ended at `[info] Reading skin` — file is 1,312 B = whole file.
`cache\skin.bin` (1,841,402 B) written at 14:12:35, crash at 14:12:40. The client downloaded
the CURRENT CDN skin and crashed reading it with the 16.3.7 parser. My lab never reproduced
because the sandbox cannot reach the CDN (skin fetch 404/failed → client skipped the skin).

**Fix**: `DisableClientSkinDownload()` in connect.cpp — after config.dll generates altv.toml,
rewrite `launcherSkin = ''` + `launcherSkinsDisabled = ['default']` (idempotent; logs to
connect.log; warns and continues if altv.toml absent).

**Lab validation (packfix4, full NSM→client flow)**: client #1 log =
`Using global cdn → Updating skin → No skin specified → Using global cdn → OpenGL →
Selected platform (steam) is invalid → Restarting as admin` — skin download/read GONE,
rest of flow identical to baseline. altv.toml on disk verified rewritten.
E2E production: **43/43 PASS**.

**Commits**: d67c1e64ef (packfix4 on fix/client-architecture) → merged main 10c98a5beb.
Binaries: NSM.exe / connect.exe = 3,856,203 B, build tag `2026-10-13-packfix4`.

## PENDING after user tests packfix4 (still owed by user)

- New launcher_*.log from the packfix4 run (expect "No skin specified", no crash at ~6 s;
  then either GTA V starts, or the KNOWN next issue appears: `steam_api64.dll doesn't match
  the expected hash` → `Failed to copy game backup files` — packs lack backup\steam_api64.dll).
- proxy_access.log paste (18 KB) — maps the client↔NSM dialog on a real machine.
- cache\skin.bin (zip+attach) — would let us reproduce the original crash in Wine for proof.
- WER event one-liner — faulting module confirmation.
- GTA5.exe Length in their Steam GTA V folder — confirms whether the client modified the game.

## Required user evidence (asked 3rd time)

1. `%LOCALAPPDATA%\39a4cb14b4afd8c1eef1667c74e3b5936238c44f\logs\launcher_2026-10-13-14-12-3*.log`
   (sits next to connect.log; the client's own log — will show exactly which of the lines above
   their machine died after).
2. WER event: `powershell Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000} -MaxEvents 50 | Where-Object {$_.Message -like '*altv*'} | Select-Object -First 2 -ExpandProperty Message`
3. Their GTA folder state: does `C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V\GTA5.exe`
   still have Steam's size (~80 MB) or 58,082,288 B (= our backup exe was copied in — game modified)?

## Candidate fixes (NOT yet implemented — need user evidence first)

- Packs: add `backup\steam_api64.dll` (source must be verified — not distributed anywhere by the fork).
- NSM pre-flight: hash-check game files before launch; on client crash, parse + surface
  `launcher_*.log` tail in NSM UI (would have shown this error on day 1).
- GTA build compatibility: expected hashes are 16.3.7-era; user's Oct-2026 Steam GTA V build
  almost certainly differs → likely needs the fork's supported build or the shipped backup files.

## Key artifacts / paths

- Rig script: `test-client-repro.sh` (headless, nohup to /tmp/repro2.log; never pipe its output).
- Extracted runtime: /var/tmp/nsmreal/prefix/drive_c/rt (95 files; backup\ has ONLY GTA5.exe).
- Client logs seen this turn: launcher_2026-10-13-17-28-50.log (platform invalid → admin restart),
  17-38-16.log (steam_api64 hash mismatch → Failed to copy game backup files).
- Fork releases: game-packs (mp1 + libce2.dll), v1.0.1 (NSM.exe/connect.exe + js-module.dll +
  libnode.dll 104 MB — SERVER modules, needed by gtamp-server for JS resources).
- Client local proxy serves ui\index.html; cachePath = baseDir\cache (NSM sets it).
