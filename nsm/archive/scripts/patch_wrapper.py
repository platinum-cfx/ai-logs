#!/usr/bin/env python3
"""Patch the embedding wrapper (nsm-steam-presence-source.c)."""
import sys

def patch(path, replacements, inserts=None):
    with open(path, 'r', newline='') as f:
        src = f.read()
    crlf = '\r\n' in src
    if crlf:
        src = src.replace('\r\n', '\n')
    for i, (old, new) in enumerate(replacements):
        n = src.count(old)
        if n != 1:
            print(f"ABORT {path}: anchor #{i} found {n} times:\n---\n{old[:200]}\n---")
            sys.exit(1)
        src = src.replace(old, new.replace('\n', '\r\n' if crlf else '\n'))
    for i, (anchor, before, block) in enumerate(inserts or []):
        n = src.count(anchor)
        if n != 1:
            print(f"ABORT {path}: insert anchor #{i} found {n} times")
            sys.exit(1)
        block = block.replace('\n', '\r\n' if crlf else '\n')
        src = src.replace(anchor, block + anchor if before else anchor + block)
    with open(path, 'w', newline='') as f:
        f.write(src)
    print(f"patched OK: {path}")

CFG_HELPER = r'''
/* .config may disable embedding (embed_game_window = false) - emergency
 * fallback so the game opens in its own window for troubleshooting. */
static int embed_enabled_by_config(void)
{
    char exe[MAX_PATH * 2], path[MAX_PATH * 2], line[512];
    char *slash; FILE *f; int enabled = 1;
    GetModuleFileNameA(NULL, exe, sizeof exe);
    slash = strrchr(exe, '\\');
    if (slash) *slash = 0;
    _snprintf(path, sizeof path, "%s\\.config", exe);
    f = fopen(path, "r");
    if (!f) return 1;
    while (fgets(line, sizeof line, f)) {
        if (_strnicmp(line, "embed_game_window", 17) == 0) {
            char *v = strchr(line, '=');
            if (v && strstr(v, "false")) enabled = 0;
            break;
        }
    }
    fclose(f);
    return enabled;
}

'''

R = []
# W1: verify the parent relationship after SetParent - never trust the return alone
R.append((
'''    dblog("embed: SetParent ok\\r\\n");

    st = GetWindowLongPtrA(gameWnd, GWL_STYLE);''',
'''    dblog("embed: SetParent ok\\r\\n");

    /* verify the actual parent relationship - never trust the return value alone */
    if (GetParent(gameWnd) != host) {
        dblog("embed: parent verify FAILED - leaving the game as a normal window\\r\\n");
        SetParent(gameWnd, NULL);
        return;
    }
    dblog("embed: parent verified\\r\\n");

    st = GetWindowLongPtrA(gameWnd, GWL_STYLE);'''))

# W2: recompute the non-client frame after the style change
R.append((
'    dblog("embed: child style set\\r\\n");',
'''    dblog("embed: child style set\\r\\n");

    SetWindowPosA(gameWnd, NULL, 0, 0, 0, 0,
                  SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE |
                  SWP_FRAMECHANGED);
    dblog("embed: frame updated\\r\\n");'''))

# W3: proper focus handover via AttachThreadInput
R.append((
'''    if (!SetFocus(gameWnd)) dblog("embed: SetFocus failed (cosmetic)\\r\\n");''',
'''    {
        DWORD gtid = GetWindowThreadProcessId(gameWnd, NULL);
        DWORD mtid = GetCurrentThreadId();
        BOOL at = (gtid && gtid != mtid) ? AttachThreadInput(mtid, gtid, TRUE) : FALSE;
        if (SetFocus(gameWnd)) dblog("embed: focus set\\r\\n");
        else dblog("embed: SetFocus failed (cosmetic)\\r\\n");
        if (at) AttachThreadInput(mtid, gtid, FALSE);
    }'''))

# W4: honor the embed_game_window setting
R.append((
'''    Sleep(1500);                            /* let the client UI come up */
    g_initialN = gta_pids(g_initial, 8, 0);''',
'''    Sleep(1500);                            /* let the client UI come up */
    if (!embed_enabled_by_config()) {
        dblog("embed: disabled by config (embed_game_window = false)\\r\\n");
        return 0;
    }
    g_initialN = gta_pids(g_initial, 8, 0);'''))

patch('/home/user/nsm/repo/client-new/nsm-steam-presence-source.c', R,
      inserts=[("static DWORD WINAPI embed_thread", True, CFG_HELPER)])

# W5: remove the release-download loop from pack_guard (release is gone; the
# launcher now installs the runtime directly from the local altv-runtime folder)
with open('/home/user/nsm/repo/client-new/nsm-steam-presence-source.c', 'r', newline='') as f:
    src = f.read()
crlf = '\r\n' in src
if crlf: src = src.replace('\r\n', '\n')
NL = '\r\n' if crlf else '\n'
m_start = src.find('_snprintf(pack, sizeof pack, "%s\\\\packs\\\\mp%d.pack", dir, i);')
assert m_start != -1, "pack loop start not found"
# back up to the start of the enclosing 'for' line
for_line = src.rfind('for (i = 1; i <= 7; i++) {', 0, m_start)
assert for_line != -1, "for line not found"
m_end = src.find('dblog("pack: guard done', m_start)
assert m_end != -1, "guard done marker not found"
# walk back from m_end to the start of its line
line_start = src.rfind(NL, 0, m_end) + len(NL)
replacement = (
    '/* NOTE: fetching the large mp1.pack from a GitHub release was removed -' + NL +
    ' * the launcher now installs the game runtime directly from the local' + NL +
    ' * altv-runtime folder shipped in the same ZIP (EnsureRuntimeInstalled in' + NL +
    ' * connect.cpp), so no release download is needed. Existing packs are left' + NL +
    ' * exactly as they are. */' + NL + '    ')
src = src[:for_line] + replacement + src[line_start:]
with open('/home/user/nsm/repo/client-new/nsm-steam-presence-source.c', 'w', newline='') as f:
    f.write(src)
print("pack_guard release-fetch removed OK")

# W6: .config - document the embedding toggle
with open('/home/user/nsm/repo/client-new/.config', 'r', newline='') as f:
    cfg = f.read()
nl = '\r\n' if '\r\n' in cfg else '\n'
if 'embed_game_window' not in cfg:
    cfg = cfg.replace(
        "masterlist_url = 'http://127.0.0.1:8080'",
        "masterlist_url = 'http://127.0.0.1:8080'" + nl + nl +
        "# Show the game inside the NSM window (false = GTA V opens in its own window)" + nl +
        "embed_game_window = true")
    with open('/home/user/nsm/repo/client-new/.config', 'w', newline='') as f:
        f.write(cfg)
    print(".config: embed_game_window added")
