# Deep Inventory — Every File, Every Match (Mission Phase 6)
_Swept: 13,553 files @ a1-rebrand (d6f7212). Method: full bare-clone git grep (reproducible via
`nsm/branding/sweep_inventory.py`). Raw evidence: `inventory/ALL-MATCHES.txt` (6,394 matches, tagged),
`inventory/FILENAMES.txt`, `inventory/WAVE1-FILES.txt`._

## Headline

| | |
|---|---|
| Files in tree | 13,553 |
| Files containing legacy terms | **2,143** |
| Already clean | 11,410 (84%) |
| Total matching lines | **6,394** |
| Files whose PATH contains a legacy term | 1,165 (KEEP-path — renaming breaks includes/build/runtime) |

## Every match classified

| Category | Lines | Files | Action |
|---|---|---|---|
| REBRAND-url | 1,419 | 639 | Split: cosmetic doc links → rebrand; functional endpoints → keep until own mirror (Wave 2) |
| REBRAND-docs | 1,373 | 1,080 | Rebrand (cosmetic comments/docs — Wave 3) |
| REVIEW | 985 | 295 | Manual triage: issue templates, CI names, build scripts (Wave 4) |
| **KEEP-scripting-api** | 930 | 233 | **UNTOUCHED — QBCore/ESX/script compat (user-approved)** |
| KEEP-internal-symbol | 712 | 177 | Untouched — C++ `namespace CitizenFX`, `Cfx*` classes (zero user visibility, high risk) |
| KEEP-runtime-id | 470 | 168 | Untouched — component names `citizen:server:*`, natives paths, DLL/source dir names |
| REBRAND-visible | 309 | 72 | **Wave 1 — user-visible strings (locale .po/.pot 239 lines, console/error strings)** |
| KEEP-vendor | 189 | 71 | Untouched — vendored third-party |
| KEEP-legal | 7 | 3 | Untouched — LICENSE/NOTICES (+ `AssemblyInfo` "Copyright CitizenFX" attribution lines = legal, reclassified) |

By term (overlapping): cfx 3,399 · citizen 2,259 · citizenfx 1,204 · fivem 1,061 · fxserver 412 · fivereborn 6

## URL reality check (Wave 2 decision data)

| Domain | Refs | Nature |
|---|---|---|
| content.cfx.re | 583 | **FUNCTIONAL — game cache/updater** (GameCache.cpp = 641 matches total). Works today; replacing requires own content mirror (Phase 2 project). Keep + document. |
| cfx.re (bare) | 577 | Mixed: doc links in comments → rebrand; some endpoints → verify each |
| runtime.fivem.net | 64 | **FUNCTIONAL — updater/crash endpoints.** Keep + document until mirror. |
| aka.cfx.re / static.cfx.re / *.users.cfx.re | ~15 | Functional/shortlinks — verify individually |
| docs.fivem.net / forum.* / wiki.* | ~20 | Cosmetic → rebrand |

## Execution waves

1. **Wave 1 — user-visible strings** (~72 files): locale `.po/.pot` (239 lines: "FiveM.com" → NSM Community, "FiveM Diag" → NSM Diag, etc.), C++ console/error strings, `launcher.manifest` `name="FiveM"`, `diagutil.rc` "FiveM Diagnostics Utility". Exceptions needing code-aware edits: `MiniDump.cpp` `fivem.exe+` match (add `nsm.exe+` case, keep old for legacy dumps), `console/premake5.lua` targetname (build output name — verify against build script first).
2. **Wave 2 — URLs**: cosmetic links rebranded; functional endpoints (content.cfx.re, runtime.fivem.net) kept + documented → own mirror in Phase 2.
3. **Wave 3 — docs/comments** (1,080 files, mechanical).
4. **Wave 4 — REVIEW triage** (295 files: .github templates, CI image names, build scripts).
5. **KEEP set documented** in this file (scripting API, runtime IDs, internal symbols, vendor, legal, paths).

## Legal guardrail (Phase 2 tie-in)

`AssemblyInfo.cs` lines "Copyright CitizenFX and contributors, licensed under the FiveM Platform Agreement"
are **attribution, not branding** — they stay (LGPL + honest provenance). Root LICENSE and
THIRD_PARTY_NOTICES.md untouched. This is the "legally required" bucket from the mission spec.
