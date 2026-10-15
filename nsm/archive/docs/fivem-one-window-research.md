# Research: how FiveM gets "one window", and what gets NSM the same

Date: 2026-10-13 · Status: research only, no code written · Trigger: user — "the server
list and the game should be just running on nsm.exe… shouldn't bring up another window"

## 1. How FiveM actually does it (verified from the public citizenfx/fivem sources)

FiveM has **one window because the game process owns the window from the very
beginning, and every piece of UI is drawn inside it**. There is no launcher
window that later becomes a game window.

- `FiveM.exe` is only a bootstrap/update stub (the "MAIN" personality). It
  spawns two kinds of subprocesses from the same code base
  ([Game Integration, citizenfx/fivem](https://deepwiki.com/citizenfx/fivem/8-game-integration),
  from `code/client/launcher/premake5.lua`, `Main.cpp`, `CitizenGame.cpp`):
  - `CitizenFX_SubProcess_game_*` (GAME) — **loads GTA5.exe in-process**: maps
    the game executable, hooks `GetStartupInfoW` to intercept the game's entry,
    redirects the file system, then hands control to the game engine. The GTA
    window you see belongs to this process from the first frame.
  - `CitizenFX_SubProcess_chrome` (CHROME) — CEF subprocess that renders UI.
- The main menu, server list, loading screens and in-game menus are all **NUI**:
  CEF (Chromium) pages **composited as an overlay on the game's own DirectX
  surface inside the game window** — "the game renders it on top of the world"
  ([FiveM NUI tutorial](https://fivesecured.com/guides/fivem-nui-tutorial),
  [NUI overview](https://grokipedia.com/page/NUI_FiveM)). The main-menu UI
  itself lives in the game repo as a web app (`ext/cfx-ui` in
  [citizenfx/fivem](https://github.com/citizenfx/fivem)).
- Input: everything flows through the **game's own window messages**. The game
  always has focus; CEF pages only receive keyboard/mouse when the game grants
  it (`SetNuiFocus`). Nothing is ever embedded, reparented, or cross-process.

**Conclusion: FiveM never "embeds" anything. The window you open IS the game
window; the launcher UI is a web overlay drawn inside the game's frame.**

## 2. How altV does it (our client's parent architecture)

- altV's launcher window (server list) is **its own window** with a CEF webview
  rendered by a separate `altv-webengine.exe` subprocess
  ([altV client troubleshooting](https://docs.altv.mp/articles/troubleshooting/client.html)).
- On connect, GTA5.exe starts as its own process with **its own window**; the
  launcher window is separate (it closes/hides when the game starts). altV is
  *two windows in sequence*, not one. `-customui` replaces the launcher home
  page — it does not put UI inside the game window.

## 3. Where NSM stands today (verified in our source)

Two windows, because the list and the game live in **different processes**:

- **Server list window** = `msedge.exe --app=http://127.0.0.1:9987
  --window-size=1280,820` — a Microsoft Edge app window, a *separate process*
  (`OpenInAppWindow()` in `src/browser/browser_server.h`). Fallback: Chrome,
  Brave, then the system browser.
- **Game host window** = `NSMMainWindow`, a real window in the NSM.exe process
  (`NsmHostWndThread` in `src/connect.cpp`), shown only after the wrapper
  SetParents the GTA window into it (`src/wrapper.c` embed steps).

So during play the user sees: Edge window (list) + NSM window (game). Exactly
what they reported. Also observed in their log: clicking X on the game host
window mid-game hides it ("Host window hidden") — the game keeps running
invisible.

## 4. Can we copy FiveM's architecture exactly?

**No — blocked by the closed client.** True FiveM-style means the game window
exists from startup with our server list drawn inside it (in-game CEF overlay
before connecting to any server). That requires modifying the client to render
our UI at the GTA main menu. The gtamp client is closed, prebuilt binaries
patched at runtime (our own EXCLUDED_FILES.md: altv-client.dll, libce2.dll
"cannot be rebuilt"). altV-style `-customui` lives in the *launcher* window,
which disappears when the game starts — that path gives two windows, the thing
the user rejected.

## 5. What gets NSM the same *experience* (recommended)

**One NSM window that hosts both the list and the game:**

1. **Replace the Edge app window with an embedded WebView2 browser inside
   `NSMMainWindow`** (Microsoft's supported way to host Chromium in any Win32
   app; the runtime ships with Windows 10/11 and auto-installs otherwise).
   NSM.exe then owns the only window: open NSM → the list is right there,
   same window, one taskbar entry. Our existing UI (launcher_html_data.h) is
   served exactly as today — only the window around it changes.
2. **Game embed into that same window** — the SetParent flow already works
   (user's log: embed verified twice on real hardware). On connect: hide the
   browser child, embed the game; on leave: detach, show the browser again.
   List → play → leave → list, one window throughout. This *is* the FiveM UX.
3. **X-button policy while in game**: closing the single window while playing
   must mean "quit game + back to list" (or prompt), not "hide the game".

### Open risk: game input while embedded (packfix6-B)
Research on cross-process SetParent input issues
([MSDN SetParent](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setparent),
[SO: cross-process SetParent](https://stackoverflow.com/questions/3459874/good-or-evil-setparent-win32-api-between-different-processes),
[SO: embedding HWND](https://stackoverflow.com/questions/170800/embedding-hwnd-into-external-process-using-setparent)):
- `WS_CHILD` must be set (and `WS_POPUP` cleared) **before** `SetParent`, plus
  `SWP_FRAMECHANGED` — our wrapper currently sets the style *after*.
- Cross-process SetParent implicitly **attaches the two threads' input queues**
  (AttachThreadInput): one side blocking freezes the other; Windows 10 1703+
  force-resets the child process's input state on SetParent.
- Fallback that sidesteps all of it: **"fake embed"** — keep the game window
  top-level but make it *owned* by NSMMainWindow (owner ≠ parent: stays above
  the owner, minimizes with it, input completely normal) and sync its
  position/size over the host client area.
- **Unknown: did input actually work in the user's two embedded sessions?**
  They played ~2 min each and never complained about frozen input — the
  "input frozen" finding came from the Wine rig with the mock game. If real
  input works, packfix6 shrinks to item 1 + window policy.

## 6. Options summary

| Option | What | Verdict |
|---|---|---|
| 1. True FiveM architecture | game window from boot, list as in-game overlay | **Blocked** — needs client rebuild (closed binaries) |
| 2. One NSM window hosting WebView2 (list) + game (SetParent) | FiveM's *UX* on our architecture | **Recommended** — all pieces in our control |
| 3. Brand client home (-customui = our list) | altV-style | **Rejected by user** — two windows in sequence |

## 7. Sources
- citizenfx/fivem source + Game Integration wiki: https://github.com/citizenfx/fivem · https://deepwiki.com/citizenfx/fivem/8-game-integration
- NUI model: https://fivesecured.com/guides/fivem-nui-tutorial · https://grokipedia.com/page/NUI_FiveM
- altV client/webview: https://docs.altv.mp/articles/troubleshooting/client.html
- SetParent/input: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setparent · https://stackoverflow.com/questions/3459874 · https://stackoverflow.com/questions/170800/44950922
- Our own code: src/browser/browser_server.h (OpenInAppWindow), src/connect.cpp (NsmHostWndThread), src/wrapper.c (embed), user connect.log 2026-10-13 17:07–17:13
