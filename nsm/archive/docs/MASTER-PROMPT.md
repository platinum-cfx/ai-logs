# NSM PROJECT — MASTER PROMPT
_Paste this as your first message in any new chat to resume with full state. Written 2026-10-14, ~06:30 UTC._

## MISSION
Build **NSM** — the user's own FiveM-class GTA V multiplayer platform — from their copy of the FiveM source code. Own client (NSM.exe), own server (nsm-server.exe), own masterlist. Fully disconnected from Cfx/FiveM control. Final acceptance = runs on the user's real Windows PC with legit GTA V (Steam). **No success claims without real evidence; no unverified builds.**

## ACCESS (required to do anything)
- GitHub token: `[REDACTED_GITHUB_TOKEN]`
- Repo: `platinum-cfx/NSM-FIVEM` (private). Default branch `main` (stock+CI fixes), branch `a1-rebrand` (the NSM rebrand).
- API: `Authorization: token <T>` header. Raw files: `https://raw.githubusercontent.com/platinum-cfx/NSM-FIVEM/<branch>/<path>`.
- CI is driven ONLY via API dispatches: `POST /repos/platinum-cfx/NSM-FIVEM/actions/workflows/p2-build.yml/dispatches` with `{"ref":"<branch>","inputs":{"product":"fxserver"|"fivem"|"fxserver-linux"}}`. **User must never click "Run workflow" in the UI** (no-op runs at 03:34/06:00/06:01 prove it happened; it can confuse/cancel real runs).
- User's other repos: `fivem-source` (untouched mirror, do not touch), `NSM` (old project, untouched), `altv-test` (has `masterlist/` dir — the old altV masterlist/networking the user wants reused), `GTAMPv1` (old own-engine launcher), `coremp` (altV modules), forked `txAdmin`, `cfx-server-data`, `natives`.

## BUILD SYSTEM (proven, all green on stock)
- GH Actions, runner `windows-2022` (client+server) / `ubuntu-latest` (linux server via upstream Alpine/proot Docker recipe from `code/tools/ci/docker-builder/Dockerfile`).
- Workflow: `.github/workflows/p2-build.yml`. Env the upstream scripts need: `CI=true`, `CFX_DRY_RUN=true`, `CFX_PRODUCT_NAME`, `CI_COMMIT_REF_NAME`, `CI_COMMIT_SHA`, `CI_PROJECT_DIR`, `CI_PIPELINE_ID` (linux). NEVER set `CFX_RETAIL_BUILD`/`CFX_FEATURE_BRANCH_BUILD` (demands private URIs).
- Server = `code/tools/ci/build_server_windows.ps1`; client = `build_client.ps1` (needs CEF auto-download + yarn); linux = `build_server_docker_alpine.sh` (fivem-private now optional when `FIVEM_PRIVATE_URI` unset).
- Local-bare-repo edit method (no full clone needed): clone `--bare`, `git fetch` branch, python index plumbing with `GIT_INDEX_FILE` (read-tree FETCH_HEAD → hash-object --stdin → update-index --cacheinfo → write-tree → commit-tree -p parent → update-ref → push). ALWAYS verify tree: 13550 entries, 151 gitlinks (160000), 14 symlinks (120000), workflow present.
- Release packaging: artifact zip → rezip release folder as `NSM/<files>` → GitHub Release + streaming asset upload via python `http.client` (curl --data-binary @file OOMs at 490MB).

## FIXES ALREADY MADE (do not re-debug)
1. Squash-import lost 151 submodule gitlinks → restored from upstream master pins.
2. Import lost 66 files + flattened 14 symlinks + stripped genapi.sh exec bit → all restored (fixed every CSC/C1083/MSB3073/MSB8066 compile error).
3. `cfxRunMSBuild.psm1`: retargets WindowsTargetPlatformVersion to newest installed SDK (runner lacks 10.0.22000).
4. setuptools into EVERY python (node-gyp needs distutils, py3.12+).
5. `git~=2.26` pinned in proot_prepare.sh (2026 edge git vs libcurl 7.72 symbol clash).
6. Dry-run symbol-upload skips: both `cfxUploadServerSymbols.psm1` and `cfxUploadClientSymbols.psm1` (they killed jobs AFTER successful MSBuild).
7. Linux ssh-agent/ssh-add guarded behind dry-run (empty SSH_SYMBOLS_PRIVATE_KEY).

## A1 REBRAND — commits on `a1-rebrand` (in build order)
1. `819f297` launcher targetname `FiveM`→`NSM` (code/client/launcher/premake5.lua) ✅
2. `b7183f7` LauncherConfig.h five-block: PRODUCT_NAME L"NSM", CONTENT_NAME "nsm", LINK_PROTOCOL L"nsm" ✅
3. `67460a4` FXServer.exe→`nsm-server.exe` (code/server/launcher/premake5.lua + both alpine scripts) ✅
4. `7187874` CFX_UPDATER_URL → `http://194.104.146.133/updates` ✅
5. `b4c6d04` launcher.rc metadata: Product/Company=NSM, "NSM Application Data", OriginalFilename NSM.exe ✅
6. `cd65092` client symbols dry-run skip ✅

**Remaining rebrand:** masterlist/announce wiring (discovery + heartbeat → user's infra, informed by `altv-test/masterlist`), keymaster/portal-key system CUT, mutex/registry/user-agent "FiveM|Cfx" leak sweep, cfx-ui main menu → NSM design (Phase B), icons (binary asset commit).

## STATUS AT TIME OF WRITING
- Stock builds: Windows server GREEN (269MB artifact), Linux server GREEN (fx.tar.xz), Windows client compiled green (v0.1 died only at pre-fix symbols step).
- **v0.1 preview released**: https://github.com/platinum-cfx/NSM-FIVEM/releases/tag/nsm-v0.1-preview (490MB). Raw build output — user tested: NSM.exe LAUNCHED (logs as "NSM", crash handler works) then failed `CitizenGame.dll` (0x8007007e) and `components.json` missing — both expected: v0.1 lacked PackClient staging.
- **v0.2 in flight (client run 38521297504 + server run 38520403407, started 06:07/06:16 UTC 2026-10-14, ETA ~08:00-08:20 UTC)** — first PROPERLY PACKED build with rebrand 1-6. Known risk: updater phones `194.104.146.133/updates` which serves nothing yet → if client errors on update check, fix = serve minimal manifest from VPS or defer endpoint.
- When v0.2 green: repackage release folder as `NSM-client-v0.2-preview.zip` → new GitHub Release → user tests: expects components.json+cef present, GTA V Steam scan, UI appears.
- User machine: GTA V = Steam `C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V`; old NSM at `C:\Users\austi\Desktop\NSM-main\client-new\`.
- User's masterlist: Node service on VPS 194.104.146.133 (`/api/servers`).

## STANDING DECISIONS & RULES (user-set, never violate)
- Reuse existing networking: altV networking from old repo + masterlist as an .exe (like old altV masterlist). No new networks.
- NSM.exe is THE main exe; no WebView2/Chrome/Edge main UI; one window; zero terminal commands for launcher flow.
- Mod menus: user allows them — later work item: strip/defeat client scanner (or per-server policy).
- Escrowed FiveM scripts: user owns some, wants them on NSM. Position: cannot/will not crack Cfx escrow DRM. Routes: ask authors for unencrypted builds (offer to draft messages), audit which scripts are actually escrowed, Phase B = own NSM escrow system for sellers.
- txAdmin: user wants OWN admin panel from scratch (NSM Admin, Node.js, phased: MVP = dashboard+console+players+bans). Do NOT spend cycles rebranding txAdmin (throwaway).
- Actions quota: private repo = 2000 min/mo (Windows 2×, Linux 1×). ~Heavily used. If wall: ask user to flip repo public (unlimited free).
- "You do it all" — user runs nothing, agent executes everything via API. BUILD-NSM.md in repo is reference only.
- Additive only; backup before modify; verify against evidence; scoped plan before disruptive changes; separate branch (a1-rebrand) for rebrand; no repo/file deletions; answer "why" first; ultra-short replies preferred; user is non-technical — plain language.
- Times: user is Atlantic Daylight (UTC−3). Quota-conscious: each CI cycle ~2h Windows.

## NEXT STEPS (in order)
1. Collect v0.2 client+server results → if green: package v0.2 release (client + nsm-server.exe) → user run-test (report: components.json gone? GTA V scan? updater wall?).
2. If updater wall: serve minimal update manifest from VPS or temporarily neutralize update check (code change).
3. Commit 6: masterlist/announce wiring (study `altv-test/masterlist` first) + cut keymaster (server license key check — find in citizen-server-impl / server boot code).
4. Commit 7: leak sweep (mutex, registry, user-agent, remaining "FiveM"/"CitizenFX" strings).
5. Stand up first test server: nsm-server.exe + cfx-server-data resources (user's fork) on user PC/VPS; server.cfg; then 2-player test.
6. Phase B backlog: cfx-ui main menu → NSM design; NSM Admin panel (from scratch); build caching for faster CI cycles; NSM escrow; icons.
