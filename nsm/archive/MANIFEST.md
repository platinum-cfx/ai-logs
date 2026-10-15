# Archive manifest (tidied 2026-10-15)

Everything here is COMPLETED-phase material, kept for reference. Active work
lives in: nsm/CI-BUILD-LOG.md, nsm/branding/, nsm/masterlist/.

- docs/            Investigations: client crash, one-window research/plan,
                   launch-failure audit, real-Windows test, packs/tests READMEs,
                   fivem-source notes, MASTER-PROMPT.md (project brief).
- src/             Sources of early tools: connect.cpp (standalone connect),
                   wrapper.c, packer/mp-extractor, httplib.h (reusable for
                   NSMOwner.exe panel in Phase 3), discord.def, manifest.h.
- mocks-src/       .c/.h sources of test mocks (altv/gta5/listener/runner/
                   decrypt). Compiled exes + testpacks/ .pack fixtures deleted.
- logs/matrix-logs/  s1-s6 connect-matrix logs (pack fix verification).
- old-binaries/    bin/ (NSM.exe, connect.exe, discord_rpc.dll — v0.1/0.2-era
                   deliverables, superseded by in-build client) and a1-stock/
                   (stock FXServer.exe reference + old NSM.exe).
- scripts/         e2e.sh, e2e_production.sh, test-*.sh, patch_connect.py,
                   patch_wrapper.py (early-phase test/patch tooling).
- plans/           new_single_window.md, want.json.
- CHAT-LOG.md / CI-BUILD-LOG.md / FILE-TREE.md / MASTER-PROMPT.md / README.md
                   (pre-existing archive of the earliest phase).

Deleted (regenerable/obsolete): /home/user/go (74MB build cache), testpacks/
(12MB pack fixtures), tree.json (2.2MB file-tree dump), compiled mock
binaries, stray root .cpp fetches, rejected logo candidate.
