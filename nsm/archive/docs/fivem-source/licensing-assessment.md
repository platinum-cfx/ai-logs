# fivem-source — Licensing & Reuse Assessment

Inspected: 2026-10-13 · `platinum-cfx/fivem-source` @ `06215ba`
Verdict up front: **the repository is two-tier licensed. The parts that make it a GTA V
multiplayer client are Take-Two proprietary and may NOT be reused for NSM. A defined
subset ("the Files") is LGPL-2.0 and IS reusable, with obligations.**

## 1. The actual license (upstream `citizenfx/fivem` LICENSE, since the 2023 Take-Two acquisition)

> © 2023 Take-Two Interactive Software, Inc. All rights reserved.
> Use of this software is subject to the Rockstar Games Creator Platform License
> Agreement (fivem.net/terms) and all terms referenced therein.
>
> However, the following files and directories, collectively referred to as the "Files":
> `code/client/shared/`, `code/client/citicore/`, `code/client/launcher/`,
> `code/client/common/`, `code/tools/`, `code/components/citizen-*/`,
> `code/components/font-renderer/`, `code/components/vfs-core/`, `code/vendor/*.lua`
> are free software under the **GNU LGPL 2.0**.

Everything not in that list is governed by the Rockstar Games Creator Platform License
Agreement — a platform terms-of-use, **not** an open-source license granting reuse in a
separate product. NSM is a separate product; the Creator Platform terms do not grant
NSM the right to redistribute or modify those parts.

## 2. Component-by-component classification

**LGPL-2.0 (reusable for NSM, with LGPL obligations):**
- `code/client/launcher/` — the bootstrap/one-window loader spine (personality system,
  ExecutableLoader, game-host subprocess)
- `code/client/{shared,citicore,common}/` — core utilities, component framework base
- `code/components/citizen-*` — **all of them**: resources-*, scripting-*, level-loader-*,
  mod-loader, playernames-*, game-main/ipc, devtools, and **the entire citizen-server-\*
  fxserver implementation**
- `code/components/{font-renderer,vfs-core}/`, `code/tools/`, `code/vendor/*.lua`
- Estimate: ~35 of 117 components, but including the launcher spine and the whole server

**Take-Two proprietary (NOT reusable for NSM):**
- All GTA V game integration: `gta-core-five`, `gta-game-five`, `gta-streaming-five`,
  `gta-net-five`, `gta-mission-cleanup-five`, `extra-natives-five`,
  `loading-screens-five`, `handling-loader-five`, `rage-*-five` (allocator, device,
  graphics, input, nutsnbolts, scripting), `scripthookv`, `asi-five`, `pool-sizes-state`
- All NUI/UI machinery: `nui-core`, `nui-gsclient`, `nui-resources`, `conhost-v2/-posh`, `n19ui`
- Network transport: `net`, `net-base`, `net-packet`, `net-tcp-server`, `net-http-server`
- Platform: `legitimacy` (ownership validation), `discord`, `http-client`, `voip-*`, `glue`, `sticky`
- All `*-rdr3` / `*-ny` variants of the above; `data/`, `ext/sdk` natives data
- **These are precisely the components that implement "connect to a server, stream
  resources, render UI in-game, play multiplayer." A client built only from the LGPL
  tier boots GTA V in one window but has no multiplayer and no in-game UI.**

**Third-party (vendor/, per their own licenses — mostly permissive):**
curl (curl license), protobuf (BSD), v8 (BSD), boost (BSL), lua (MIT), minhook (BSD),
zlib, openssl, node, and ~140 more — reusable per their terms; attribution required.

## 3. State of the platinum-cfx mirror (compliance defects — verified in git history)

The mirror's 18 commits are the squashed import plus four commits that **delete license text**:
- `d118a63` "Update LICENSE" — deletes the entire 34-line LICENSE (the Take-Two + LGPL notice)
- `650aeb6` "Update MIT.txt", `ccb3445` "Update curl.txt", `3677194` "Update Zlib.txt" —
  delete the full text of those LICENSES/ files
- `THIRD_PARTY_NOTICES.md` and `README.md` are also blanked

**Consequence: as it stands, this mirror strips required licensing information. No reuse
or redistribution is compliant until the upstream LICENSE, LICENSES/*.txt and
THIRD_PARTY_NOTICES.md are restored verbatim.** (Restore is prepared as Phase 1 of the
plan; it is 4 files, additive, no code changes.)

## 4. LGPL obligations if NSM reuses the launcher spine / citizen-* components

- Keep the LGPL-2.0 notice with the code; state changes made to the Files
- LGPL §2: distribute modified Files' **source** alongside any binary distribution
- LGPL linking: if linked statically into a closed NSM binary, object files must be
  provided so relinking is possible — dynamic linking or full NSM-source distribution avoids this
- Do not imply Cfx.re/Take-Two endorsement of NSM (upstream notices must travel with the code)

## 4b. The Rockstar Games Creator Platform License Agreement (fivem.net/terms, 10-Sept-2026 revision) — key clauses, verbatim

The repo LICENSE makes the non-LGPL tier "subject to" this agreement. What it actually grants:

> §2.1 Grant: "…Rockstar grants you a limited, non-exclusive, non-transferable,
> non-sublicensable, **revocable** license to **access and use the Creator Services**…"
> (§1.1: Creator Services = "the software platforms commonly known as 'FiveM' and 'RedM'")

> §2.2 Restrictions: "Nothing in this Creator PLA grants you any right to use, reproduce,
> copy, adapt, edit, modify, distribute… **create derivative works based on** … other than
> as expressly permitted by Rockstar."

> §7.2: "Rockstar reserves the right to take Adverse Action… in the event of a breach."

Reading: the non-LGPL code is licensed for **using FiveM/RedM as Rockstar's platforms**.
It grants no right to build a different, rebranded product (NSM) from that code and
distribute it. Building stock, unmodified, for personal use is the "use the Services"
case; modification + redistribution is not granted. The LGPL "Files" list remains the
only tier carrying modification/distribution rights.

## 5. Bottom line

| Goal | Lawful from this source? |
|---|---|
| Build stock FiveM/FXServer unmodified for personal use | Yes (subject to fivem.net/terms) |
| Reuse LGPL launcher spine + citizen-* framework in NSM | **Yes**, with §4 obligations |
| Reuse gta-core/net/nui/streaming (the multiplayer core) in NSM | **No** — Take-Two proprietary |
| Full "FiveM-style NSM client" from this repo | **No** — the required core is not licensed for it |
| Publish the current mirror (license files stripped) | **No** — restore notices first |
