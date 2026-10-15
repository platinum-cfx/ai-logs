#!/usr/bin/env python3
"""Patch connect.cpp and nsm-steam-presence-source.c for fix/embedding.
Exact-match anchors; every anchor must hit exactly once or we abort."""
import sys, re

def patch(path, replacements, inserts=None):
    with open(path, 'r', newline='') as f:
        src = f.read()
    crlf = '\r\n' in src
    if crlf:
        src = src.replace('\r\n', '\n')
    for i, (old, new) in enumerate(replacements):
        n = src.count(old)
        if n != 1:
            print(f"ABORT {path}: anchor #{i} found {n} times (need 1):\n---\n{old[:200]}\n---")
            sys.exit(1)
        src = src.replace(old, new.replace('\n', '\r\n' if crlf else '\n'))
    for i, (anchor, before, block) in enumerate(inserts or []):
        n = src.count(anchor)
        if n != 1:
            print(f"ABORT {path}: insert anchor #{i} found {n} times")
            sys.exit(1)
        block = block.replace('\n', '\r\n' if crlf else '\n')
        if before:
            src = src.replace(anchor, block + anchor)
        else:
            src = src.replace(anchor, anchor + block)
    with open(path, 'w', newline='') as f:
        f.write(src)
    print(f"patched OK: {path} ({len(replacements)} replacements, {len(inserts or [])} inserts)")

# ---------------------------------------------------------------- connect.cpp
HELPERS = '''
// ============================================================
// FiveM-parity helpers: local masterlist + server auto-start,
// direct runtime install from the local altv-runtime folder,
// and the NSM host window the game is embedded into.
// ============================================================
static bool NsmPortOpen(const string& host, int port) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) return false;
    sockaddr_in a; memset(&a, 0, sizeof a);
    a.sin_family = AF_INET; a.sin_port = htons((u_short)port);
    a.sin_addr.s_addr = inet_addr(host.c_str());
    bool ok = (connect(s, (sockaddr*)&a, sizeof a) == 0);
    closesocket(s);
    return ok;
}

static bool NsmSpawnAndWaitPort(const string& exePath, const string& workDir,
                                const string& host, int port, int timeoutMs) {
    STARTUPINFOA si; PROCESS_INFORMATION pi;
    memset(&si, 0, sizeof si); si.cb = sizeof si;
    char cmd[MAX_PATH * 2];
    _snprintf(cmd, sizeof cmd, "\\"%s\\"", exePath.c_str());
    if (!CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL,
                        workDir.c_str(), &si, &pi)) return false;
    CloseHandle(pi.hThread);
    for (int t = 0; t < timeoutMs; t += 500) {
        if (NsmPortOpen(host, port)) { CloseHandle(pi.hProcess); return true; }
        Sleep(500);
    }
    CloseHandle(pi.hProcess);
    return NsmPortOpen(host, port);
}

static bool NsmIsLocalHost(const string& h) {
    return h == "127.0.0.1" || h == "localhost" || h.empty();
}

static void EnsureLocalMasterlistRunning(const string& baseDir, const string& masterlistUrl) {
    string u = masterlistUrl;
    if (u.rfind("http://", 0) == 0) u = u.substr(7);
    else if (u.rfind("https://", 0) == 0) u = u.substr(8);
    size_t slash = u.find('/');
    if (slash != string::npos) u = u.substr(0, slash);
    string host = "127.0.0.1"; int port = 8080;
    size_t c = u.find(':');
    if (c != string::npos) {
        host = u.substr(0, c);
        try { port = stoi(u.substr(c + 1)); } catch (...) {}
    } else if (!u.empty()) host = u;
    if (!NsmIsLocalHost(host)) return;             // only auto-start our own
    if (NsmPortOpen(host, port)) return;           // already running
    const char* rel[] = { "\\\\..\\\\masterlist\\\\masterlist.exe", "\\\\masterlist\\\\masterlist.exe" };
    for (const char* r : rel) {
        string exe = baseDir + r;
        if (GetFileAttributesA(exe.c_str()) != INVALID_FILE_ATTRIBUTES) {
            string dir = exe.substr(0, exe.find_last_of("\\\\/"));
            WriteLog("Starting local masterlist...");
            if (NsmSpawnAndWaitPort(exe, dir, host, port, 10000))
                WriteLog("Local masterlist is running.");
            else
                WriteLog("Local masterlist did not open its port; continuing.");
            return;
        }
    }
    WriteLog("masterlist.exe not found next to the launcher; assuming it runs elsewhere.");
}

static void EnsureLocalServerRunning(const string& baseDir, const string& host, int port) {
    if (!NsmIsLocalHost(host)) return;             // remote servers are never started by us
    if (NsmPortOpen(host, port)) { WriteLog("Local game server already running."); return; }
    const char* rel[] = { "\\\\..\\\\server\\\\gtamp-server.exe", "\\\\server\\\\gtamp-server.exe" };
    for (const char* r : rel) {
        string exe = baseDir + r;
        if (GetFileAttributesA(exe.c_str()) != INVALID_FILE_ATTRIBUTES) {
            string dir = exe.substr(0, exe.find_last_of("\\\\/"));
            WriteLog("Starting local game server (gtamp-server.exe)...");
            if (NsmSpawnAndWaitPort(exe, dir, host, port, 15000))
                WriteLog("Local game server is running.");
            else
                WriteLog("Local game server did not open its port; the client will retry.");
            return;
        }
    }
    WriteLog("gtamp-server.exe not found next to the launcher; nothing to auto-start.");
}

static void NsmCopyTreeSkipExisting(const string& src, const string& dst) {
    CreateDirectoryA(dst.c_str(), NULL);
    string pat = src + "\\\\*";
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pat.c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE) return;
    do {
        if (!strcmp(fd.cFileName, ".") || !strcmp(fd.cFileName, "..")) continue;
        string s = src + "\\\\" + fd.cFileName;
        string d = dst + "\\\\" + fd.cFileName;
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            NsmCopyTreeSkipExisting(s, d);
        } else if (GetFileAttributesA(d.c_str()) == INVALID_FILE_ATTRIBUTES) {
            CopyFileA(s.c_str(), d.c_str(), TRUE);
        }
    } while (FindNextFileA(h, &fd));
    FindClose(h);
}

static void EnsureRuntimeInstalled(const string& baseDir, const string& targetDir) {
    string altvExe = targetDir + "\\\\altv.exe";
    if (GetFileAttributesA(altvExe.c_str()) != INVALID_FILE_ATTRIBUTES) return; // already present
    const char* rel[] = { "\\\\..\\\\altv-runtime", "\\\\altv-runtime" };
    for (const char* r : rel) {
        string rtRoot = baseDir + r;
        string pat = rtRoot + "\\\\*";
        WIN32_FIND_DATAA fd;
        HANDLE h = FindFirstFileA(pat.c_str(), &fd);
        if (h == INVALID_HANDLE_VALUE) continue;
        do {
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) continue;
            if (!strcmp(fd.cFileName, ".") || !strcmp(fd.cFileName, "..")) continue;
            string sub = rtRoot + "\\\\" + fd.cFileName;
            if (GetFileAttributesA((sub + "\\\\altv.exe").c_str()) == INVALID_FILE_ATTRIBUTES) continue;
            WriteLog("Installing game runtime from: " + sub);
            NsmCopyTreeSkipExisting(sub, targetDir);
            WriteLog("Game runtime install complete.");
            FindClose(h);
            return;
        } while (FindNextFileA(h, &fd));
        FindClose(h);
    }
    WriteLog("No local altv-runtime folder found; relying on pack extraction only.");
}

// ---- NSM host window: the application window the game is embedded into ----
static HWND g_nsmHostWnd = NULL;

static LRESULT CALLBACK NsmHostWndProc(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (m == WM_CLOSE) { ShowWindow(h, SW_HIDE); return 0; }  // hide, never destroy
    return DefWindowProcA(h, m, w, l);
}

static DWORD WINAPI NsmHostWndThread(LPVOID unused) {
    (void)unused;
    WNDCLASSA wc; memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = NsmHostWndProc;
    wc.hInstance = GetModuleHandleA(NULL);
    wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    wc.hIcon = LoadIconA(GetModuleHandleA(NULL), MAKEINTRESOURCEA(1));
    wc.lpszClassName = "NSMMainWindow";
    RegisterClassA(&wc);
    g_nsmHostWnd = CreateWindowExA(0, "NSMMainWindow", "NSM",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 1280, 820,
        NULL, NULL, GetModuleHandleA(NULL), NULL);
    MSG msg;
    while (g_nsmHostWnd && GetMessageA(&msg, NULL, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    return 0;
}

static void ShowHostWindow(const char* title) {
    if (!g_nsmHostWnd) return;
    SetWindowTextA(g_nsmHostWnd, title);
    if (IsIconic(g_nsmHostWnd)) ShowWindow(g_nsmHostWnd, SW_RESTORE);
    else ShowWindow(g_nsmHostWnd, SW_SHOW);
    SetForegroundWindow(g_nsmHostWnd);
    SetActiveWindow(g_nsmHostWnd);
}

static void HideHostWindow() {
    if (g_nsmHostWnd) ShowWindow(g_nsmHostWnd, SW_HIDE);
}

'''

R = []
# P1: WriteLog localtime_s portability (mingw)
R.append((
"""        struct tm parts;
        localtime_s(&parts, &now_c);""",
"""        struct tm parts;
#ifdef _MSC_VER
        localtime_s(&parts, &now_c);
#else
        struct tm* pparts = localtime(&now_c);
        if (pparts) parts = *pparts;
#endif"""))

# P2a: EnsureGtaPathConfigured signature
R.append((
"inline bool EnsureGtaPathConfigured(const string& baseDir) {",
"inline bool EnsureGtaPathConfigured(const string& baseDir, bool allowPrompt) {"))
# P2b: prompt only when asked
R.append((
"""    // Prompt user to browse for GTA5.exe
    string userChosen = BrowseForGtaExe();""",
"""    // Prompt user to browse for GTA5.exe (only at Connect time, never at startup,
    // so no mysterious dialog appears before the server browser opens)
    string userChosen = allowPrompt ? BrowseForGtaExe() : "";"""))

# P3a: WinMain reorder - early log init + silent detection + masterlist autostart
R.append((
"""    string baseDir = GetExecutableDir();
    EnsureGtaPathConfigured(baseDir);
    string masterlistUrl = ReadConfigValue(baseDir, "masterlist_url", "http://127.0.0.1:8080");""",
"""    string baseDir = GetExecutableDir();

    // Determine Local app directory FIRST - the log must exist before any GTA
    // detection so every path decision is visible in connect.log
    char localAppData[MAX_PATH];
    ExpandEnvironmentStringsA("%LOCALAPPDATA%", localAppData, MAX_PATH);
    string key = "gtamp";
    string targetDir = string(localAppData) + "\\\\" + ComputeHash(key);
    CreateDirectoryA((targetDir + "\\\\logs").c_str(), NULL);
    g_logFilePath = targetDir + "\\\\logs\\\\connect.log";
    WriteLog("Starting connect.exe / NSM.exe");

    // Silent GTA detection at startup (saves to .config when found; NEVER prompts)
    EnsureGtaPathConfigured(baseDir, false);
    string masterlistUrl = ReadConfigValue(baseDir, "masterlist_url", "http://127.0.0.1:8080");

    // FiveM parity: if the masterlist is local and not running, start it
    EnsureLocalMasterlistRunning(baseDir, masterlistUrl);"""))

# P3b: remove the old later duplicate block
R.append((
"""
    // Determine Local app directory
    char localAppData[MAX_PATH];
    ExpandEnvironmentStringsA("%LOCALAPPDATA%", localAppData, MAX_PATH);
    string key = "gtamp";
    string targetDir = string(localAppData) + "\\\\" + ComputeHash(key);
    
    CreateDirectoryA((targetDir + "\\\\logs").c_str(), NULL);
    g_logFilePath = targetDir + "\\\\logs\\\\connect.log";
    WriteLog("Starting connect.exe / NSM.exe");
""",
""))

# P4: start host window thread after launcher server
R.append((
"""    // Start embedded launcher server and open dedicated FiveM-styled launcher window
    if (!gtamp::StartLauncherServer(baseDir, masterlistUrl, !hasConnect)) {
        return 0;
    }
""",
"""    // Start embedded launcher server and open dedicated FiveM-styled launcher window
    if (!gtamp::StartLauncherServer(baseDir, masterlistUrl, !hasConnect)) {
        return 0;
    }

    // NSM host window: the real application window the game gets embedded into
    CreateThread(NULL, 0, NsmHostWndThread, NULL, 0, NULL);
"""))

# P5: loop - parse port, auto-start server, connect-time GTA check
R.append((
"""        size_t colon = pickedServer.find(':');
        serverIp = (colon != string::npos) ? pickedServer.substr(0, colon) : pickedServer;
        connectArgs = "-connecturl altv://connect/" + pickedServer;""",
"""        size_t colon = pickedServer.find(':');
        serverIp = (colon != string::npos) ? pickedServer.substr(0, colon) : pickedServer;
        int serverPort = 7788;
        if (colon != string::npos) { try { serverPort = stoi(pickedServer.substr(colon + 1)); } catch (...) {} }
        connectArgs = "-connecturl altv://connect/" + pickedServer;

        // FiveM parity: if connecting to a local server that is not running, start it
        EnsureLocalServerRunning(baseDir, serverIp, serverPort);

        // GTA path must be valid before the client starts - ask NOW, not at startup,
        // so the picker appears exactly when the user tries to connect
        if (!EnsureGtaPathConfigured(baseDir, true)) {
            MessageBoxW(NULL,
                L"NSM could not find your GTA V installation.\\nPress Connect again and choose your GTA5.exe in the folder picker that appears.",
                L"NSM - GTA V location", MB_ICONWARNING | MB_OK);
            if (hasConnect) break;
            continue;
        }"""))

# P6: stop wiping the runtime on reboot
R.append((
"        MarkForDeleteOnReboot(targetDir);",
"""        // NOTE: the game runtime in %LOCALAPPDATA% is intentionally NOT wiped on
        // reboot anymore. Files persist; anything missing is re-installed from the
        // local altv-runtime folder - no 230MB pack download is ever needed."""))

# P7: direct runtime install before proxy load
R.append((
"""        // Load proxy.dll and start proxy
        string proxyPath = targetDir + "\\\\proxy\\\\proxy.dll";""",
"""        // Make sure the game runtime is fully present (fresh install or after a
        // reboot). Installs add-only from the altv-runtime folder shipped in the ZIP.
        EnsureRuntimeInstalled(baseDir, targetDir);

        // Load proxy.dll and start proxy
        string proxyPath = targetDir + "\\\\proxy\\\\proxy.dll";"""))

# P8: show host window right before launching the game
R.append((
"""        // Start altv.exe
        string altvExe = targetDir + "\\\\altv.exe";""",
"""        // Show the NSM host window - the game window is embedded into it
        if (ReadConfigValue(baseDir, "embed_game_window", "true") != "false") {
            ShowHostWindow(("NSM - " + (pickedName.empty() ? pickedServer : pickedName)).c_str());
        }

        // Start altv.exe
        string altvExe = targetDir + "\\\\altv.exe";"""))

# P9: hide host window when the session ends
R.append((
"""        // If launcher was invoked directly with command-line -connect, exit after game closes.
        if (hasConnect) {
            break;
        }""",
"""        // Session over: hide the game host window - the server browser is the app again
        HideHostWindow();

        // If launcher was invoked directly with command-line -connect, exit after game closes.
        if (hasConnect) {
            break;
        }"""))

patch('/home/user/nsm/repo/sources/cpp/connect.cpp', R, inserts=[("int APIENTRY WinMain", True, HELPERS)])
