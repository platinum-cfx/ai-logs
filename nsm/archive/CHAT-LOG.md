# NSM PROJECT — CHRONOLOGICAL CHAT LOG (reconstructed)
_Honest framing: early sessions were auto-summarized; this is a faithful reconstruction
from the session memory + the current session, not verbatim transcript. Decisions and
outcomes are exact; wording is condensed. Timestamps UTC where known._

## ERA 0 — Before A1 (historical context)
- Earlier project phases: NSM launcher wrapper work (packfix5: binary patching of a
  3,878,328-byte exe, PE-timestamp-only diffs, E2E 43/43), alt runtime experiments
  (cancelled), masterlist glue tests. Old artifacts live in workspace `nsm/bin`,
  `nsm/src`, `nsm/mocks`, `nsm/matrix-logs`, `nsm/testpacks`.
- User decisions from that era that STILL bind: no WebView2/Chrome/Edge as main UI,
  one window, zero terminal commands in launcher flow, NSM.exe is THE exe, no fake
  claims, verify against evidence, additive-only edits + backups, answer "why" first.

## ERA 1 — Licensing + A1 selection
- Licensing assessment completed (workspace `nsm/docs/fivem-source/licensing-assessment.md`,
  includes verbatim Creator PLA §1.1/§2.1/§2.2/§2.3/§7.2 quotes). Conclusion: build from
  the fivem-source snapshot, keep license files, strip Cfx branding (code yes / brand no).
- **A1 chosen explicitly** by user: build own platform from fivem-source. Protection rules
  set: never delete repos, fivem-source + NSM repos untouched, separate rebrand branch.
- Base repo prepared: squash-import of fivem-source snapshot + restored LICENSE,
  THIRD_PARTY_NOTICES.md, 10 LICENSES/*, README, BUILD-NSM.md → pushed as `0a521fa`
  to new private repo `platinum-cfx/NSM-FIVEM` (branches: main, a1-rebrand).

## ERA 2 — "You do it all" (the pivot to CI)
- User refused to run local Windows builds; ordered: "you do it all and find a way
  around it and just make it work." Pivot: GitHub Actions windows-2022 runners driven
  purely via API. Sandbox cannot build (Linux, ~13GB disk vs ~60GB need, 30-min caps).
- Reverse-engineered Cfx's own CI from the repo: fxd.ps1, build_server_windows.ps1,
  build_client.ps1, cfxBuildContext/MSBuild/Prebuild psm1s, .gitlab-ci.yml, alpine
  proot recipe. Wrote `.github/workflows/p2-build.yml`.

## ERA 3 — The debugging gauntlet (8 failed runs, each one fix)
1. Run 1 (80s): my `./$script` PowerShell expansion bug → call operator fix.
2. Run 2: **submodules never cloned** — squash-import lost all 151 gitlinks (mode 160000).
   Restored from upstream citizenfx/fivem master pins via index surgery.
   - Mid-crisis: first gitlink commit (9ca77fd) was built from a stale index and
     contained ONLY the links — full tree restored next commit (533b978). Verified.
3. Run 3: node-gyp/gyp needs `distutils` (removed in Python 3.12) → setuptools into
   EVERY runner python.
4. Run 4: MSB8036 Windows SDK 10.0.22000.0 missing on runner → cfxRunMSBuild.psm1
   now retargets to newest installed SDK.
5. Run 5: my SDK detector picked "wdf" (alphabetical sort) → filter to version-shaped
   folders, sort as versions.
6. Run 6: compile phase reached — died at CSC CS2001 (clrcore-v2/Math missing) +
   client-side C1083 debugging_buildflags.h + MSB3073 msobj140.dll + MSB8066 v8 curl.
   **Root cause: squash-import ALSO lost 66 files + flattened 14 symlinks + stripped
   genapi.sh's exec bit.** Full upstream-vs-mirror tree diff, everything restored (9251764).
7. Linux run 1: docker build missing `-f` flag (my workflow bug).
8. Linux run 2: edge git vs pinned libcurl 7.72 (`curl_global_trace` symbol) → pin
   `git~=2.26` in proot_prepare.sh (c7c7777). Then `genapi.sh: Permission denied`
   → exec bit restored (d8c9ffc). Then ssh-add with empty key killed the job AFTER a
   successful build → guarded behind dry-run (eafaec4).
- Windows server+client symbol-upload steps also killed jobs after successful MSBuilds
  → both psm1s skip in dry-run (45a73d7, cd65092).

## ERA 4 — GREEN (stock phase complete)
- **Windows server: GREEN** (run 38499403735, 269MB artifact).
- **Linux server: GREEN** (fx.tar.xz). **Windows client: compiled green.**
- User questions answered along the way: masterlist.exe (mock only; real one is the
  Node service on VPS 194.104.146.133), where NSM.exe is (didn't exist yet), citizenfx
  org survey (87 repos; cfx-server-data + txAdmin matter; no shortcuts), "so we copied
  fivem?" (yes — code yes/brand no, that's A1; "your own FiveM"), escrowed scripts
  (can't and won't crack Cfx DRM; author route + future NSM escrow), mod menus
  (allowed; strip scanner later), txAdmin (user wants OWN admin panel from scratch),
  keymaster (cut it, queued with commit 6), "network" clarified = players seeing each
  other in-game (that's the engine itself, already compiled in).

## ERA 5 — Rebrand (a1-rebrand, 6 commits)
- Branch fast-forwarded to main (all CI fixes), then:
  1. `819f297` FiveM.exe→NSM.exe (launcher premake targetname)
  2. `b7183f7` PRODUCT_NAME/CONTENT_NAME/LINK_PROTOCOL → NSM/nsm/nsm:// (LauncherConfig.h)
  3. `67460a4` FXServer.exe→nsm-server.exe (+ alpine script references)
  4. `7187874` CFX_UPDATER_URL → http://194.104.146.133/updates
  5. `b4c6d04` launcher.rc metadata (Product/Company NSM, folder name, copyright w/ Cfx attribution)
  6. `cd65092` client symbols dry-run skip
- User decisions added: reuse altV networking from old repo (`altv-test/masterlist`);
  masterlist must be an .exe like the old altV one; user's paid scripts are escrowed
  (position held: no DRM circumvention).

## ERA 6 — v0.1 preview + user's real test
- First rebranded client build completed MSBuild but died at pre-fix symbols step;
  504MB artifact still captured. Extracted NSM.exe (4.9MB) to workspace; packaged
  607-file 490MB zip → GitHub Release `nsm-v0.1-preview`.
- **User ran it on their PC.** Log: NSM.exe LAUNCHED, logged as "NSM", crash handler
  worked, then `Could not load CitizenGame.dll` (0x8007007e) and on retry
  `Could not find component cache storage file (components.json)`.
  Diagnosis: v0.1 = raw build output, missing PackClient staging (CEF, components.json).
  v0.1 declared a dead end BY CONSTRUCTION.
- v0.2 dispatched (all 6 rebrand commits + symbols fix → PackClient runs). During
  monitoring: my status-script misread led me to re-dispatch the client, which
  auto-cancelled the in-flight run (~20 min lost, my error, disclosed to user).
  Fresh client run 38521297504 (06:16) + server run 38520403407 (06:07) in flight.
- User asked for Linux-side speedups: explained client is Windows-only physics;
  dispatched server build in parallel; promised build-caching investigation later.
- User asked for this archive (context-limit insurance).

## Standing user profile / preferences
- Non-technical; wants plain-language "why" first; short replies; gets sleepy; eager
  ("uppppdate mee"); pings often with "update"/"go". Atlantic Daylight Time (UTC−3).
- Must NOT click "Run workflow" in GitHub UI (creates no-ops, can cancel real runs).
- Everything agent-executed; user only: downloads, extracts, double-clicks, reports
  error text verbatim (they're good at this — the logs they pasted drove every fix).
