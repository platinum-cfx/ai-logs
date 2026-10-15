#!/usr/bin/env python3
# round-2 patch on top of the packfix build:
#  a. DecryptDataAES: block-size validation + retry final chunk without the
#     padding check (handles packs that are not PKCS7-padded), IV state saved
#  b. extraction loop: skip mp1.pack entirely when it is the stub
#  c. knownSize[0] = the FIXED full pack (228682672); old broken asset
#     (226614288) gets an explicit warning line
#  d. call site: WriteLog the failure reason so the log carries the full story
import sys
PATH = "connect.cpp"
src = open(PATH, "rb").read().decode("latin-1").replace("\r\n", "\n")

def rep(old, new, what):
    global src
    if src.count(old) != 1:
        print(f"ANCHOR FAIL ({src.count(old)}x): {what}")
        sys.exit(1)
    src = src.replace(old, new)
    print(f"ok: {what}")

# ---- a. DecryptDataAES: block check + padding-tolerant final chunk ----
rep('''    streampos processed = 0;
    while (processed < dataSize) {
        DWORD toRead = CHUNK_SIZE;
        if (dataSize - processed < (streampos)CHUNK_SIZE) {
            toRead = (DWORD)(dataSize - processed);
        }
        
        in.read((char*)buffer, toRead);
        DWORD bytesRead = (DWORD)in.gcount();
        BOOL isFinal = (processed + (streampos)bytesRead >= dataSize);
        
        DWORD dataLen = bytesRead;
        if (!CryptDecrypt(hKey, 0, isFinal, 0, buffer, &dataLen)) {
            if (why) *why = "decryption failed - the file is corrupt, truncated, or not a valid NSM pack (wrong key or damaged content)";
            CryptDestroyKey(hKey);
            CryptReleaseContext(hProv, 0);
            return false;
        }
        
        out.write((char*)buffer, dataLen);
        processed += bytesRead;
    }''',
    '''    if (dataSize % 16 != 0) {
        if (why) *why = "decryption failed - the encrypted data length is not a multiple of 16, so the file is truncated or corrupt";
        CryptDestroyKey(hKey);
        CryptReleaseContext(hProv, 0);
        return false;
    }

    streampos processed = 0;
    while (processed < dataSize) {
        DWORD toRead = CHUNK_SIZE;
        if (dataSize - processed < (streampos)CHUNK_SIZE) {
            toRead = (DWORD)(dataSize - processed);
        }
        
        in.read((char*)buffer, toRead);
        DWORD bytesRead = (DWORD)in.gcount();
        BOOL isFinal = (processed + (streampos)bytesRead >= dataSize);
        
        DWORD dataLen = bytesRead;
        if (!isFinal) {
            if (!CryptDecrypt(hKey, 0, FALSE, 0, buffer, &dataLen)) {
                if (why) *why = "decryption failed - the file is corrupt, truncated, or not a valid NSM pack (wrong key or damaged content)";
                CryptDestroyKey(hKey);
                CryptReleaseContext(hProv, 0);
                return false;
            }
            out.write((char*)buffer, dataLen);
        } else {
            // Final chunk: try the standard PKCS7 padding strip first. Some
            // packs (original gtamp format) are NOT PKCS7-padded - for those,
            // CryptDecrypt(Final=TRUE) fails on the last block. Retry the
            // final chunk without the padding check and keep the raw block
            // (a trailing partial block is ignored by the PE loader). The
            // IV state is saved/restored so the retry decrypts correctly.
            BYTE ivBackup[16];
            DWORD ivLen = 16;
            BYTE scratch[CHUNK_SIZE + 16];
            memcpy(scratch, buffer, bytesRead);
            if (!CryptGetKeyParam(hKey, KP_IV, ivBackup, &ivLen, 0)) ivLen = 0;
            if (CryptDecrypt(hKey, 0, TRUE, 0, buffer, &dataLen)) {
                out.write((char*)buffer, dataLen);
            } else {
                if (ivLen == 16) CryptSetKeyParam(hKey, KP_IV, ivBackup, 0);
                dataLen = bytesRead;
                if (CryptDecrypt(hKey, 0, FALSE, 0, scratch, &dataLen)) {
                    WriteLog("note: " + inputFile + " does not use standard PKCS7 padding - keeping the raw final block");
                    out.write((char*)scratch, dataLen);
                } else {
                    if (why) *why = "decryption failed - the file is corrupt, truncated, or not a valid NSM pack (wrong key or damaged content)";
                    CryptDestroyKey(hKey);
                    CryptReleaseContext(hProv, 0);
                    return false;
                }
            }
        }
        processed += bytesRead;
    }''',
    "DecryptDataAES: block check + padding-tolerant final chunk")

# ---- b. skip mp1.pack when it is the stub ----
rep('''    for (int i = 1; i <= 7; ++i) {
        string packName = "mp" + to_string(i);
        string mpPackPath = selDir + "\\\\" + packName + ".pack";
        string mpDllPath = targetDir + "\\\\" + packName + "_ext.dll";
        string why;''',
    '''    for (int i = 1; i <= 7; ++i) {
        string packName = "mp" + to_string(i);
        string mpPackPath = selDir + "\\\\" + packName + ".pack";
        string mpDllPath = targetDir + "\\\\" + packName + "_ext.dll";
        if (i == 1 && selMp1Stub) {
            // The stub is a 949 KB downloader placeholder - it cannot provide
            // libs\\libce2.dll (226 MB). Skip it: the wrapper's pack guard is
            // already downloading the full pack in the background; the
            // post-extraction verification below reports libce2 honestly.
            WriteLog("pack mp1.pack SKIPPED: it is the small stub (cannot provide libs\\\\libce2.dll) - the full pack downloads in the background");
            continue;
        }
        string why;''',
    "extraction: skip stub mp1")

# ---- c. knownSize[0] = fixed pack + old-broken-asset warning ----
rep('    const long long knownSize[7] = { 226614288LL, 59032608LL, 41842720LL, 47905824LL, 44633120LL, 45305888LL, 60693024LL };',
    '''    const long long knownSize[7] = { 228682672LL, 59032608LL, 41842720LL, 47905824LL, 44633120LL, 45305888LL, 60693024LL };
    const long long MP1_OLD_BROKEN = 226614288LL;   // old game-packs asset: encrypted with an incompatible key - can never decrypt''',
    "knownSize update + old-broken constant")

rep('''                if (i == 0 && pr.size < MP1_STUB_MAX) { note += " [STUB - cannot provide libs\\\\libce2.dll]"; mp1Stub = true; }''',
    '''                if (i == 0 && pr.size < MP1_STUB_MAX) { note += " [STUB - cannot provide libs\\\\libce2.dll]"; mp1Stub = true; }
                if (i == 0 && pr.size == MP1_OLD_BROKEN) note += " [KNOWN-BAD: the old game-packs release encrypted this pack with an incompatible key - it will be replaced automatically; see nsm-embed-debug.log]";''',
    "old-broken-asset warning at probe")

# ---- d. call site: log the failure reason ----
rep('''            bool soft = packFailReason.rfind("SOFT:", 0) == 0;
            if (soft) packFailReason = packFailReason.substr(5);
            if (packFailReason.empty()) packFailReason = "Preparing the game files failed. Details are in the log.";''',
    '''            bool soft = packFailReason.rfind("SOFT:", 0) == 0;
            if (soft) packFailReason = packFailReason.substr(5);
            if (packFailReason.empty()) packFailReason = "Preparing the game files failed. Details are in the log.";
            WriteLog("Game files preparation FAILED: " + packFailReason);''',
    "call site: log failure reason")

open(PATH, "wb").write(src.replace("\n", "\r\n").encode("latin-1"))
print("patched:", PATH, len(src), "chars")
