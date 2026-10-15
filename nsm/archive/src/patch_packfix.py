#!/usr/bin/env python3
# packfix patch for connect.cpp (NSM "mp1.pack not found when it exists")
# - DecryptDataAES: reports the exact failure reason
# - EnsureGameFilesReady: rewritten per spec
# - call site: reason-driven error dialog
# - startup: exe path / baseDir / CWD / build id logging
import sys

PATH = "connect.cpp"
src = open(PATH, "rb").read().decode("latin-1").replace("\r\n", "\n")
CRLF = "\r\n"

def rep(old, new, what):
    global src
    if src.count(old) != 1:
        print(f"ANCHOR FAIL ({src.count(old)}x): {what}")
        sys.exit(1)
    src = src.replace(old, new)
    print(f"ok: {what}")

# ---------------- 1. DecryptDataAES: signature + reasons ----------------
rep('bool DecryptDataAES(const string& inputFile, const string& outputFile) {',
    'bool DecryptDataAES(const string& inputFile, const string& outputFile, string* why = nullptr) {',
    "DecryptDataAES signature")

rep('    if (!in.is_open()) return false;',
    '''    if (!in.is_open()) {
        DWORD oe = 0;
        WIN32_FILE_ATTRIBUTE_DATA ofad;
        if (GetFileAttributesExA(inputFile.c_str(), GetFileExInfoStandard, &ofad)) {
            oe = (ofad.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) ? ERROR_ACCESS_DENIED : 0;
        } else {
            oe = GetLastError();
        }
        if (why) *why = "cannot open the pack file (Windows error " + to_string(oe) + ")" +
            (oe == ERROR_ACCESS_DENIED ? " - access denied: check folder permissions or antivirus" :
             (oe == ERROR_FILE_NOT_FOUND || oe == ERROR_PATH_NOT_FOUND) ? " - file not found" : "");
        return false;
    }''',
    "decrypt: input open reason")

rep('    if (!out.is_open()) return false;',
    '''    if (!out.is_open()) {
        if (why) *why = "cannot create the temporary extractor file " + outputFile + " - check disk space and folder permissions";
        return false;
    }''',
    "decrypt: output open reason")

rep('    if (in.gcount() != 16) return false;',
    '''    if (in.gcount() != 16) {
        if (why) *why = "file is smaller than 16 bytes - not a valid NSM pack";
        return false;
    }''',
    "decrypt: short read reason")

rep('''    if (!CryptAcquireContext(&hProv, NULL, MS_ENH_RSA_AES_PROV, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) {
        return false;
    }''',
    '''    if (!CryptAcquireContext(&hProv, NULL, MS_ENH_RSA_AES_PROV, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) {
        if (why) *why = "Windows crypto provider unavailable (error " + to_string(GetLastError()) + ")";
        return false;
    }''',
    "decrypt: acquire context reason")

rep('''    if (!CryptImportKey(hProv, (BYTE*)&blob, sizeof(blob), 0, 0, &hKey)) {
        CryptReleaseContext(hProv, 0);
        return false;
    }''',
    '''    if (!CryptImportKey(hProv, (BYTE*)&blob, sizeof(blob), 0, 0, &hKey)) {
        if (why) *why = "cannot import the AES key (error " + to_string(GetLastError()) + ")";
        CryptReleaseContext(hProv, 0);
        return false;
    }''',
    "decrypt: import key reason")

rep('''        if (!CryptDecrypt(hKey, 0, isFinal, 0, buffer, &dataLen)) {
            CryptDestroyKey(hKey);
            CryptReleaseContext(hProv, 0);
            return false;
        }''',
    '''        if (!CryptDecrypt(hKey, 0, isFinal, 0, buffer, &dataLen)) {
            if (why) *why = "decryption failed - the file is corrupt, truncated, or not a valid NSM pack (wrong key or damaged content)";
            CryptDestroyKey(hKey);
            CryptReleaseContext(hProv, 0);
            return false;
        }''',
    "decrypt: CryptDecrypt reason")

# ---------------- 2. helpers + new EnsureGameFilesReady ----------------
NEWFUNC = r'''// ---- pack resolution + diagnostics ------------------------------------------
// Rewritten after the real-machine report "mp1.pack not found although the
// file exists": the launcher now
//   1. logs the running NSM.exe path, baseDir and the working directory,
//   2. probes EVERY candidate pack directory and EVERY pack file (absolute
//      path, size, Windows error code),
//   3. validates all seven packs in a candidate BEFORE selecting it - no
//      directory switching halfway through extraction,
//   4. reports the exact failing item (missing pack / decryption failure /
//      extractor DLL load failure / missing entry point / missing runtime
//      files after extraction) instead of a generic "mp1.pack not found".
// All paths resolve from the location of NSM.exe itself - never from the
// current working directory.
static void NsmLogDirListing(const string& dir) {
    string pat = dir + "\\*";
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pat.c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE) {
        WriteLog("  folder " + dir + " : cannot list contents (Windows error " + to_string(GetLastError()) + ")");
        return;
    }
    string lines = "  folder " + dir + " contains:";
    int shown = 0;
    do {
        if (!strcmp(fd.cFileName, ".") || !strcmp(fd.cFileName, "..")) continue;
        if (shown >= 12) { lines += "\n    ... (more entries not shown)"; break; }
        long long sz = ((long long)fd.nFileSizeHigh << 32) | (long long)fd.nFileSizeLow;
        lines += "\n    ";
        lines += fd.cFileName;
        lines += (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) ? " (folder)" : (" (" + to_string(sz) + " B)");
        ++shown;
    } while (FindNextFileA(h, &fd));
    FindClose(h);
    if (shown == 0) lines = "  folder " + dir + " : (EMPTY - no files or subfolders)";
    WriteLog(lines);
}

struct NsmPackProbe { bool exists; long long size; DWORD err; };

static NsmPackProbe NsmProbeFile(const string& path) {
    NsmPackProbe p; p.exists = false; p.size = 0; p.err = 0;
    WIN32_FILE_ATTRIBUTE_DATA fad;
    if (GetFileAttributesExA(path.c_str(), GetFileExInfoStandard, &fad)) {
        if (fad.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) { p.err = ERROR_ACCESS_DENIED; return p; }
        p.exists = true;
        p.size = ((long long)fad.nFileSizeHigh << 32) | (long long)fad.nFileSizeLow;
    } else {
        p.err = GetLastError();
    }
    return p;
}

static string NsmErrHint(DWORD e) {
    if (e == ERROR_FILE_NOT_FOUND) return " - file not found";
    if (e == ERROR_PATH_NOT_FOUND) return " - a folder in the path does not exist";
    if (e == ERROR_ACCESS_DENIED) return " - access denied: check folder permissions or antivirus";
    if (e == ERROR_SHARING_VIOLATION) return " - file is locked by another process";
    return "";
}

static string NsmParentDir(const string& dir) {
    string::size_type pos = dir.find_last_of("\\/");
    if (pos == string::npos || pos < 3) return "";
    return dir.substr(0, pos);
}

// Same source discovery as EnsureRuntimeInstalled: <baseDir>\..\altv-runtime
// and <baseDir>\altv-runtime, each with a version subfolder containing
// altv.exe. Returns the absolute source path for relPath, or "".
static string NsmRuntimeSourcePath(const string& baseDir, const string& relPath) {
    const char* rel[] = { "\\..\\altv-runtime", "\\altv-runtime" };
    for (const char* r : rel) {
        string rtRoot = baseDir + r;
        string pat = rtRoot + "\\*";
        WIN32_FIND_DATAA fd;
        HANDLE h = FindFirstFileA(pat.c_str(), &fd);
        if (h == INVALID_HANDLE_VALUE) continue;
        do {
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) continue;
            if (!strcmp(fd.cFileName, ".") || !strcmp(fd.cFileName, "..")) continue;
            string sub = rtRoot + "\\" + fd.cFileName;
            if (GetFileAttributesA((sub + "\\altv.exe").c_str()) == INVALID_FILE_ATTRIBUTES) continue;
            if (GetFileAttributesA((sub + relPath).c_str()) != INVALID_FILE_ATTRIBUTES) return sub + relPath;
        } while (FindNextFileA(h, &fd));
        FindClose(h);
    }
    return "";
}

// UTF-8 text -> wide MessageBox (paths may contain non-ASCII user names)
static void NsmMessageBox(const string& utf8Msg, const char* title, UINT flags) {
    int wl = MultiByteToWideChar(CP_UTF8, 0, utf8Msg.c_str(), -1, NULL, 0);
    int tl = MultiByteToWideChar(CP_UTF8, 0, title, -1, NULL, 0);
    if (wl <= 0 || tl <= 0) { MessageBoxA(NULL, utf8Msg.c_str(), title, flags); return; }
    wchar_t* wm = new wchar_t[wl];
    wchar_t* wt = new wchar_t[tl];
    MultiByteToWideChar(CP_UTF8, 0, utf8Msg.c_str(), -1, wm, wl);
    MultiByteToWideChar(CP_UTF8, 0, title, -1, wt, tl);
    MessageBoxW(NULL, wm, wt, flags);
    delete[] wm; delete[] wt;
}

bool EnsureGameFilesReady(const string& baseDir, const string& targetDir, string* failReasonOut = nullptr) {
    // ---- fast path: runtime already complete and manifest-verified ----
    bool dirValid = true;
    int manifestSize = sizeof(g_Manifest) / sizeof(g_Manifest[0]);
    for (int i = 0; i < manifestSize; ++i) {
        string filePath = targetDir + g_Manifest[i].relPath;
        if (filePath.find("skin.bin") != string::npos) continue;

        size_t actualSize = GetFileSizeStr(filePath);
        if (actualSize != g_Manifest[i].expectedSize) {
            dirValid = false;
            break;
        }
    }

    if (dirValid) {
        string altvPath = targetDir + "\\altv.exe";
        DWORD attr = GetFileAttributesA(altvPath.c_str());
        if (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
            WriteLog("Game files verified and ready in " + targetDir);
            return true;
        }
    }

    // ---- log the real paths (everything resolves from the EXE location) ----
    char exePath[MAX_PATH] = {0};
    char cwdBuf[MAX_PATH] = {0};
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    GetCurrentDirectoryA(MAX_PATH, cwdBuf);
#ifdef NSM_BUILD_ID
    WriteLog("NSM build: " NSM_BUILD_ID);
#endif
    WriteLog("EnsureGameFilesReady: NSM.exe path = " + string(exePath));
    WriteLog("EnsureGameFilesReady: baseDir (folder of NSM.exe, the ONLY folder used for pack lookups) = " + baseDir);
    WriteLog("EnsureGameFilesReady: current working directory (informational only, NEVER used for pack lookups) = " + string(cwdBuf));
    WriteLog("EnsureGameFilesReady: game runtime targetDir = " + targetDir);
    WriteLog("Extracting game packs into " + targetDir + "...");

    // ---- candidate pack directories, in priority order ----
    // documented layouts:  <NSM folder>\packs          (exe next to packs\)
    //                     <NSM folder>\client-new\packs (shipped ZIP layout)
    // plus the parent folder when NSM.exe sits inside client-new, and the
    // legacy "loose packs next to the exe" layout.
    string candidates[4]; int candCount = 0;
    candidates[candCount++] = baseDir + "\\packs";
    candidates[candCount++] = baseDir + "\\client-new\\packs";
    string parentDir = NsmParentDir(baseDir);
    if (!parentDir.empty()) candidates[candCount++] = parentDir + "\\packs";
    candidates[candCount++] = baseDir;
    WriteLog("Pack directory candidates (checked in this order, all resolved from the NSM.exe location):");
    for (int c = 0; c < candCount; ++c) WriteLog("  candidate " + to_string(c + 1) + ": " + candidates[c]);

    const char* packNames[7] = { "mp1.pack", "mp2.pack", "mp3.pack", "mp4.pack", "mp5.pack", "mp6.pack", "mp7.pack" };
    const long long knownSize[7] = { 226614288LL, 59032608LL, 41842720LL, 47905824LL, 44633120LL, 45305888LL, 60693024LL };
    const long long MP1_STUB_MAX = 10LL * 1024 * 1024;   // same threshold as the wrapper's pack guard

    // ---- validate ALL SEVEN packs in a candidate BEFORE selecting it ----
    string selFull, selStub;             // first complete candidate (full mp1 / stub mp1)
    int bestPresent = -1; string bestDir, bestMissing;
    for (int c = 0; c < candCount; ++c) {
        const string& cand = candidates[c];
        WIN32_FILE_ATTRIBUTE_DATA fad;
        bool dirExists = GetFileAttributesExA(cand.c_str(), GetFileExInfoStandard, &fad)
                         && (fad.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY);
        if (!dirExists) {
            WriteLog("  candidate " + cand + " : directory does not exist (Windows error " + to_string(GetLastError()) + ")");
            continue;
        }
        int present = 0; bool mp1Stub = false; string missing;
        for (int i = 0; i < 7; ++i) {
            string p = cand + "\\" + packNames[i];
            NsmPackProbe pr = NsmProbeFile(p);
            if (pr.exists) {
                ++present;
                string note = "  pack check: " + p + " : present, " + to_string(pr.size) + " B";
                if (pr.size != knownSize[i])
                    note += " (release pack is " + to_string(knownSize[i]) + " B - content is validated during decryption)";
                if (i == 0 && pr.size < MP1_STUB_MAX) { note += " [STUB - cannot provide libs\\libce2.dll]"; mp1Stub = true; }
                WriteLog(note);
            } else {
                if (!missing.empty()) missing += "; ";
                missing += string(packNames[i]) + " at " + p + " (Windows error " + to_string(pr.err) + NsmErrHint(pr.err) + ")";
                WriteLog("  pack check: " + p + " : NOT FOUND (Windows error " + to_string(pr.err) + NsmErrHint(pr.err) + ")");
            }
        }
        WriteLog("  candidate " + cand + " : " + to_string(present) + "/7 packs present" + (mp1Stub ? " (mp1.pack is the stub)" : ""));
        if (present == 7) {
            if (!mp1Stub && selFull.empty()) selFull = cand;
            if (mp1Stub && selStub.empty()) selStub = cand;
        }
        if (present > bestPresent) { bestPresent = present; bestDir = cand; bestMissing = missing; }
    }

    string selDir = selFull.empty() ? selStub : selFull;      // prefer a candidate with the FULL mp1
    bool selMp1Stub = !selFull.empty() ? false : !selStub.empty();

    if (selDir.empty()) {
        WriteLog("ERROR: no candidate directory contains all 7 game packs.");
        for (int c = 0; c < candCount; ++c) NsmLogDirListing(candidates[c]);
        NsmLogDirListing(baseDir);
        string detail;
        if (bestPresent > 0) {
            detail = "Game packs incomplete in \"" + bestDir + "\" - only " + to_string(bestPresent) + " of the 7 pack files were found.\nMissing: " + bestMissing;
        } else {
            string candList;
            for (int c = 0; c < candCount; ++c) { if (!candList.empty()) candList += "\n  "; candList += candidates[c]; }
            detail = "No game packs (mp1.pack - mp7.pack) were found. Checked folders:\n  " + candList;
        }
        detail += "\n\nPlace all seven pack files (mp1.pack - mp7.pack) into the \"packs\" folder next to NSM.exe:\n" + baseDir + "\\packs\nEvery checked path, file size and folder listing is in connect.log.";
        if (failReasonOut) *failReasonOut = detail;
        return false;
    }
    WriteLog("Selected pack directory: " + selDir + " (all 7 packs present" +
             (selMp1Stub ? "; mp1.pack is the small STUB - the full pack downloads in the background" : "") + ")");

    // ---- extract ALL packs from the ONE selected directory ----
    CreateDirectoryA(targetDir.c_str(), NULL);
    SHCreateDirectoryExA(NULL, (targetDir + "\\logs").c_str(), NULL);
    CreateDirectoryA((targetDir + "\\proxy").c_str(), NULL);
    CreateDirectoryA((targetDir + "\\cef").c_str(), NULL);
    CreateDirectoryA((targetDir + "\\cef\\locales").c_str(), NULL);
    CreateDirectoryA((targetDir + "\\libs").c_str(), NULL);
    CreateDirectoryA((targetDir + "\\cache").c_str(), NULL);
    CreateDirectoryA((targetDir + "\\backup").c_str(), NULL);

    for (int i = 1; i <= 7; ++i) {
        string packName = "mp" + to_string(i);
        string mpPackPath = selDir + "\\" + packName + ".pack";
        string mpDllPath = targetDir + "\\" + packName + "_ext.dll";
        string why;
        if (!DecryptDataAES(mpPackPath, mpDllPath, &why)) {
            WriteLog("FAILED: " + packName + ".pack could not be decrypted: " + why);
            if (failReasonOut) *failReasonOut =
                "Extraction failed - " + packName + ".pack could not be decrypted.\nReason: " + why +
                "\nPack file: " + mpPackPath +
                "\n\nThe file is corrupt, truncated or not a valid NSM pack. Re-download it (github.com/platinum-cfx/NSM -> Code -> Download ZIP, or Releases -> game-packs) and place it in:\n" + selDir;
            return false;
        }
        HMODULE hMp = LoadLibraryA(mpDllPath.c_str());
        if (!hMp) {
            DWORD le = GetLastError();
            WriteLog("FAILED: extractor DLL for " + packName + ".pack did not load (Windows error " + to_string(le) + ")");
            DeleteFileA(mpDllPath.c_str());
            if (failReasonOut) *failReasonOut =
                "Extraction failed - the extractor for " + packName + ".pack could not be loaded (Windows error " + to_string(le) +
                (le == ERROR_ACCESS_DENIED ? " - access denied: check antivirus" : "") + ").\nPack file: " + mpPackPath +
                "\n\nThe pack is corrupt or incomplete. Re-download it and place it in:\n" + selDir;
            return false;
        }
        typedef void (*RunExtractorFunc)(const char*);
        RunExtractorFunc runExtractor = (RunExtractorFunc)GetProcAddress(hMp, "RunExtractor");
        if (!runExtractor) {
            WriteLog("FAILED: extractor DLL for " + packName + ".pack has no RunExtractor entry point");
            FreeLibrary(hMp);
            DeleteFileA(mpDllPath.c_str());
            if (failReasonOut) *failReasonOut =
                "Extraction failed - the extractor for " + packName + ".pack is invalid (entry point 'RunExtractor' missing).\nPack file: " + mpPackPath +
                "\n\nRe-download the pack and place it in:\n" + selDir;
            return false;
        }
        runExtractor(targetDir.c_str());
        FreeLibrary(hMp);
        DeleteFileA(mpDllPath.c_str());
        WriteLog("pack " + packName + ".pack extracted OK from " + selDir);
    }
    WriteLog("Packs successfully extracted.");

    // ---- verify the extracted payload against the manifest ----
    int checked = 0;
    string uncovered;
    int uncoveredCount = 0;
    bool libce2MissingStub = false;
    for (int i = 0; i < manifestSize; ++i) {
        string relPath = g_Manifest[i].relPath;
        if (relPath.find("skin.bin") != string::npos) continue;
        ++checked;
        string filePath = targetDir + relPath;
        if (GetFileSizeStr(filePath) == g_Manifest[i].expectedSize) continue;
        string srcPath = NsmRuntimeSourcePath(baseDir, relPath);
        if (!srcPath.empty()) {
            WriteLog("  pending: " + relPath + " is not in the runtime folder yet - it will install from " + srcPath);
            continue;
        }
        if (relPath.find("libce2.dll") != string::npos && selMp1Stub) {
            libce2MissingStub = true;
            WriteLog("  libs\\libce2.dll is NOT present: mp1.pack is the small stub and cannot provide it");
            continue;
        }
        ++uncoveredCount;
        if (uncovered.size() < 400) uncovered += relPath + " (expected " + to_string(g_Manifest[i].expectedSize) + " B)\n";
    }
    if (libce2MissingStub && uncoveredCount == 0) {
        WriteLog("Post-extraction verification: libs\\libce2.dll is unavailable - mp1.pack is the STUB.");
        WriteLog("The full mp1.pack (226,614,288 B) downloads automatically in the background (see nsm-embed-debug.log: 'pack: mp1.pack upgraded').");
        if (failReasonOut) *failReasonOut =
            "SOFT:The game file libs\\libce2.dll is not available yet.\n\n" + selDir + "\\mp1.pack is the small STUB pack - it cannot provide libce2.dll.\n\nThe full mp1.pack (226,614,288 B) is downloading automatically in the background. Press Connect again once nsm-embed-debug.log shows 'pack: mp1.pack upgraded' (usually within a minute).\n\nManual fix: download mp1.pack from github.com/platinum-cfx/NSM/releases (game-packs) and place it in:\n" + selDir;
        return false;
    }
    if (uncoveredCount > 0) {
        WriteLog("Post-extraction verification FAILED: " + to_string(uncoveredCount) + " of " + to_string(checked) + " required files are missing and no local source can provide them:\n" + uncovered);
        if (failReasonOut) *failReasonOut =
            "Extraction incomplete - " + to_string(uncoveredCount) + " required game file(s) are still missing after extracting all 7 packs (full list in connect.log).\nThe packs in:\n" + selDir + "\nmay be corrupt or from a different NSM version. Re-download them.";
        return false;
    }
    WriteLog("Post-extraction verification passed: all " + to_string(checked) + " required files present (or installable from the local altv-runtime).");
    return true;
}'''

start_anchor = 'bool EnsureGameFilesReady(const string& baseDir, const string& targetDir) {'
end_anchor = '    WriteLog("Packs successfully extracted.");\n    return true;\n}'
si = src.find(start_anchor)
ei = src.find(end_anchor)
if si < 0 or ei < 0 or ei < si:
    print("ANCHOR FAIL: EnsureGameFilesReady bounds")
    sys.exit(1)
src = src[:si] + NEWFUNC + src[ei + len(end_anchor):]
print("ok: EnsureGameFilesReady replaced")

# ---------------- 3. call site: reason-driven dialog ----------------
rep('''        NsmSetDetail("preparing game files");
        // Ensure game engine packs are ready
        if (!EnsureGameFilesReady(baseDir, targetDir)) {
            MessageBoxW(
                NULL,
                L"GTAMP game packs (packs/mp1.pack) not found in launcher directory.\\nPlease place NSM.exe inside your GTAMP folder to launch GTA V.",
                L"NSM Launcher",
                MB_ICONINFORMATION | MB_OK
            );''',
    '''        NsmSetDetail("preparing game files");
        // Ensure game engine packs are ready; on failure show the EXACT cause
        // (missing pack file / decryption / extractor / missing runtime files)
        string packFailReason;
        if (!EnsureGameFilesReady(baseDir, targetDir, &packFailReason)) {
            bool soft = packFailReason.rfind("SOFT:", 0) == 0;
            if (soft) packFailReason = packFailReason.substr(5);
            if (packFailReason.empty()) packFailReason = "Preparing the game files failed. Details are in the log.";
            string msg = packFailReason + "\\n\\nFull details (every checked path, file size and folder listing) are in:\\n" + g_logFilePath;
            NsmMessageBox(msg, "NSM - Game Files Error", (soft ? MB_ICONWARNING : MB_ICONERROR) | MB_OK);''',
    "call site dialog")

# remove the old libce2 WARNING block (subsumed by the verification above)
rep('''        // The one file the STUB mp1.pack cannot provide: libs\\libce2.dll.
        // Without it the alt:V client exits with 0xC0000005 before starting
        // GTA V. Warn loudly instead of letting the client crash silently.
        if (GetFileAttributesA((targetDir + "\\\\libs\\\\libce2.dll").c_str()) == INVALID_FILE_ATTRIBUTES) {
            WriteLog("WARNING: libs\\\\libce2.dll is missing - the small stub mp1.pack cannot provide it.");
            WriteLog("The full mp1.pack downloads in the background once NSM starts (see nsm-embed-debug.log:");
            WriteLog("'pack: mp1.pack upgraded' - then press Connect again). Manual: github.com/platinum-cfx/NSM/releases -> game-packs.");
        }

''', '', "old libce2 warning block removed")

# ---------------- 4. startup logging: exe path, baseDir, CWD, build id ----------------
rep('    WriteLog("Starting connect.exe / NSM.exe");',
    '''    WriteLog("Starting connect.exe / NSM.exe");
#ifdef NSM_BUILD_ID
    WriteLog("NSM build: " NSM_BUILD_ID);
#endif
    {
        char nsmExePath[MAX_PATH] = {0};
        char nsmCwd[MAX_PATH] = {0};
        GetModuleFileNameA(NULL, nsmExePath, MAX_PATH);
        GetCurrentDirectoryA(MAX_PATH, nsmCwd);
        WriteLog(string("NSM.exe path: ") + nsmExePath);
        WriteLog("baseDir (folder of NSM.exe - ALL pack lookups use this, never the working directory): " + baseDir);
        WriteLog("current working directory (informational only): " + string(nsmCwd));
    }''',
    "startup path logging")

open(PATH, "wb").write(src.replace("\n", "\r\n").encode("latin-1"))
print("patched:", PATH, len(src), "chars")
