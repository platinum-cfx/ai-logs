# AxiomFX / NSM Complete Rebrand — Mission Status Tracker
_Mission prompt accepted 2026-10-15. This file is the running, auditable record._

## Baseline (recorded 2026-10-15, Phase 1)

| Item | Value |
|---|---|
| Stock baseline branch | `main` @ `5afdec195255e5b776cfb6d15dc945d40a5e8dbb` (preserved, untouched) |
| Active rebrand branch | `a1-rebrand` @ `d6f7212f2b48e1670a9eef1c0ebde14eb0c8bcdf` |
| **New mission branch** | `axiomfx-complete-rebrand` @ `d6f7212f2b48` (created from a1-rebrand tip — all future mission commits land here) |
| Masterlist repo | `platinum-cfx/NSM-masterlist` (separate, per standing decision) |
| Website repo | `platinum-cfx/NSM-website` |
| CI | `p2-build.yml` via API dispatch only (client=fivem, server=fxserver, linux=fxserver-linux); never RETAIL |
| Shipped | **client v0.7.1-localtest (localhost endpoints, direct-binary patched)** + client v0.7 (644549113) + v0.6-preview (644549632) + server v0.7.1 (644338212) on release 412737383 |
| Build in flight | wave builds #38 (fivem) + #39 (fxserver) @ 28ea7a3 on axiomfx-complete-rebrand — compile evidence for the wave commit |
| Spend | ≈$9.40 of $100 Actions budget |

## Initial occurrence inventory (Phase 1, first pass)

GitHub code-search counts on the **default branch (`main` = stock baseline — the "before" picture)**:
counts capped at 1000; the full a1-rebrand tree sweep (bare clone + git grep, incl. YAML/JSON/lua/rc/manifests) is the next pass.

| Term | ~Files (main branch) |
|---|---|
| `CitizenFX` | 374 |
| `FiveM` | 224 |
| `cfx.re` | 665 |
| `fivem://` | 3 |
| `FXServer` | 156 |

## Phase scorecard

| Phase | Status | Notes |
|---|---|---|
| 1 — Baseline + branch | ✅ DONE | This file + branch `axiomfx-complete-rebrand` |
| 2 — Licensing/provenance | 🟡 started | Root LICENSE read: © Take-Two; core "Files" (code/client/{shared,citicore,launcher,common}, code/tools, code/components/citizen-*, font-renderer, vfs-core, vendor/*.lua) under **LGPLv2** — modifiable/redistributable under those terms; rest governed by Rockstar Creator Platform License. Full categorization report pending. |
| 3 — Product rebrand | ✅ ~95% | v0.1–v0.7 shipped + **waves 1-4 source pass committed (28ea7a3)**: locale .po display text, error/console strings, CitizenFX.log→NSM.log, fivem.cfg→nsm.cfg, fivem*.ico→nsm*.ico, launcher.manifest identity, MiniDump NSM.exe+ hashes. Remaining: REVIEW-bucket triage (950 identifier lines), cfx-ui main menu, green boot logo. |
| 4 — Masterlist audit | ❌ pending | Masterlist v2 exists (NSM-masterlist repo, Go+py). Endpoint verification report pending. |
| 5 — Upstream reference removal | 🟡 partial | Server package: 0 FiveM strings in nsm-server.exe, only Mono .NET API DLLs retain CitizenFX (script compat, documented). Source tree sweep pending. |
| 6 — Repo-wide search | ✅ inventory done | 13,553 files swept via bare-clone grep: 6,394 matches / 2,143 files classified (see `branding/inventory/INVENTORY-SUMMARY.md` + `ALL-MATCHES.txt`). Rebrand execution: Wave 1 (user-visible, 72 files) → Wave 2 (URLs) → Wave 3 (docs) → Wave 4 (triage). |
| 7 — Build + runtime validation | 🟡 client ✅ / server 🔴 | **Client v0.7 SHIPPED** (asset 644549113, 233,710,030 B, all packaging asserts green, fresh d6f7212 launcher). Wave builds #38/#39 (fxserver+fivem @28ea7a3) in flight. Server still gated: | Server asserts at boot: `Registry.h:164 instance.GetRef()` = a `GetComponent<T>()` hitting an empty per-object registry. Same assert on v0.5/v0.7/v0.7.1 → ordering/wiring, not missing files. v0.7.1 package verified structurally perfect (25/25 DLLs, imports resolve, deps satisfied, ServerMain chain intact). **Awaiting user's fresh crash dump (crashes/ folder, non-`-full` file) to pinpoint the faulting component.** |
| 8 — Delivery reports | 🟡 partial | Releases shipped; consolidated reports (branding changes, search, licensing, masterlist, build logs) to be assembled as phases complete. |

## Known licensing facts (Phase 2 running notes)

- Root LICENSE: © 2023 Take-Two Interactive. Platform under Rockstar Games Creator Platform License (fivem.net/terms); the listed "Files" dirs under LGPLv2.1 (redistribution + modification permitted under LGPL terms); THIRD_PARTY_NOTICES.md governs vendored code.
- svadhesive: Cfx-internal, absent from public source (0 paths in 15,442-entry tree) — cannot be rebuilt; removed from boot list (v0.7.1) since no component declares a dependency on it.
- legitimacy.dll, sticky.dll: prebuilt closed components in the client; documented blockers, not modified.

## Next actions (in order)

1. **[P0, Phase 7]** User sends fresh v0.7.1 crash dump → decode → targeted fix (package-level or small code fix on `axiomfx-complete-rebrand` + fxserver rebuild ~2h).
2. **[Phase 7]** Client v0.7 run 38754548380 completes (in the big MSVC build step, no stall) → package `NSM-client-v0.7.zip` → user retest.
3. **[Phase 7]** Wave builds #38/#39 complete → verify green → v0.8 server/client packaging. Server crash fix STILL P0 (need user's crash dump).
4. **[Phase 2 — OWN THE NETWORK, user VPS ready]** (a) user buys domain + points DNS at 194.104.146.133; (b) reverse proxy + TLS on VPS; (c) updater endpoint (cut runtime.fivem.net); (d) game-cache mirror (needs VPS disk spec; Rockstar-data caveat documented); (e) masterlist v2 under domain; (f) own keymaster (optional).
4. **[Phase 2]** Licensing categorization report (inventory data + LICENSE/THIRD_PARTY_NOTICES review).
5. **[Phase 4]** Masterlist endpoint verification (live against VPS 194.104.146.133 service) + report.
6. **[Phase 3 remainder]** Green boot logo + client main-menu (cfx-ui) redesign after v0.7 ships.


---
## Phase 1.5 — NSM Local Stack v1 (2026-10-15 evening) — SHIPPED
- **NSM-Masterlist.exe = ONE backend exe** (in NSM-client-v0.7.2-localtest.zip, asset 644732472):
  masterlist v2 + NSM website (blue skin, accounts, server list, upvotes) + accounts with roles
  (owner=Cravenz / admin / staff / user; /admin/users staff page) + game-cache pass-through proxy
  (routes /a /c /d /e /f /k /l /p /r /s /v /w) + updater 404. Localhost: bind 127.0.0.1:80.
  Source: platinum-cfx/NSM-masterlist @ 14b3306110 + workspace nsm/stack/.
- **NSM-client-v0.7.2-localtest** (asset 644732472): green boot logo -> blue NSM N-mark (UTF-16 XAML
  patch in NSM.exe); 10,444 CDN URLs -> local mirror routes; START-LOCALHOST.bat; all v0.7.1 patches.
- **NSM-server-v0.8-localtest** (asset 644733387): announce/ticket/pool-size -> 127.0.0.1 (our
  masterlist); aka.cfx.re -> route /a. Server appears on own website + client list.
- Owner login: username Cravenz; set password once: `NSM-Masterlist.exe -owner-pass <pw>`.
- Sign-in (client): still Discord for now — root cause known (server-driven signin button URL,
  discord.dll RPC client_id 1560111337923805305); fix = serve auth buttons from our stack (NEXT).
- P0 UNCHANGED: server boot assert Registry.h:164 — still waiting on user's newest crash dump.

## 2026-10-15 (night 2) — P0 SERVER ASSERT SOLVED (fix building) + user redirect to client close
- User clarified symptom is CLIENT: NSM.exe -> launcher opens -> closes -> never shows server list.
  User insists the Steam-title error "been there since the start, not the problem".
- PROVEN ROOT CAUSE of server boot assert (Registry.h:164, every server since v0.5):
  our NSM heartbeat patch in GameServer.cpp forced `if (true)` around code calling
  GetComponent<ServerLicensingComponent>() — that class is ONLY instantiated by closed
  svadhesive.dll (not shipped, not buildable). First heartbeat ~1-2s after boot -> empty
  per-object registry -> assert -> server closes. Same class of bug as v0.7.3 sticky removal.
- FIX (commit 3562e83 on axiomfx-complete-rebrand, pushed; CI run 38795556491 building):
  GameServer.cpp: attach empty `new ServerLicensingComponent("", "", "")` right after
  OnAttached(instance) (class is OPEN + trivial; own masterlist needs no listing token),
  AND kDefaultServerList -> http://127.0.0.1/api/serverlist/ingress for localtest
  (was VPS IP — even a working server would have heartbeat to a dead VPS => empty list).
  v0.8.1 package = v0.8 zip + rebuilt citizen-server-impl.dll (pending build).
- Evidence gathered: stock FXServer build 35245 (Aug-2026-era, win32) downloaded to
  /tmp/stock/pkg (volatile): svadhesive.dll present there (720992 B, registers
  ServerLicensingComponent + ClientComplianceComponent; build path cfx-fivem-3). Stock
  components.json = 29 entries (we ship 25; missing fxdk/devtools/gui/svadhesive — none
  required by any open code; grep-verified; NOT adding svadhesive = no Cfx licensing).
- ServerNucleusMock.cpp cfx-re/api/register flow: guarded by sv_licenseKeyToken (unset) — inert.
- CI note: main branch (5afdec1) is NOT our line; our line = axiomfx-complete-rebrand
  (28ea7a3 -> 3562e83). Dispatched p2-build product=fxserver ref=axiomfx-complete-rebrand.
  Wrongly dispatched run on main (38795478585) cancelled.
- NEXT: when CI completes -> download artifact -> swap citizen-server-impl.dll into server
  package -> v0.8.1 zip -> upload release 412737383. CLIENT close still needs: user answers
  (version in use, RGL-Legacy status, exact visible behavior) + fresh install-folder log.

## 2026-10-15 (night 3) — localhost endpoint audit; client close still unproven
- Inspected the v0.7.4 client UI bundle: `BASE_URL` is `http://127.0.0.1/api/servers`, then it requests `/streamRedir/` and `/single/`. These are API routes, not browser pages; matching handlers exist in `masterlist.go`. `/runtime/counts.json` is also implemented.
- `website.go:buildMux` registers every prefix in `proxyRoutes`, including `/l/` -> `https://lambda.fivem.net`, `/f/` -> `https://forum.cfx.re`, and `/c/`, `/r/` game/cache routes. These are backend proxy routes, not missing website pages. `/updates/` intentionally returns 404 in local mode to keep the installed build.
- User confirms the ROSLauncher child log has only one line (`hello from ... FiveM_ROSLauncher ros:launcher`), with no later entries. The parent log shows the launcher child was created; this proves startup, not why it exits.
- Source check: `code/components/sticky/src/LaunchIntercept.cpp` starts `GameProcess.exe`, waits for it, then terminates its master process with exit code 0. That can explain the clean-looking close if the child exits, but does not identify why the child exits. Do not blame the `/ros/validate` 403 without more evidence.
- Correction: earlier claim that `/l/api/validate/entitlement` was a missing website page was wrong; `/l/` is already proxied. A draft unconditional-valid response was never integrated, shipped, or uploaded; removed. Canonical `NSM-Masterlist-v1.1.exe` remains untouched.

## 2026-10-15 (night 4) — client child-exit diagnostics in CI
- User confirmed the `FiveM_ROSLauncher` log has only its startup line; no later error/details. No further log is available from that run.
- Added source-only diagnostics to `code/components/sticky/src/LaunchIntercept.cpp`: trace master/debug state, `CreateProcessW` success/failure + Win32 error, `ResumeThread` result, wait result, and child exit code. No entitlement behavior or launch decision changed; no 127.0.0.1 route changes.
- Reviewable commit `904bb01b4deb546783651d77042de3f19b151d54` pushed to `axiomfx-complete-rebrand`.
- Server CI run `38795556491` completed successfully on `3562e833`; rebuilt DLL packaged with the existing v0.8 localtest files, localhost URL rewrites reapplied, CRC/static checks passed, and a new GitHub release asset uploaded: `NSM-server-v0.8.1-localtest.zip` (68,976,189 bytes). Runtime boot/list verification is still pending.
- Client CI run `38801965172` (commit `904bb01b`) is still compiling. Its diagnostic package is configured to upload as a uniquely named GitHub release asset after build/package checks; it will not replace v0.7.4. It is diagnostic, not a client fix.
- User asked for GitHub release files rather than workspace outputs. No client package uploaded yet. Do not claim client boot is fixed until runtime verification.
