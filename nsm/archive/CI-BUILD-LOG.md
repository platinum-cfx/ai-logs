# CI BUILD LEDGER — every Actions run and what it taught us
_Run IDs are on github.com/platinum-cfx/NSM-FIVEM → Actions. W=Windows, L=Linux.*

## Stock phase (branch: main)
| Run | Product | Outcome | Cause / fix that followed |
|---|---|---|---|
| 38473820239 | fxserver W | ❌ 80s | my `./$script` pwsh bug → `& .\script.ps1` |
| 38474444844 | fxserver W | ❌ 8m | submodules never cloned: 151 gitlinks lost in import → restored |
| 38476561599 | fxserver W | ❌ 11m | gitlinks commit was tree-only (9ca77fd) → full tree restored (533b978) |
| 38477753519 | fxserver W | ❌ 12m | gyp needs distutils (py3.12) → setuptools into every python |
| 38482120266 | fxserver W | ❌ 12m | MSB8036 SDK 22000 → retarget to installed SDK |
| 38483575112 | fxserver W | ❌ 12m | my detector picked "wdf" → version-shaped filter |
| 38492059227 | fxserver W | ❌ ~2h | **MSBuild GREEN**, died at sym-upload → dry-run skip (45a73d7) |
| 38492061122 | fivem W | ❌ ~2.5h | **MSBuild GREEN** (after 66-file/14-symlink restore), died at sym-upload |
| 38492063147 | fxserver L | ❌ 25m | docker build missing `-f` → fixed |
| 38494643821 | fxserver L | ❌ ~1h | edge-git vs libcurl 7.52 symbol crash → pin git~=2.26 |
| 38497053152 | fxserver L | ❌ ~1h | **build complete**, genapi.sh exec bit → restored (d8c9ffc) |
| (post-ssh-fix) | fxserver L | ❌ | ssh-add empty key post-build → dry-run guard (eafaec4) |
| 38499403735 | fxserver W | ✅ **GREEN** | 269MB artifact — first full success |
| 38502753590 | fxserver L | ✅ **GREEN** | fx.tar.xz |
| 38506909846/264 | (UI clicks) | ⚠️ no-ops | user clicked Run workflow — 0 min, 0 artifacts, harmless |

## Rebrand phase (branch: a1-rebrand)
| Run | Product | Outcome | Note |
|---|---|---|---|
| 38508172296 | fivem W | ❌ ~2h | **MSBuild GREEN — NSM.exe born.** Died at CLIENT sym-upload → cd65092. 504MB artifact → v0.1 release |
| 38519506200 | fivem W | ⛔ cancelled | casualty of my accidental re-dispatch (disclosed) |
| 38521297504 | fivem W | ⏳ in flight | **v0.2** — all 6 rebrand commits + PackClient. Started 06:16 UTC 10-14 |
| 38520403407 | fxserver W | ⏳ in flight | **first nsm-server.exe build**. Started 06:07 UTC 10-14 |

## Quota ledger (approx.)
Private repo: 2,000 included min/mo; Windows burns 2×, Linux 1×. Pre-project usage
~313 units (user's NSM repo CI). This project has burned roughly: W runs ≈ 11h real
(~1320 units) + L runs ≈ 3h (~180 units) ≈ **~1800 of 2000** — the wall is close.
**If new dispatches fail to start with a billing error: ask user to flip repo public
(unlimited free Actions; content already equivalent to public fivem-source).**

## 2026-10-14 ~13:15 UTC — v0.2 milestone
- Server run 38520403407 artifact pulled, verified nsm-server.exe + all server DLLs.
- Packaged full server per Invoke-PackServer recipe: bins (no pdbs) + data trees + system resources BUILT LOCALLY (monitor from txAdmin v8.1.1, chat webpack-built w/ node 20, yarn+webpack copied) + cfx-server-data resources + server.cfg + start.bat.
- **RELEASE nsm-v0.2-preview** (id 412737383): NSM-server-v0.2-preview.zip (68.5 MB) uploaded.
- Client fix: commit bbe05c1 (commit 7/N: ProductExeName FiveM.exe→NSM.exe in cfxBuildContext.psm1); client run 38568447578 in progress, ETA ~15:00 UTC. When green → attach NSM-client zip to same release.
- Rebrand verified in server binaries: nsm-server.exe has 8 "NSM" hits; only fivem.net remnant = terms URL string (leak sweep later).

## 2026-10-14 ~13:25 UTC — server crash diagnosed & fixed
- User report: nsm-server.exe opens then crashes.
- Root cause: data/server/components.json lists **svadhesive** — a PRIVATE Cfx component (no public source; official CI gets it via cfxSetupPrivate). Our public-source build has no svadhesive.dll → component loader fatal on boot.
- Official public-build behavior found in code/tools/build/run_postbuild.ps1:170-177: "for public source builds, remove adhesive from the components list" when dll absent. Our CI never runs run_postbuild (it early-returns in CI env) and I package manually from the artifact → step was missed.
- Fix: removed svadhesive from components.json in package; also removed stale monitor/starter.js per postbuild. Re-zipped (68.5MB), replaced release asset on nsm-v0.2-preview (old asset 640438038 deleted, new uploaded).
- **PACKAGING RULE (future runs): after assembling server package, strip svadhesive if svadhesive.dll absent.**
- Verified programmatically: all 28 remaining components.json entries map to shipped DLLs.

## 2026-10-14 ~13:40 UTC — second crash diagnosis round (user: "does the same thing")
- Wine reproduction: BOTH our build and OFFICIAL FXServer crash 0xC0000005 in CoreRT.dll early-init under wine (wine artifact, pre-component-load) → wine useless for full boot test; but proves crash handler works (dumps written to crashes/).
- Imported-check of all binaries: clean (d3d11/gdiplus etc. = system dlls).
- **Full diff vs official server.7z (runtime.fivem.net, build 37287)** found REAL gap: **natives_server.lua/.zip/.d.ts/.js + rpc_natives.json were missing** — these are GENERATED (prebuild_natives.cmd: curl static.cfx.re/natives/natives.lua → ext/natives lua53 codegen). Our CI never ran prebuild_natives; data/shared is gitignored for these. Server-side lua natives = required by every resource; likely crash when first resource (mapmanager/chat, lua) calls a native at boot.
- Also: natives_cfx.lua (codegen input) needs Cfx internal native-doc-gen pipeline → used official's generated natives files instead (hash-based bindings, version-independent; fork-drift risk limited to newest natives).
- Restored 4 mono portable-PDBs from artifact bins (had been swept with pdbs).
- Re-zipped + replaced release asset (~68.8MB, 3rd revision).
- KEY LESSONS RECORDED: (1) packaging must mirror prebuild_natives outputs; (2) wine+relay+minidump workflow works for reproduction; (3) ext/natives has full codegen toolkit + stash (lua53.exe runs under wine; natives DB downloadable from static.cfx.re).
- CLIENT NOTE: client package (cfxPackClient copies data\shared\*) is missing the CLIENT natives (natives_0193D0AF/21E43A33/universal + v8 + rpc) for the same reason — must inject before shipping client zip.
- Client run 38568447578 still in_progress at 13:40 UTC.

## 2026-10-14 ~13:55 UTC — third crash round (user retested, still crashes)
- User pasted crash dump AS TEXT (binary-mangled). Recovered: Win11 22H2 (build 22621), Ryzen 9 6900HS, cmdline `nsm-server.exe +exec server.cfg`, folder C:\Users\austi\Desktop\NSM-Server.
- Decoded from module list: 19/29 component DLLs loaded (net/tcp/http/packet/instance/net/vfs-core/resources-core/scripting-server/conhost/http-client/curl/scripting-core/scripting-mono+mono-2.0/devtools/scripting-lua/vfs-impl/pool-sizes/server-impl/nng/voip-mumble). NOT loaded: server-main, server-monitor, state-fivesv, state-rdr3sv, fxdk, resources-metadata-lua, scripting-mono-v2, scripting-node, server-gui. Crash while loading component #20 in topo order (loader is fatal-clean on missing names; crash = in-flight DLL load).
- Wine findings: crash = DllGameComponent::CreateComponent (DllGameComponent.Win32.cpp:120) with ZERO components loaded (wine-only wall, BOTH builds hit it; solo-component runs under wine are all clean; empty components.json exits clean). Wine cannot reach user's crash point.
- All runtime imports of all DLLs verified against shipped VC runtimes: satisfied (not a missing-export problem).
- **llvm-symbolizer 19.1.0 installed** (/usr/local/bin, from LLVM release tarball; apt/pip broken for this). PDBs from artifact at /var/tmp/srv/art/.build-cache/.../dbg/. READY to symbolicate user's dump.
- AWAITING: user to ATTACH the actual .dmp file (not paste) + confirm natives_server.lua present in their folder (zip v3 check).

## 2026-10-14 ~14:05 UTC — bisect round (v4 zip)
- 2nd pasted dump = same crash, mangled; uploads/ still has no .dmp file. Pasted text recovered: user's stack had LoadLibrary("wintrust"), ("dcomp"), ("D3DCOMPILER_47") patterns in flight; voip-server-mumble.dll path; console::Context / ConsoleCommandManager strings; CRT locale/env parsing; CPU brand strings. All = normal leftovers, no smoking gun except: crash during a LoadLibrary that never completes.
- Wine deep-dive: wine crash = heap-corruption write (0xC0000005 write to freed block) at CoreRT+0x17cc9 (DllGameComponent::CreateComponent:120 = LoadLibrary line, likely inlined HardErrorScope/converter allocs at function entry) — occurs at FIRST CreateComponent with multi-component list only (solos all clean; swapping official gui+imgui in didn't change it) => wine-only heap quirk, NOT user's crash. Wine CANNOT reproduce user's #20 crash.
- Binary structure of our 9 unloaded DLLs vs official: essentially identical (sizes within 5%, same section counts) — no build-config mismatch.
- **v4 SHIPPED**: components.json trimmed 28→25 by removing non-essential suspects: citizen:server:gui (prime suspect — wine stack had its path; imports gdiplus+imgui; user's machine never maps it; wintrust/dcomp load patterns nearby), citizen:server:fxdk (devkit), citizen:server:state:rdr3sv (RedM). DLLs still shipped in zip (just not loaded). If v4 boots on user machine => culprit among the 3 (gui most likely). If still crashes => #20 is among the essential 6 (main/monitor/state-fivesv/metadata-lua/mono-v2/node) => NEED the actual .dmp file.
- llvm-symbolizer + PDBs ready for instant analysis when real dump arrives.
- Client build 38568447578 STILL in_progress at 14:05 UTC (started 13:01, unusually long — check for hang next turn).

## 2026-10-14 ~15:30 UTC — sandbox reset + decode-tool handoff
- v4 (gui/fxdk/rdr3sv removed) STILL CRASHED on user machine => culprit in the essential 6 (main/monitor/state-fivesv/metadata-lua/mono-v2/node), OR same-point-as-before crash. New dump: ed51b4df-d20d-4e1c-bcbd-4c53ff89afd9.dmp.
- User cannot attach .dmp (too big for chat); 3rd text paste confirmed useless for exception data (expected — chat strips non-printable bytes).
- Gave user a PowerShell MDMP decoder (decode.ps1): auto-picks newest non-full .dmp in crashes dir, prints exception code/addr/params + RIP/RSP/regs + full module list (base+size, load order) + 8KB stack scan mapped to module+offset. Output auto-copied to clipboard + saved to Desktop\crash-decode.txt. This yields everything needed to symbolicate.
- Alternative offered: curl upload of the .dmp to litterbox.catbox.moe (72h temp) if they prefer sending the whole file.
- SANDBOX RESET between turns: /var/tmp wiped (llvm-symbolizer, PDB artifact, official dlls, wine tree ALL GONE). Re-staging started in background (process symbolizer-staging-a01dc174, log /var/tmp/dl/stage.log): artifact 11876098474 PDBs + LLVM 19.1.0 symbolizer. If reset again next turn, redo via recipes in Key Results.
- Client run 38568447578: build job running since 13:01:59Z, ~2.5h — long but client is the big target; GH timeout 6h. Check next turn; if concluded, build client zip per recipe.

## 2026-10-14 14:32 UTC — client build failure diagnosed + fixed + redispatched
- Client run 38568447578 (bbe05c1) FAILED at 14:18:31Z after 78 min: ALL compilation+linking succeeded; failure at final pack step: cfxPackClient.psm1:99 `Copy-Item $binRoot\RGL-ElevationHelper.exe` -> "Cannot find path". Root cause: RGL-ElevationHelper.exe comes "# From closed" (Cfx.re private binary store, normally placed via Invoke-CfxSetupPrivate which no-ops without their credentials). Runtime code has ZERO references to it (code search: only the pack script) — it is only needed for Rockstar-Games-Launcher-owned GTA copies; user is on Steam.
- Audited rest of pack flow for more closed deps: CEF ✓ (vendored), UI zips ✓ (built), FiveM_Diag.exe ✓ (built), bootstrapper ✓ (CitiLaunch linked), xz.exe ✓ (committed in repo, 221696 B). GCI skipped (no PrivateRoot). Sentry skipped (not public build). RGL was the ONLY gap.
- PATCHED code/tools/ci/psm1/cfxPackClient.psm1 on a1-rebrand: conditional `if (Test-Path ...)` around the RGL copy. Commits: d6555f62 (accidental no-op — line-ending assert failed, content unchanged) + 08ef67bc (real patch, blob b5abbf15, verified via API). New a1-rebrand tip = 08ef67bc (was bbe05c1).
- Redispatched client: run 38581479629 on 08ef67bc, in_progress 14:32:49Z. ETA ~80 min. If green: assemble client zip with natives injection per Key Results, attach to nsm-v0.2-preview release.
- Symbolizer staging COMPLETE: /usr/local/bin/llvm-symbolizer 19.1.0 + 44 PDBs in /var/tmp/srv/art/.build-cache/bin/server/windows/release/dbg/ (from artifact 11876098474). Sandbox survived this turn (no reset).
- Still waiting on user to run decode.ps1 and paste crash-decode output (server critical path).
- Note: /var/tmp reset DID happen between turns 14:05->14:15; re-staged within 40s via background process. If it resets again, redo from recipes.

## 2026-10-14 ~15:00 UTC — ROOT CAUSE FOUND AND FIXED (v5 shipped)
**User's decode.ps1 output cracked it.** Crash: 0xC0000005 READ at 0x0, RIP=msvcp140.dll+0x13028. Symbolication chain:
- msvcp140+0x13028 = mtx_do_lock (mutex.cpp:100) [MS PDB from msdl symbol server, GUID 0753A17D158361AF59555FCC6FB65C03 age 1]
- Caller frames: CoreRT+0x2BC65 = std::unique_lock<std::mutex> ctor, CoreRT+0x2B329 = thread lambda, CoreRT+0x2AD83 = std::thread::_Invoke; rcx/rsi = g_instanceRegistry (CoreRT .data)
- Faulting instruction: lea rcx,[rsi+8]; mov rax,[rcx]; mov rax,[rax] → reads *(mutex+8) as pointer, got NULL
**ROOT CAUSE: VC runtime ABI mismatch.** Binaries built with runner toolset 14.44.35207; shipped data/redist/crt msvcp140.dll = 14.34.31938 (repo-committed). App-local old CRT shadows user's newer system one. Old mtx_do_lock interprets new-layout std::mutex; field +8 = NULL → null deref on first cross-thread mutex lock (CoreRT worker thread locks g_instanceRegistry). Explains: every build crashing, varying loaded-component counts (timing race), dump signature, and wine heap weirdness. Upstream avoids it by building with the 14.34-era VS their crt matches (cfxSetupVS uses whatever VS is installed, no pin).
**FIX:** added 'crt' product mode to p2-build.yml (commits 5d7e60e3, 11056d38, 1725ccd7, b47f34e0 — final working) that uploads the runner's newest x64 VC143 CRT (14.44.35211) as artifact. 4 dispatch iterations: 1) fetch-crt.yml approach dead (workflow_dispatch requires default-branch registration — deleted), 2) redist layout is MSVC\v143 not versioned dirs, 3) FileVersion has 'built by: cloudtest' suffix breaking [version] cast, 4) success: artifact 11904039849, all DLLs 14.44.35211.
**v5 SHIPPED** (asset 640716182): v4 + CRTs swapped (10 files incl. new vcruntime140_threads.dll), components.json still 25 (gui/fxdk/rdr3sv still off — keep one variable changed; restore after boot confirmed).
**Repo fixed permanently:** data/redist/crt updated to 14.44.35211 (10 commits 881b41a1..4c84cd4e) — future server+client builds pack the right CRT. NOTE: running client build 38581479629 (still in_progress at 15:00) checked out BEFORE the crt commit → its cache has 14.34 CRTs → MUST swap CRTs into caches/fivereborn/bin/ during client zip assembly.
- a1-rebrand tip now 4c84cd4e. p2-build.yml accepts product: fxserver|fivem|fxserver-linux|crt.

## 2026-10-14 22:52 UTC — CLIENT v0.2 packaged and shipped
- Client run 38581479629: COMPLETED SUCCESS at 16:28Z (started 14:32Z, ~116 min).
- Sandbox reset again before this turn (3rd time); re-staged: client artifact 11912545721 (765MB, p2-fivem-output) + toolset-crt artifact 11904039849 (still alive, 7-day retention).
- Client artifact contents: caches/fivereborn/ = complete client app (CitizenFX.exe, CoreRT, all DLLs, CitizenFX_SubProcess_game_*.bin for GTA builds 1604-3788, bin/ with CEF 85 files, citizen/ 225 files), caches root metadata (CitizenFX.exe.xz, caches.xml, fivereborn.json, version.txt), .build-cache/ raw outputs.
- VERIFIED in source (Bootstrap.cpp:110): update-server unreachable + local CoreRT.dll present => launcher continues offline. LauncherConfig.h already rebranded: PRODUCT_NAME NSM, CONTENT_NAME "nsm", CFX_UPDATER_URL http://194.104.146.133/updates. No prod.fivem.net refs left in repo.
- Fixes applied to package:
  1. CRT swap: caches/fivereborn/bin/ had 14.34.31938 (build predates CRT repo fix) -> replaced with 14.44.35211 from toolset-crt artifact (client had the SAME server ABI bug baked in).
  2. components.json: removed "adhesive" (63->62) - adhesive.dll is closed-source Cfx (missing => FatalErrorNoReport at boot). Only missing component; all 62 others verified present on disk.
  3. Natives: NO injection needed - build generated them all (natives_0193D0AF.lua 2,061,978 B, natives_21E43A33.lua, natives_universal, natives_server + zips + v8 .js/.d.ts + natives_blob.bin).
- NSM-client-v0.2-preview.zip (229,315,451 B, asset 641926819) = NSM-Client/ folder = fivereborn cache content, portable: run CitizenFX.exe (name kept for self-update compat; binary is the NSM rebrand).
- Server v5: user has NOT yet reported test results (7h gap since v5 shipped at ~15:00Z).
- Next: user tests v5 server -> boots? -> client connect test (run CitizenFX.exe with Steam running, F8 console, connect IP:30120) -> two-player acceptance test. Queued: masterlist/keyserver on VPS 194.104.146.133, restore server gui/fxdk/rdr3sv components, adhesive/RGL closed-binary filtering in pack scripts.

## 2026-10-14 23:00 UTC — client "Unknown component adhesive" crash: fixed (client v2 shipped)
- User tested client within 2 min of first upload (log 22:53): fatal at 58s: "Unknown component adhesive" -> crash dialog + DumpServer capture.
- Root cause: EarlyMode.Win32.cpp force-loads {"legitimacy","adhesive"} at early boot. ComponentLoader.cpp:330 maps unknown "adhesive" -> "sticky", but "sticky" was never in components.json (repo data/client/components.json has adhesive, not sticky) => fallback failed => FatalError (prints ORIGINAL name "adhesive"). Removing adhesive from json (my earlier fix) made it WORSE - registered-adhesive would have failed differently (missing dll fatal); the correct fix = replace adhesive with sticky (sticky.dll IS built+shipped, it's the open adhesive replacement; code/components/sticky exists).
- FIXED: repo data/client/components.json adhesive->sticky (commit 6da43410279a) + rebuilt package (components.json: 63 entries incl sticky, no adhesive) + re-uploaded client asset 641942623 (NSM-client-v0.2-preview.zip, 229,315,456 B).
- Server v5 re-verified from the live asset: 25 components, no svadhesive, ZERO missing DLLs (Server.cpp's svadhesive reference is just an fxdk-mode skip; server json has no svadhesive). Server unaffected by this bug.
- GameMode.Win32.cpp hardcoded loads verified present in json: http-client, citizen:game:main, nui:core, conhost:v2, fxdk:main ✓. EarlyMode: legitimacy ✓ sticky ✓ (now).
- Client log otherwise healthy through 58s (boot, subprocess launch started). Next unknowns beyond this point: game subprocess component loads, legitimacy/Steam check, GTA launch.
