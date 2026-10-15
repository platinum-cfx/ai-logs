# NSM PROJECT ARCHIVE — README (start here)
_Created 2026-10-14 ~06:40 UTC. Self-contained survival kit for the NSM platform build._

## What this archive is
Everything needed to resume, audit, or hand off the NSM project: the master prompt
(for booting a fresh AI session with full control), the full chronological story of
the build, the CI build ledger, and a guided map of every file.

## Archive contents
| File | What it is |
|---|---|
| `MASTER-PROMPT.md` | Paste-into-a-new-chat boot file: token, repo, recipe, rules, next steps |
| `CHAT-LOG.md` | Reconstructed chronological log of the whole project (phases, errors, fixes, decisions) |
| `CI-BUILD-LOG.md` | Every GitHub Actions run: what it was, what happened, what it taught us |
| `FILE-TREE.md` | Guided map: this workspace AND the NSM-FIVEM repo |

## The 30-second version
NSM = user's own FiveM (GTA V multiplayer platform) built from their fivem-source copy.
Repo: platinum-cfx/NSM-FIVEM (private). CI factory on GitHub Actions is proven green
on stock (server Windows+Linux, client). Rebrand (NSM.exe, nsm-server.exe, NSM identity,
user's endpoints) is 6 commits deep on `a1-rebrand`. v0.1 preview released and
launch-tested by the user (exe runs, dies on missing packaged files — expected).
v0.2 (properly packed) client+server were compiling at time of archive. Remaining:
masterlist/keymaster wiring, leak sweep, first 2-player test on the user's PC.

## Where truth lives (in priority order)
1. The GitHub repo (commits = reality) — platinum-cfx/NSM-FIVEM
2. The Actions tab (build results + logs)
3. This archive (state + decisions)
4. Any AI chat's memory (including the one that wrote this) — verify against 1–3.
