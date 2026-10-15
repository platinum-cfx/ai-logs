# fivem-source — Repository Architecture Map

Inspected: 2026-10-13 · Repo: `platinum-cfx/fivem-source` @ main `06215ba` (18 commits)
· Identity: **snapshot of `citizenfx/fivem` master** (squashed import; slightly stale —
lacks upstream's `mp2026_01`/build 3889 entry in GameBuilds.h)

## Top level

| Path | Contents |
|---|---|
| `code/` | all C++ source: `client/` (launcher, citicore, shared, common, scripting cores), `components/` (117 components), `tools/` |
| `vendor/` | ~150 submodules (curl, protobuf, v8 12.4, boost split, lua, eastl, bgfx, node, openssl, mumble deps…) |
| `ext/` | natives declarations, sdk, system-resources, typings, ui-build. **Missing vs upstream: `ext/cef`, `ext/cfx-ui`** (the main-menu UI) — not in `.gitmodules` |
| `data/` | per-game-build data files |
| `docs/` | `building.md`, `layout.md` |
| `fxd.cmd` / `fxd.ps1`, `prebuild.cmd` | build drivers (premake5-based) |
| `.gitlab-ci.yml` | CI pipeline |

## Build system (from `docs/building.md`)

Windows **only**: Visual Studio 2022 (C++ + .NET workloads, Win11 SDK 10.0.22000.0),
PowerShell 7, Python ≥3.8, MSYS2, Node+Yarn. Steps: `git submodule update --init` →
`fxd get-chrome` (downloads CEF) → `prebuild` (natives bindings) → `fxd gen -game five|server|rdr3`
→ build the generated VS solution.
**This cannot be built in the Linux/mingw sandbox — no MSVC. All builds need a Windows machine.**

## Client launcher spine — `code/client/launcher/` (the one-window architecture)

- `Main.cpp` — entry point; **personality system** compiled per-target:
  MAIN (`FiveM.exe`, bootstrap/updates), GAME (`CitizenFX_SubProcess_game_*`,
  **loads GTA5.exe in-process**), CHROME (`CitizenFX_SubProcess_chrome`, CEF UI subprocess)
- `CitizenGame.cpp` — maps the game executable via `ExecutableLoader`, hooks
  `GetStartupInfoW` to intercept game entry, applies runtime hooks before the game runs
- `ExecutableLoader.cpp/.h` — PE mapping of GTA5.exe into the host process
- `Bootstrap.cpp`, `GameCache.cpp`, `Updater.cpp`, `UpdaterUI.cpp` — updates, cache, boot splash
- `CrossBuildLaunch.cpp`, `GameSelect.cpp`, `ViabilityChecks.cpp`, `OSChecks.h` — game build
  selection and platform validation

**This is why FiveM is one window:** the game-host subprocess is the process that owns the
game window from the first frame; the launcher stub and UI subprocess never create a
competing top-level window. No SetParent, no embedding.

## Component inventory (117) — grouped by role

- **Game integration (GTA V)**: `gta-core-five`, `gta-game-five`, `gta-streaming-five`,
  `gta-net-five`, `gta-mission-cleanup-five`, `extra-natives-five`, `loading-screens-five`,
  `handling-loader-five`, `rage-allocator/device/graphics/input/nutsnbolts/scripting-five`,
  `scripthookv`, `asi-five`, `pool-sizes-state`
- **Framework ("citizen-*")**: `citizen-game-main/ipc`, `citizen-level-loader-*`,
  `citizen-mod-loader-five`, `citizen-playernames-*`, `citizen-resources-{client,core,gta,metadata-lua}`,
  `citizen-scripting-{core,lua,mono,mono-v2,node,v8*,v8client,v8node}`,
  `citizen-legacy-net-resources`, `citizen-devtools`
- **Server (fxserver)**: `citizen-server-{impl,main,instance,net,monitor,state,state-fivesv,gui,fxdk}`,
  `net`, `net-base`, `net-packet`, `net-tcp-server`, `net-http-server`, `conhost-server`,
  `voip-server-mumble`, `scripting-server`, `vfs-impl-server`
- **UI/CEF**: `nui-core`, `nui-gsclient`, `nui-resources`, `conhost-v2`, `conhost-posh`, `n19ui`
- **Platform/validation**: `legitimacy` (game-ownership checks), `discord`, `http-client`,
  `voip-mumble`, `glue`, `sticky`, devtools/debug components
- **RDR3 / NY (GTA IV) variants** of the above
- `vfs-core`, `font-renderer`, `tool-*`, `scrbind-*`, `debug-*`

## Runtime flow (FiveM client)

```
FiveM.exe (MAIN: update check, boot splash)
  └─ spawns CitizenFX_SubProcess_game_five (GAME personality)
       ├─ ExecutableLoader maps GTA5.exe in-process (FS redirected via vfs)
       ├─ component framework boots inside the game process (gta-core-five hooks)
       ├─ spawns CEF subprocess(es) → NUI (main menu / server list / loading)
       └─ GTA window = THE app window; all UI composited inside it
connect: NUI (in-game CEF) → net stack (gta-net-five) → resource streaming
         (citizen-resources-*) → gameplay; disconnect returns to the in-game menu
```

## Mirror gaps vs upstream (verified)

1. `ext/cef` and `ext/cfx-ui` submodules absent → client UI cannot build from this mirror
   as-is (server `-game server` build is unaffected).
2. License files stripped (see licensing-assessment.md) — blocks lawful redistribution.
3. Slightly stale vs upstream master (no `mp2026_01` / build 3889).
