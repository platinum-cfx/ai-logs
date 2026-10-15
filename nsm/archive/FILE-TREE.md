# GUIDED FILE TREE — workspace + repo

## A. This workspace (`/home/user/nsm/`)
```
nsm/
├── archive/                    ← THIS archive (survival kit)
│   ├── README.md               start here (index)
│   ├── MASTER-PROMPT.md        paste-into-new-chat boot file (token inside)
│   ├── CHAT-LOG.md             reconstructed chronological project log
│   ├── CI-BUILD-LOG.md         every Actions run + quota ledger
│   └── FILE-TREE.md            this file
├── a1-stock/                   ← A1 proof artifacts (the good stuff)
│   ├── NSM.exe                 4.9MB first rebranded client exe (v0.1, runs but lacks packaged deps)
│   └── FXServer-stock.exe      263KB stock server launcher exe (from first green build)
├── docs/
│   ├── fivem-source/licensing-assessment.md   final legal assessment (PLA quotes)
│   ├── fivem-source/architecture-map.md       STALE: claims ext/cef+cfx-ui missing (wrong)
│   ├── fivem-source/client-replacement-plan.md pre-A1 plan doc (needs update)
│   └── MASTER-PROMPT.md        original master prompt (also in archive/)
├── bin/                        old packfix5 canon: NSM.exe + connect.exe (pre-A1, not used in A1)
├── src/                        old wrapper sources (connect.cpp etc., pre-A1)
├── mocks/                      old test fakes (mock_masterlist.exe, mock_gta5.exe, altv mocks…)
├── matrix-logs/                old packfix matrix test logs
├── testpacks/                  old test pack fixtures (12MB)
├── uploads/                    old artifacts
├── e2e_production.sh, test-*.sh, patch_*.py    old test/patch tooling
├── tree.json                   mirror tree snapshot (2.2MB, used for import diff)
├── want.json / new_single_window.md            old planning notes
```

## B. The repo that matters: `platinum-cfx/NSM-FIVEM`
```
Branches:
├── main        stock + CI fixes (builds green; reference baseline)
└── a1-rebrand  = main + rebrand commits 1–6 (THE NSM branch)

Key files (rebrand touchpoints):
├── code/client/launcher/premake5.lua      targetname NSM (commit 1)
├── code/client/launcher/LauncherConfig.h  PRODUCT_NAME/CONTENT_NAME/LINK_PROTOCOL/CFX_UPDATER_URL (2,4)
├── code/client/launcher/launcher.rc       exe metadata (5)
├── code/server/launcher/premake5.lua      targetname nsm-server (3)
├── code/tools/ci/build_server_windows.ps1     server CI orchestrator
├── code/tools/ci/build_client.ps1             client CI orchestrator
├── code/tools/ci/build_server_docker_alpine.sh + build_server_proot_alpine.sh  (linux, FXServer refs renamed)
├── code/tools/ci/docker-builder/Dockerfile + proot_prepare.sh (git~=2.26 pin)
├── code/tools/ci/psm1/cfxRunMSBuild.psm1          (SDK retarget)
├── code/tools/ci/psm1/cfxUploadServerSymbols.psm1 (dry-run skip)
├── code/tools/ci/psm1/cfxUploadClientSymbols.psm1 (dry-run skip)
├── .github/workflows/p2-build.yml        THE CI factory (products: fxserver | fivem | fxserver-linux)
├── LICENSE, THIRD_PARTY_NOTICES.md, LICENSES/*   restored license set
└── README.md, BUILD-NSM.md               reference docs

Build outputs (in artifacts): .build-cache/bin/<five|server>/<platform>/release/
Client bundle = 607 files, 1.9GB unpacked. Server bundle ≈ 269MB.

Releases: github.com/platinum-cfx/NSM-FIVEM/releases
└── nsm-v0.1-preview  NSM-client-v0.1-preview.zip (490MB) — raw output, known-incomplete
```

## C. Other user repos (context)
- `fivem-source` — the untouched mirror (base of record; DO NOT TOUCH)
- `NSM` — old project (DO NOT TOUCH)
- `altv-test` — has `masterlist/` dir: the old altV masterlist/networking to reuse (commit 6 source)
- `GTAMPv1` — old own-engine launcher (v2.2.2)
- `coremp` — altV module collection
- forks: `txAdmin`, `cfx-server-data`, `natives`, `node-libclang`, `cef`, `fivem` (citizenfx fork)

## D. User machine (for the final test)
- GTA V (Steam): `C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V`
- Old NSM: `C:\Users\austi\Desktop\NSM-main\client-new\`
- Test server target: 127.0.0.1:7788 (historical); masterlist VPS: 194.104.146.133
