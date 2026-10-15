# NSM Client Replacement — Implementation Plan & Alt-Dependency Evaluation

Date: 2026-10-13 · Status: **plan + assessment (P0) complete; no code written yet — builds
require a Windows machine (MSVC), which this sandbox is not.**

Target UX (user spec): `NSM.exe → platform/game validation → NSM server browser → connect →
GTA V multiplayer → disconnect → NSM server browser`, one cohesive window, no WebView2,
no Chrome/Edge main interface, no SetParent-reparenting as the architectural foundation.

## 1. What NSM uses from the alt runtime today (closed binaries)

| Component | Origin | Role | Replaceable from fivem-source? |
|---|---|---|---|
| `altv.exe` (gtamp client 16.3.7) | closed, runtime-patched | client launcher: boot, inject GTA, connect | LGPL launcher spine could own boot+window; **multiplayer cannot** |
| `altv-client.dll` / injected client | closed | actual multiplayer client in GTA V | **No** — equivalent = Take-Two-tier components |
| `libce2.dll`, mp1–mp7 packs | closed/encrypted | client runtime data | n/a |
| `gtamp-server.exe` (alt server core) | closed | multiplayer server | **Yes legally** (citizen-server-* is LGPL) but = moving the whole server to fxserver |
| NSM `proxy/`, `discord_rpc.dll` wrapper | ours | traffic proxy, embed/presence/log tailing | ours — keep |
| NSM masterlist, server browser UI, packs pipeline | ours | list + install flow | ours — keep (spec: keep identity) |

## 2. What the alt runtime cannot deliver for the target UX

1. One window from boot — altv.exe always creates its own launcher window, then GTA's
   window (two windows; we currently hide the first and SetParent the second).
2. A pre-connect server browser inside the game window — alt in-game CEF is
   resource-driven (needs an active server connection); no main-menu UI hook.
3. FiveM lifecycle (in-game menu → connect → loading → play → back to menu) — alt
   returns to desktop on disconnect.

## 3. Paths considered

**Path A — full FiveM-derived NSM client from this source: BLOCKED (licensing).**
The GTA V multiplayer core (gta-core-five, gta-net-five, gta-streaming-five, rage-*,
nui-*, net-*) is Take-Two proprietary under the Creator Platform terms. Building NSM's
client on it is not a licensed use. Clean-room reimplementation of that layer is a
multi-year project and is not proposed.

**Path B — hybrid: LGPL launcher spine (NSM.exe) + existing alt runtime for multiplayer.**
NSM.exe is built from the LGPL launcher (rebranded MAIN personality): it owns the
game-host subprocess that loads GTA V **in-process** → one window from boot, by
architecture, exactly like FiveM. Multiplayer continues to come from the working alt
runtime: the question becomes whether the alt client's injection sequence (patches →
DLL injection → entrypoint, currently driven by altv.exe) can be driven from our loader.
The alt binaries are closed but our project already wraps/proxies them extensively.
Honest unknowns: the alt client's launch contract with altv.exe is undocumented; the
pre-connect browser inside the game window still needs a UI channel that is not in the
LGPL tier (candidate: our own overlay in the loader's host window pre-game — design
needed; candidate 2: accept the browser in the loader window that the game then fills —
same HWND, zero reparenting).

**Path C — current architecture (packfix5 + SetParent embed): REJECTED by user spec**
(no SetParent foundation, no WebView2). Kept as the working fallback that ships today;
the game embed already works on the real machine.

## 4. Phased plan (each phase gated; no success claims without verification)

- **P0 — done (this document set):** inspection, architecture map, licensing assessment.
- **P1 — restore licensing compliance in the mirror** (additive commit: reinstate
  upstream `LICENSE`, `LICENSES/*.txt`, `THIRD_PARTY_NOTICES.md`; new branch
  `license-restore`). Required before any reuse. Needs owner approval (it is the
  user's repo) — prepared, not pushed.
- **P2 — prove the toolchain on a Windows machine** (owner machine, legit GTA V):
  restore `ext/cef`+`ext/cfx-ui` submodules, `git submodule update --init`,
  `fxd get-chrome`, `prebuild`, `fxd gen -game server` **and** `-game five`, build stock
  FXServer + stock FiveM unmodified. Deliverable: build logs. **Cannot be done in this
  sandbox (Linux, no MSVC).** Everything after this point depends on P2 passing.
- **P3 — LGPL-spine prototype: "NSM.exe" = rebranded MAIN + GAME personality**,
  boots GTA V in-process into one window (no multiplayer yet). Acceptance: one window
  from launch through GTA main menu on the real machine; source published per LGPL.
- **P4 — multiplayer integration spike:** drive the alt client's injection from the
  loader (time-boxed reverse-engineering spike against the closed alt binaries we
  already ship); fallback documented if the contract proves unusable. Acceptance:
  connect → gameplay in the same window, verified on the real machine.
- **P5 — NSM integration:** platform/game validation at boot (our existing preflight),
  our masterlist browser in the loader window, connect flow, disconnect → browser.
  Acceptance: full user-spec flow end-to-end on real Windows + legit GTA V; rig E2E
  updated where mockable; masterlist/services never auto-started by NSM.

## 5. Required runtime replacement (if Path B proceeds)

- **Replaced:** altv.exe's role as process/window owner (LGPL launcher spine takes over).
- **Kept:** alt injected client + gtamp-server (multiplayer), NSM masterlist/UI/packs.
- **Retired:** NSM's SetParent embed host window, hidden-client plumbing (packfix5 UI
  streaming remains as interim UX on Path C builds).

## 6. Blockers / unsupported (current, honest list)

1. **No Windows/MSVC build capability in this sandbox** — P2+ all run on the owner machine.
2. **Take-Two tier of fivem-source is unusable** for NSM (licensing) — full client
   replacement is off the table; Path B hybrid is the only lawful route to the target UX.
3. **Mirror defects:** license texts stripped (P1), `ext/cef` + `ext/cfx-ui` missing,
   snapshot slightly stale (no build 3889).
4. **Closed alt binaries** — Path B P4 depends on an undocumented injection contract; may fail.
5. **GTA V update pinning** — the LGPL loader carries game-build tables that age with
   GTA V updates (upstream keeps them current; a fork must track upstream).
6. Pre-connect in-game browser (exact FiveM look) is not in the LGPL tier — Path B
   approximates it in the loader's own window (same HWND the game then fills).
