
## 2026-10-14 23:30Z — masterlist rebrand (commits 9179aec + 4b33199)

Scope closed. Findings: client browser list = worker fetch of
`https://frontend.cfx-services.net/api/servers/streamRedir/` (4-byte LE
length-prefixed protobuf `master.Server` frames; schema extracted from the
worker bundle: EndPoint=1, Data=2; ServerData svMaxclients=1 clients=2
protocol=3 hostname=4 gametype=5 mapname=6 resources=8 server=9 players=10
iconVersion=11 vars=12(map entry k=1,v=2) enhancedHostSupport=16
upvotePower=17 connectEndPoints=18 burstPower=19). Browser filter =
`init(["gta5"])` on Data.vars.gamename. Single server JSON at
`/api/servers/single/<ep>`. Heartbeat only sent when sv_licenseKeyToken
non-empty (blank key = no heartbeat at all) → gate removed. Connect tickets
gated on `sv_lan` (default FALSE): blank ticket or missing pubkey → error
drop. → **NSM servers must set `sv_lan "true"`** for ticket-free direct
connect. Pool limits fetch failure is graceful (0=unlimited).

Commits (a1-rebrand tip now 4b331993803c):
- 9179aec9f6a3 — CnlEndpointOverride.h (CNL→VPS), GameServer.cpp (ingress→VPS
  + unconditional heartbeat), InitConnectMethod.cpp + PoolSizesState.cpp
  (pool limits→VPS), ext/ui-build/build.cmd + patch_ui_urls.ps1 (URL rewrites
  inside prebuilt UI bundle: frontend.cfx-services/lambda/servers-frontend/
  gss/static-counts → http://194.104.146.133), tools/masterlist/* (service).
- 4b331993803c — patch_ui_urls.ps1 UTF-8 no-BOM (cosmetic; in-flight builds
  use BOM version — harmless for ES modules).

Simulation against shipped ui.zip: exactly 2 files patched (index-*.js +
WorkerSource.worker-*.js), zero URL leftovers, no other files affected.

Masterlist service (tools/masterlist + /home/user/nsm/masterlist/, zip:
nsm-masterlist-vps.zip): Python stdlib, port 80; GET streamRedir (protobuf
stream), GET single, POST ingress (TTL 5 min, forces vars.gamename=gta5),
GET pubkey (PKCS#1 RSA 2048, key committed), identities/featured/notices/
tweets/pool-limits/counts stubs. Local E2E test passed (heartbeat→stream
decoded by hand, all endpoints 200/404 as designed).

Builds dispatched 23:24Z on 9179aec: fxserver run 38653883116, fivem run
38653884943. Server v6 / client v3 candidates when green.

Server config needed on user side:
  sv_lan "true"          (ticket-free direct connect)
  (sv_master1 already defaults to VPS ingress)
VPS: deploy nsm-masterlist-vps.zip (systemd, port 80, TCP 80 open).

## 2026-10-15 01:25Z — server v6 + client v3 SHIPPED (masterlist rebrand live)

Builds on 9179aec: fxserver run 38653883116 GREEN ~00:34Z (artifact
11938598395), fivem run 38653884943 GREEN 01:16Z (artifact 11939928452).
Extra commit a874d21ef4dc (data/server/components.json → proven v5 25-entry
list; repo copy had drifted: svadhesive + rdr3sv + no devtools — svadhesive
would fatal; data-only, no rebuild needed).

NSM-Server v0.6 (asset 642206197, 68.7 MB, replaced v5 640716182):
- v5 package base + new binaries overlaid (no dbg/CitiTest/lib/exp)
- citizen-server-impl.dll: 3× "194.104.146.133" (ingress + CNL pubkey +
  pool limits) verified
- server.cfg NOW INCLUDES sv_lan "true" (ticket-free direct connect!)
- README updated (masterlist auto-heartbeat note)

NSM-Client v0.3 (asset 642258943, 229 MB, replaced v2 641942623):
- artifact caches/fivereborn + 10 CRT DLLs @14.44 in bin/ + components.json
  (63 entries, sticky, no adhesive — repo tip copy)
- ui.zip patched IN-BUILD by build.cmd/patch_ui_urls.ps1: index JS + worker
  JS now http://194.104.146.133/api/servers, streamRedir + single + icons;
  zero leftover cfx URLs; ui-big clean (media + pdf/prime workers only)
- CitizenFX.exe: 6× VPS URL (CnlEndpointOverride.h took effect)
- 413 files = exact parity with v2 client

Masterlist wire format (verified end-to-end locally + simulated patch):
GET /api/servers/streamRedir/ → [u32 LE len][protobuf master.Server
{1:EndPoint str, 2:ServerData}] frames; ServerData fields: 1 svMaxclients,
2 clients, 3 protocol, 4 hostname, 5 gametype, 6 mapname, 8 resources rep,
9 server str, 10 players rep msg, 11 iconVersion, 12 vars map
(entry{1:key,2:val}), 16 enhancedHostSupport, 17 upvotePower,
18 connectEndPoints rep, 19 burstPower. Browser filter: Data.vars.gamename
must be "gta5" (init(["gta5"])). /api/servers/single/<ep> → JSON
{EndPoint, Data{camelCase}}. Heartbeat POST /api/serverlist/ingress
{port, listingToken, ipOverride, private, fallbackData{players, info,
dynamic}} → 200 {} = ok (lastError empty).

REMAINING FOR USER: deploy masterlist on VPS (nsm-masterlist-vps.zip in
/home/user/nsm/masterlist/), open TCP 80, download+deploy server v6 +
client v3, acceptance test (two players, direct connect IP:30120).

## 2026-10-15 01:31Z — masterlist as standalone exe/binaries

Go rewrite (tools/masterlist/masterlist.go, commit cc21712e690b, stdlib
only). Built with go1.27.2: NSM-Masterlist.exe (Win x64, 6.8MB PE32+),
nsm-masterlist-linux-amd64 (6.6MB static), nsm-masterlist-linux-arm64
(6.1MB). Linux-amd64 passed the identical E2E test suite as the Python
version (heartbeat -> single JSON -> protobuf stream hand-decoded -> all
stubs). systemd unit now runs the binary. Kit nsm-masterlist-vps.zip
(8.1MB, 9 files) in /home/user/nsm/masterlist/ AND release asset
642278897 (wget-able from the VPS). Python masterlist.py kept as
fallback. NOTE: Go toolchain installed to /usr/local/go (volatile);
source is in the repo + workspace, rebuild = GOOS/GOARCH go build.

## 2026-10-15 02:45Z — Phase 1 rebrand source commit a6f780f3d1b8 (BUILDS BLOCKED ON BILLING)

All Phase 1 source work committed to a1-rebrand (tree of 14 entries on top
of cc21712e690b):
- code/server/launcher/src/Server.cpp: monitor gate inverted (server:main
  default; monitor ONLY with -txadmin/-monitor), auto `"+exec" "server.cfg"`
  when absent, console title "NSM Server", version/help lines NSM Community
  + discord.gg/UXj5QfCX88, Windows.h include.
- code/server/launcher/src/Main.cpp: 2x CPU message -> "NSM Server",
  kvm64 link -> hypervisor docs.
- code/components/citizen-server-monitor/src/MonitorInstance.cpp:
  "NSM-Server-" version prefix + ASCII txAdmin banner replaced with
  "NSM Server - AxiomFX (monitor mode)".
- code/components/citizen-server-impl/src/InfoHttpHandler.cpp: 2x
  "NSM-Server-" GIT_DESCRIPTION (info.json + version convar; /version
  endpoint reuses versionVar).
- code/components/discord/src/DiscordPresence.cpp: app 1560111337923805305,
  asset nsm_large (committed earlier this session, included here).
- code/server/launcher/server.rc: NSM Community / NSM Server (AxiomFX) /
  NSM / (C) 2026 NSM Community / nsm-server.exe / AxiomFX.
- code/server/launcher/server.manifest: identity NSMServer.
- ext/ui-build/build.cmd: calls patch_ui_bundle.ps1 (2x); patch_ui_urls.ps1
  DELETED; patch_ui_bundle.ps1 added (24-rule full bundle rebrand).
- icons: server.ico + client launcher fivem.ico/fivem_sp.ico/fivem_sdk.ico
  all = NSM multi-size ico (56,242 B) — exe/taskbar/splash logo covered.
All patches byte-verified by diff against pre-commit raws; Server.cpp
brace-balance double-checked (an earlier bad insert was caught + redone).

Masterlist: /v1/public/notices/fivem -> {"notices":[]} was ALREADY in
masterlist.go (Go rewrite) — nothing to add.

Dispatched p2-build.yml (383704415) fxserver+fivem at 02:41Z on a6f780f:
runs 38672303672 + 38672305688 BOTH FAILED INSTANTLY —
"The job was not started because recent account payments have failed or
your spending limit needs to be increased. Please check the 'Billing &
plans' section in your settings."
=> USER ACTION REQUIRED: GitHub Settings -> Billing & plans: fix payment
or raise Actions spending limit. Then run
/home/user/nsm/branding/dispatch_phase1.sh (re-dispatches both), wait for
green (server ~70 min, client ~110 min), then
/home/user/nsm/branding/package_phase1.py --server-run ID --client-run ID --upload
(builds server v0.7 + client v0.4 zips locally, full asserts incl.
414-file client parity +steam_appid.txt 218, then swaps release assets
on release 412737383).

Discord deliverables (user side):
- App icon: /home/user/nsm/branding/nsm-icon-1024.png -> Discord Dev
  Portal -> app 1560111337923805305 -> General Information -> App Icon.
- Rich presence art: same portal -> Rich Presence -> Art Assets ->
  upload nsm-icon-1024.png (or a 512+) named "nsm_large".

## 2026-10-15 03:45Z — masterlist v2 + feed features (commit 5acb9ff3c348)

Billing fixed by user ($100 spending limit; ~$2.91 per build pair). Builds
re-dispatched 02:57Z on a6f780f: fxserver run 38673689559 + fivem run
38673691537. Watcher (start_process) auto-packages v0.7/v0.4 + uploads
when both green.

masterlist v2 (E2E verified locally: heartbeat/upvotes/fakeplayers/feed/
auth/protobuf stream decode incl. varint tags; 9000 cap; state persist):
- /admin/* Bearer OWNER_TOKEN: upvotes {endpoints,set|add} (multi-server),
  fakeplayers {endpoints,count 0..9000} (deterministic names, e.g.
  ElectricCobra/TurboDragon; overrides clients if above real; fills
  protobuf field 10 players + JSON players), feed post/import/delete,
  GET state. state.json persists across restarts.
- /v1/public/tweets serves Twitter-format array (rawTweetToActivityDataItem
  compatible: id_str/text/created_at/user.name/user.screen_name/entities/
  extended_entities.media). counts.json includes fake players.
- discord_feed_poller.py (stdlib, REST polling /channels/:id/messages,
  45s): mirrors user's #updates channel 1545984006196166736 (text, author,
  avatar, image attachments as tweet media). Needs user-created bot token
  (Message Content Intent + Read History, invite to guild).
- Kit nsm-masterlist-vps.zip rebuilt (13 files: binaries x3 + go + poller
  + 2 systemd units + 2 env examples + README + key + py fallback),
  release asset replaced (new id 642568660, same filename).
- UI feed links: hardcoded x.com/FiveM/status/ template -> scravenz101:
  patch_ui_bundle.ps1 rule added (commit 5acb9ff) AND packaging-time
  patch in package_phase1.py (in-flight build a6f780f bakes x.com/NSM;
  packaging fixes it to scravenz101 + asserts).

DECLINED (told user): making FiveM-bought ESCROW-protected scripts run on
NSM (defeats Cfx script DRM; their backend also rejects fork builds).
Non-escrow Tebex scripts work anywhere incl. NSM already. NSM keymaster =
Phase 2 with website (free NSM keys + own script marketplace protection).
FiveM upvote purchases cannot be read from outside fivem.net; NSM upvote
shop = Phase 2 website at $5.99/upvote (FiveM parity ~$6).
X API: no free reads anymore (pay-per-use since Feb 2026) - Discord
channel is the feed source; X can be added later via /admin/feed/import.

## 2026-10-15 03:52Z — workspace tidied; watcher restart note

Cleanup: /home/user now 61MB (was ~150MB + 74MB go cache). Kept at top
level: CI-BUILD-LOG.md, branding/ (active patchers+packaging), masterlist/
(active service). Historical docs/src/mocks-src/logs/binaries/scripts
moved to nsm/archive/ with MANIFEST.md. Deleted: go cache, testpacks/12MB,
tree.json/2.2MB, compiled mocks, stray root fetches, obsolete
masterlist/patch_ui_urls.ps1 + pub.b64.

NOTE: sandbox restore between user messages killed the build watcher and
wiped /var/tmp/phase1-pack. Watcher restarted 03:52Z (builds unaffected -
they run on GitHub). If found dead again after both runs green, run
directly: python3 /home/user/nsm/branding/package_phase1.py
--server-run 38673689559 --client-run 38673691537 --upload
(script re-downloads any missing base zips/artifacts itself).

## 2026-10-15 04:41Z — server build FAILED (monitor banner), fixed, re-dispatched

Run 38673689559 (a6f780f) failed: MonitorInstance.cpp(172) C2001 newline in
constant — my banner re.sub replacement processed \n escapes in the template,
turning the C++ "\n\n" escapes into REAL newlines inside the trace() string
(string split over lines 172/173/174). Only error in the log (verified no
other file failed). Fix commit 4951fff391cd (single-line banner with proper
backslash-n escapes, hex-verified 5c 6e 5c 6e). Re-dispatched fxserver:
run 38682705476 on 4951fff (04:40Z, ~70 min, ~$1.12). Client run 38673691537
(a6f780f) unaffected — monitor is a server component — still in_progress,
ETA ~04:50Z. Watcher restarted with SRUN=38682705476 (also died with a
sandbox restore; /var/tmp wiped again — packaging script re-downloads
whatever it needs).
LESSON: re.sub replacement templates process \n escapes — use \\\\n (4
backslashes) in bytes literals for C++ escapes, or str.replace.

## 2026-10-15 04:55Z — client build FAILED (patcher PS syntax), fixed + re-dispatched

Run 38673691537 (a6f780f) failed at the UI patch step 110 min in:
patch_ui_bundle.ps1:39 "Missing expression after ','" — trailing comma after
the LAST $replacements element is a PS parse error. Root cause: the patcher
had only ever been Python-simulated, never parsed by real PowerShell.
NOTE: builds check out the DISPATCH-TIME sha (log confirmed a6f780f line
numbers), so the in-flight patcher fix only helps NEW dispatches.

Fixes on commit 9747097cb04a:
- trailing comma removed; pwsh 7.4 downloaded to /var/tmp/pwsh and the
  patcher now VERIFIED FOR REAL: Parser::ParseFile = 0 errors + full
  runtime patch of stock ui.zip (4 files rewritten, 0 FiveM/CitizenFX/
  Cfx.re in JS, 3 wordmarks, N-mark, 13 VPS URLs, blue 16x in CSS,
  x.com/scravenz101 links, zip integrity OK)
- Test-Path guard (missing zip used to silently create an empty one)
package_phase1.py asserts corrected: blue accent counted in CSS (not JS),
x.com packaging patch is now informational (in-build rule may handle it).

Also this session: masterlist moved to its own repo
platinum-cfx/NSM-masterlist (private): source + release v2.0.0 with
nsm-masterlist-vps.zip (asset 642700888). tools/masterlist/ removed from
NSM-FIVEM (commit 998e934), duplicate kit asset deleted from the
NSM-FIVEM release - canonical masterlist home = the new repo.

RUNNING: fxserver 38682705476 (4951fff, ~05:50Z) + fivem 38683776474
(9747097, ~06:45Z). Watcher restarted with both new IDs.

## 2026-10-15 07:0xZ — PHASE 1 v0.7 + v0.4 SHIPPED ✅

Runs: fxserver 38682705476 success (4951fff), fivem 38683776474 success
(9747097). Packaging issues found & fixed while shipping (no rebuilds needed):
- artifacts API wants Accept: application/vnd.github+json (octet-stream → 415),
  then 302 → signed Azure URL: follow redirect MANUALLY with clean headers
- fxserver artifact nests under bin/server/windows/release → overlay must map
  that subtree onto NSM-Server/ root (was creating nested server/windows/...)
- discord.dll carries a Discord-SDK OAuth AUTHORIZE template (guilds.join +
  client_id 1473308775258525930 + redirect https://cfx.re). Same-length byte
  swap at packaging: client_id → 1560111337923805305 (both 19 bytes!), cfx.re
  redirect (14B) → nsm.invalid. Active RPC id was already ours from the build.
- watcher logic bug: 'case *completed*' fired when EITHER run completed —
  rewritten to require both; sandbox also dozes between turns (background
  polls only advance during active tool calls) → prefer foreground packaging.

Both zips fully asserted (branding strings, icons, VPS URLs, sv_lan, steam
appid 218, ui.zip zero-brand + wordmarks + blue CSS + scravenz101 links,
discord old id gone) and uploaded:
- NSM-server-v0.7.zip 68,695,952 B (replaces 642206197)
- NSM-client-v0.4-preview.zip 230,415,253 B (replaces 642258943)
Total CI spend ≈ $7.61 (4 server/client runs + retry) of $100.

## 2026-10-15 07:35Z — acceptance round 1: server crash fixed + client v0.5 in flight

USER REPORTED (v0.7/v0.4):
1. Server crash at startup: assert(instance.GetRef()) Registry line 164.
   ROOT CAUSE: v0.7 was the first server build ever RUN with the a6f780f
   launcher change (default citizen:server:main). ServerMain is implemented
   by the monitor component; more importantly the shipped components.json
   was a hand-made 25-entry list (a874d21) that ADDED citizen:devtools
   (upstream never loads it in the server) and DROPP rdr3sv/svadhesive.
   FIX: restored upstream 26-entry list (commit e42715309c6) + packaging
   overlays it from nsm/branding/components-server.json (artifact does not
   carry components.json at all - it comes from the base zip). v0.7
   re-packaged + re-uploaded (same asset name). NO rebuild needed.
2. Server exe icon: verified all 6 embedded icon sizes are byte-identical
   to our NSM ico -> user is seeing Windows icon cache / old extract.
3. Client splash still FiveM-green: backdrop.png (green world map) +
   UpdaterUI theme_ProgressFg 0x66AD43 were never rebranded.
4. DLL properties still say CitizenFX: shared template code/tools/gen_rc.py.
5. CitizenFX.exe should be NSM.exe: 1 ASCII 'CitizenFX.exe' ref per file
   (exe + 20 SubProcess blobs, no UTF-16) -> same-length patch at packaging.
6. No Steam presence: launcher loads steam_api64.dll but never inits;
   legitimacy.dll only inits via the ROS flow we don't use.

CLIENT FIXES commit 93a9481aec2c (build run 38699472048, ~09:25Z):
- UpdaterUI.cpp 0x66AD43 -> 0x2F7BFF (blue progress)
- backdrop.png recolored green->blue map (same geometry)
- Main.cpp: explicit SteamAPI_Init after steam_api64 load (appid 218 =
  "Source SDK Base 2007" presence like FiveM)
- gen_rc.py: CompanyName NSM Community / ProductName AxiomFX /
  FileDescription for NSM/AxiomFX/NSM Server (all DLL properties)
Packaging v0.5: renames CitizenFX.exe -> NSM.exe + patches all binary
refs same-length; asserts zero stale refs. discord.dll oauth patch and
components.json overlay retained. Steam mutex/log names stay CitizenFX
(internals, harmless).
Spend to date ~$9.40 (incl. client rebuild $1.79).

## 2026-10-15 14:15Z — client v0.5 SHIPPED ✅

Run 38699472048 (93a9481) success. Packaged NSM-client-v0.5-preview.zip
(233,077,272 B): NSM.exe rename (20 binary refs repointed, zero stale),
blue splash assets, gen_rc NSM version info on all DLLs, SteamAPI init,
discord oauth rebrand, ui.zip fully NSM. v0.4 asset deleted; release now
exactly: NSM-client-v0.5-preview.zip (644085006) + NSM-server-v0.7.zip
(643054928). Known wart: duplicate steam_appid.txt entry inside the zip
(base already carried one; extractors overwrite - harmless). Fix in next
packaging pass: skip writing if present in base.

## 2026-10-15 14:4xZ — client v0.6: boot loading screen + FiveM-named files

User still saw the FiveM logo: (a) on NSM.exe file icon -> VERIFIED the exe's
group-1 icon (Explorer file icon + splash window class icon, LoadIcon ID 1)
is our NSM art in all 6 sizes -> Windows icon cache on the user side;
(b) during "updating game storage and launching" -> the boot loading screen
nui://game/ui/loadscreen/index.html served from citizen/ui.zip loadscreen/
with background ea097d53311d8e118a31.jpg (3840x2160, stock FiveM art with
the wordmark baked in) in citizen/ui-big.zip - never touched by the patcher.

v0.6 (packaging-only, no rebuild): NSM boot screen (navy gradient + grid +
N-mark + wordmark + tagline) swapped into ui-big.zip loadscreen entry;
FiveM.com -> NSM.com and FiveM_Diag.exe -> NSM_Diag.exe (unreferenced by
name in any binary; only locale .po text mentions them - Phase 2 polish).
v0.5 asset deleted. Locale texts + embedded manifest assemblyIdentity
name="FiveM" remain (internal/invisible).

## 2026-10-15 15:40Z — server fix verified live + unambiguous re-post (-fixed)

User read "last updated 7 hours ago" on NSM-server-v0.7.zip as "no fix posted".
API check: live asset 643054928 (updated 07:24:46Z) digest
sha256:12f6ed98bf4a79086c05d80ab9f81f9972c6a499ca4dbb485dbe19519d48ac61 ==
local verified-fixed copy (components.json: rdr3sv present, svadhesive
present, citizen:devtools absent) — same-name replacement WAS the fix; user's
Oct-14 crash dump predates it. Re-posted identical bytes as
NSM-server-v0.7-fixed.zip (same release 412737383) so old-vs-new local copies
can't be confused. Both names = identical fixed build. Client v0.7 run
38754548380 still in_progress at 15:40Z.

## 2026-10-15 15:43Z — server v0.7.1: svadhesive removed (user hit "error code 2")

USER REPORT (running NSM-server-v0.7-fixed.zip): "could not load component
manifest svadhesive.dll - windows error code 2" — the v0.7 assert fix WORKED
(loader got past the old crash), boot now stops on a missing file.
DIAGNOSIS: shipped 26-entry components.json lists "svadhesive", but
svadhesive.dll is not in the zip — and "adhesive" appears in ZERO paths of the
15,442-entry a1-rebrand tree (cfx-internal updater glue, not buildable from
our source). Cross-check: the other 25 entries all have their DLLs present.
FIX (packaging-only, no rebuild): removed "svadhesive" from
nsm/branding/components-server.json (25 entries; monitor + rdr3sv/fivesv
state stay, devtools stays out). Surgical zip: v0.7 zip with only
NSM-Server/components.json replaced; all other entries CRC-identical.
SHIPPED: NSM-server-v0.7.1.zip (release 412737383), asset
644338212, sha256 0c29a0298a5cc11afb67a886f6a81a14502f44819b08aa4c1da0d71064515fab.
package_phase1.py hardened: assert 25 entries + per-component DLL-presence
check; OLD_SERVER_ASSET repointed to v0.7.1. Evidence that no listed component
hard-depends on svadhesive at load time: the earlier broken build ran the same
list minus svadhesive and loaded all 30+ DLLs deep into init. If the user now
hits the Registry assert again, next suspect = a6f780f launcher change; need a
FRESH crash dump to confirm.


## 2026-10-15 (evening) — rebrand waves + client v0.7
- Mission Phase 6 sweep: 13,553 files, 6,394 matches classified (branding/inventory/).
- Waves 1-4 executed on axiomfx-complete-rebrand @ **28ea7a3** (119 files, 183+/182-): user-visible strings,
  locale msgstr (42 lines), CitizenFX.log→NSM.log, fivem.cfg→nsm.cfg (CONFIG_NAME, self-consistent, 0 stale refs),
  fivem*.ico→nsm*.ico + rc refs, manifest identity, MiniDump NSM.exe+ hash case (legacy kept), 20 cosmetic URLs→Discord.
  Verified: KEEP buckets byte-identical (scripting-api 930 / runtime-id 470 / internal-symbol 712 / vendor 189 / legal 7);
  0 msgid keys, 0 functional URLs, 0 Citizen./citizen:/CitizenFX:: lines touched. Review pass caught + fixed 3 regressions
  (UI-bundle find-sides, untruthful CitizenFX.*.Natives.dll comments, log-comment vs real rename). Intentionally kept:
  content.cfx.re + runtime.fivem.net (functional until mirror), Symbolication build-path check, CI identifiers.
- Dispatched wave builds: #38 fivem + #39 fxserver on axiomfx-complete-rebrand (both 204).
- Client v0.7 packaged from run 38754548380 (d6f7212, green): packager upgraded (rename-translation map so fresh
  CitizenFX.exe/FiveM.com/FiveM_Diag.exe land as NSM.exe/NSM.com/NSM_Diag.exe — assert caught a stale-launcher bug;
  zip dedupe). All asserts green: 412 fresh files, 0 CitizenFX.exe refs, discord oauth NSM, ui.zip clean, loadscreen NSM.
- Asset table fixed after a mis-named upload: **NSM-client-v0.7.zip = 644549113 (233,710,030 B)**;
  v0.6-preview restored pristine = 644549632 (233,701,399 B); OLD_CLIENT_ASSET updated.
- Baseline note: main (5afdec1) is a PR#5 merge of an EARLIER a1-rebrand state (Oct-14) — not pure stock;
  the pure-stock reference is the original import (platinum-cfx/fivem-source @ 06215ba).
- Server crash (Registry.h:164 GetComponent) STILL AWAITING user crash dump — P0.

## 2026-10-15 (night) — deep-dive: task manager / logo / Steam / localhost
- Forensics on shipped v0.7: version resources ALREADY NSM (FileDescription 'NSM', 'NSM Game subprocess');
  runtime subprocess names NSM_* (CfxSubProcess.h:54). All embedded package art blue/NSM (icons 128/256 blue,
  1250x1250 splash blue, loadscreen 3840x2160 dark blue). User's Oct-13 screenshot: 93% black, 0% green.
  => 'FiveM everywhere in task manager' + Steam 'playing fivem' consistent with OLD install/old shortcut launching.
- Green boot logo: NOT in any shipped file (proven). Source = GTA game cache update.rpf from content.cfx.re
  (mirrors/patches_fivem/<build>/update.rpf + hdiff chains in glue.dll + game bins). Fix = Phase 2 own mirror.
- DIRECT BINARY PATCH (no rebuild): NSM-client-v0.7.1-localtest.zip — all length-preserving:
  * manifests name="FiveM" -> "NSM" (20 PEs)
  * updater URLs http://194.104.146.133/... -> http://127.0.0.1/... (6 in NSM.exe + pool-sizes-state.dll) —
    full-string rewrite + null pad; server-list/counts/featured URLs inside ui.zip JS -> 127.0.0.1 (13)
  * subprocess template CitizenFX_SubProcess_%s.bin -> NSM_SubProcess_%s.bin in NSM.exe + 19 bins +
    5 DLLs (nui-core, sticky, fxdk-main, v8node, legitimacy) + own-name .bin/.pdb strings + 19 blobs renamed
  * NSM_Diag.exe version block -> NSM Diagnostics Utility / NSM Community / AxiomFX / NSM_Diag.exe
  * SDK shortcut name -> NSM.SDK; LOCAL-SERVER.ps1 + README-LOCALTEST.txt added
  * VERIFY PASS: 0 FiveM manifests, 0 VPS URLs (incl. nested zips), 0 CitizenFX_SubProcess refs,
    loadscreen intact, 63 components, steam_appid 218
- Steam display = non-Steam shortcut NAME (old 'FiveM' shortcut shows 'Playing FiveM'); instructions in README.

## 2026-10-15 evening — NSM Local Stack v1 (localhost, one exe)
- Built NSM-Masterlist.exe (Go, 7.9MB): masterlist v2 + accounts (bcrypt, roles owner/admin/staff/user) + embedded NSM website (12 templates, repo CSS recolored #2F7BFF) + pass-through game-cache proxy (12 routes) + updater 404. Live-tested 11/11: register/login/me/heartbeat/servers page/upvote/promote/security-403/all pages/masterlist APIs intact.
- Source pushed to platinum-cfx/NSM-masterlist: masterlist.go+go.mod updated; commit 14b3306110 adds accounts.go, website.go, proxy.go, site/* (17 files).
- patch_v072_localtest.py EXECUTED PASS: v0.7 -> v0.7.2-localtest (boot logo XAML green->NSM N-mark blue; 10,444 CDN URLs -> http://127.0.0.1/<route>/; bundled NSM-Masterlist.exe + START-LOCALHOST.bat + README v2; all v0.7.1 patches). Uploaded asset 644732472 (233,543,354 B).
- patch_v08_server_localtest.py EXECUTED PASS: v0.7.1 server -> v0.8-localtest (announce/ticket/pool-size VPS->127.0.0.1; 11 aka.cfx.re->route /a). Uploaded asset 644733387 (68,975,584 B).
- Sign-in root cause found: client sign-in button opens URL from server-driven auth response (LoginRequestResponse.buttons[type=signin].value; window.open in ui.zip JS); Discord flow = discord.dll RPC AUTHORIZE (client_id 1560111337923805305, redirect nsm.invalid). Full fix = serve auth response from our stack (next step, needs locating the launcher's auth-request endpoint).

## 2026-10-15 night — stack v1.1 hotfix (client stuck at "Starting NSM")
- User log: mirror WORKS (socialclub+mtl launcher+GTA5.exe 3258+update.rpf/2.rpf all fetched+cached through it);
  stuck after "Analyzing game data" at "Starting NSM" with lambda validate/discourse 403 + validate/discord 500.
- Root causes: (1) proxy dropped POST bodies on pass-through (validations are POSTs -> empty body upstream);
  (2) sign-in checks should be answered by OUR backend, not proxied to real cfx (which 500s on our app's token).
- v1.1: bodies forwarded (verified with echo upstream: full JSON+Content-Type round-trip); /l/api/validate/discourse+discord
  answered locally 403 {"error":"invalid_token"} (verified: instant LOCAL, no upstream); body logging for /l/* /f/*;
  /updates/ logging. Uploaded NSM-Masterlist-v1.1.exe (asset, 7,963,136 B). Source: NSM-masterlist commit (proxy.go, website.go).

## 2026-10-15 late — client boot hang ROOT-CAUSED (ROS/MTL clearance)
- User log: all 60+ pre-gameload components load fine; game waits forever on "ROS/MTL still hasn't cleared launch";
  /ros/validate (localhost:32891 -> real Rockstar) returns 403 DoesNotExist; retries 2/3, 3/3.
- Verified NOT our build: ROS chain in shipped legitimacy.dll byte-identical (pipes MTLLauncher_Pipe_CFX etc intact);
  steam_appid 218 matches stock; no Rockstar hosts in our route table.
- Same hang hits stock FiveM users (forum.cfx.re thread 5424184, Sep 2026, identical symptoms).
- Root cause: the wait lives in 'sticky' (cfx client anti-cheat, closed/prebuilt; loaded via components.json;
  ComponentLoader.cpp aliases adhesive->sticky). It gates game start on Rockstar's ROS clearance.
- Fix shipped for testing: components-nosticky.zip (asset 644797816) = components.json minus "sticky" (63->62 entries).
  If boot succeeds -> bake into v0.7.3 permanently (our own network does not need cfx anti-cheat).

## 2026-10-15 night — v0.7.3-localtest (boot fix shipped)
- User's manual sticky-removal test crashed: "Unknown component adhesive" (CoreRT.dll ComponentLoader
  fallback adhesive->sticky with sticky gone). Fixed in patcher: CoreRT.dll b'sticky\0' -> b'devcon\0'
  (same 6 bytes; devcon always present) so adhesive requests resolve harmlessly.
- REAL root cause of the original hang (from user's Rockstar Launcher log): their Steam GTA is the
  ENHANCED edition (app 2676230); the pinned Rockstar launcher 1.0.53.576 answers "Unsupported Steam
  title: 2676230" so the MTL launch clearance never fires. sticky was the waiter -> removed.
- NSM-client-v0.7.3-localtest.zip: v0.7.2 patches + sticky removed (components.json 62) + CoreRT
  adhesive->devcon + bundled NSM-Masterlist.exe v1.1. All 19 verify checks PASS. Uploaded to release.

## 2026-10-15 late-night — v0.7.3 WRONG (sticky is the game spawner) -> v0.7.4 shipped
- v0.7.3 (sticky removed) closes instantly after "Starting NSM": Main.cpp game-mode = EarlyMode_Init
  (loads legitimacy+adhesive, PreInitGame them) then RETURNS - sticky.dll's launcher-side PreInitGame is
  what spawns ros:launcher + the GameRuntime subprocess. Without sticky nobody spawns the game.
- CoreRT adhesive->devcon patch also wrong (EarlyMode would load devcon instead of sticky).
- v0.7.4 = v0.7.2 content (sticky intact, no CoreRT patch) + README: requires GTA V LEGACY; Steam-GTA
  users must install Legacy from the Rockstar Games Launcher (account owns gta5 - entitlement true in
  user logs; old pinned MTL 1.0.53.576 cannot launch Steam titles: "Unsupported Steam title: 2676230").
- Next fix path if RGL-Legacy install still fails: our own sticky.dll replacement (open spawner, no ROS wait).

## 2026-10-15 night — client launcher exit diagnostics (build in flight)
- User confirmed the `FiveM_ROSLauncher` child log contains only the initial `hello from ... ros:launcher` line; no later entries exist in that run.
- Inspected the open sticky launcher code: it creates `GameProcess.exe`, waits for it, and then terminates the master process with status 0. This matches a clean-looking exit if the child ends, but does not establish why it ends.
- Added non-behavior-changing `trace()` diagnostics in `code/components/sticky/src/LaunchIntercept.cpp` for master/debug state, CreateProcess error, ResumeThread result, wait result, and child exit code.
- Commit: `904bb01b4deb546783651d77042de3f19b151d54` on `axiomfx-complete-rebrand`.
- Server CI `38795556491` on `3562e833` completed successfully. v0.8.1-localtest package created by swapping the rebuilt `citizen-server-impl.dll` into the existing v0.8 package, reapplying local URL rewrites, and passing CRC/static assertions (local ingress endpoint, `sv_lan true`, no VPS URL/svadhesive). Uploaded unique GitHub release asset `NSM-server-v0.8.1-localtest.zip`, 68,976,189 bytes: https://github.com/platinum-cfx/NSM-FIVEM/releases/download/nsm-v0.2-preview/NSM-server-v0.8.1-localtest.zip. Runtime boot/list verification still pending.
- Client CI `38801965172` on `904bb01b` remains in the Windows build step. The diagnostic package watcher uploads a unique asset after passing checks; it will not replace v0.7.4.
- No client package uploaded yet; do not claim the problem is fixed.
