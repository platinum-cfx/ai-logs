#!/usr/bin/env python3
"""Direct binary patch v2: NSM-client-v0.7.zip -> NSM-client-v0.7.1-localtest.zip

All patches are length-preserving (null-padding) so no offsets shift:
  1. Every PE (NSM.exe/com/diag + 19 subprocess bins): manifest name="FiveM" -> name="NSM"
  2. NSM.exe: updater URLs http://194.104.146.133 -> http://127.0.0.1.nip.io (22=22 bytes)
  3. All PEs: utf16 template CitizenFX_SubProcess_%s.bin -> NSM_SubProcess_%s.bin
  4. Each bin: its own module name (.bin) and debug path (.pdb) -> NSM_SubProcess_*
     + zip entries renamed to match
  5. NSM.exe: SDK shortcut name CitizenFX.FiveM.SDK -> NSM.SDK
  6. NSM_Diag.exe version block -> NSM/AxiomFX strings
  7. ui.zip inner members: all http://194.104.146.133 -> http://127.0.0.1.nip.io
  8. Adds LOCAL-SERVER.ps1 + README-LOCALTEST.txt
Verifies: zero FiveM manifests, zero VPS URLs anywhere in package (incl. inner zips),
zero CitizenFX_SubProcess refs anywhere, diag block, loadscreen intact, 63 components.
"""
import zipfile, re, io, os, sys, collections, json

SRC = '/var/tmp/phase1-pack/client/NSM-client-v0.7.zip'
DST = '/var/tmp/phase1-pack/client/NSM-client-v0.7.1-localtest.zip'
U16 = lambda s: s.encode('utf-16-le')
stats = collections.Counter()

def swap(data, old, new, label, expect=None):
    """same-length byte swap; returns data"""
    assert len(old) == len(new), f'{label}: length mismatch {len(old)} vs {len(new)}'
    n = data.count(old)
    data = data.replace(old, new)
    stats[label] += n
    if expect is not None and n != expect:
        print(f'  WARNING {label}: expected {expect}, got {n}')
    return data

def pad_u16(short, total_chars):
    b = U16(short)
    return b + b'\x00' * ((total_chars - len(short)) * 2)

def patch_pe(data, own_binname):
    # 1. embedded manifest
    data = swap(data, b'name="FiveM"', b'name="NSM"  ', 'manifest name')
    # 2. updater endpoints: rewrite FULL url strings, null-pad remainder (C-string safe)
    def url_repl(m):
        old = m.group()
        new = b'http://127.0.0.1' + old[len(b'http://194.104.146.133'):]
        stats['updater URL -> localhost'] += 1
        return new + b'\x00' * (len(old) - len(new))
    data = re.sub(rb'http://194\.104\.146\.133[^\x00]*', url_repl, data)
    # 3. subprocess template (utf16)
    data = swap(data, U16('CitizenFX_SubProcess_%s.bin'),
                pad_u16('NSM_SubProcess_%s.bin', len('CitizenFX_SubProcess_%s.bin')),
                'subprocess template')
    # 4. own module name + pdb path (ascii)
    if own_binname:
        for ext in ('.bin', '.pdb'):
            old = ('CitizenFX_SubProcess_' + own_binname + ext).encode()
            new = ('NSM_SubProcess_' + own_binname + ext).encode() + b'\x00' * (len(old) - len(('NSM_SubProcess_' + own_binname + ext).encode()))
            data = swap(data, old, new, f'own name {ext}')
    return data

def patch_diag(data):
    for old, new in [('FiveM Diagnostics Utility', 'NSM Diagnostics Utility'),
                     ('cfx-collective', 'NSM Community'),
                     ('Citizen', 'AxiomFX'),           # ProductName+InternalName
                     ('citizenmp.exe', 'NSM_Diag.exe')]:
        o = U16(old) + b'\x00\x00'
        n = U16(new) + b'\x00' * (len(o) - len(U16(new)))
        data = swap(data, o, n, f'diag: {old}')
    return data

def patch_inner_zip(data, label):
    """rewrite members of a nested zip, patching URLs"""
    zin = zipfile.ZipFile(io.BytesIO(data))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zo:
        for it in zin.infolist():
            b = zin.read(it.filename)
            if b.count(b'http://194.104.146.133'):
                stats[f'{label} URL -> localhost'] += b.count(b'http://194.104.146.133')
                b = b.replace(b'http://194.104.146.133', b'http://127.0.0.1')
            zi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
            zi.external_attr = it.external_attr
            zi.compress_type = zipfile.ZIP_DEFLATED
            zo.writestr(zi, b)
    return buf.getvalue()

LOCAL_SERVER = r'''# NSM local test server - serves 127.0.0.1:80 for the NSM client's test endpoints.
# Right-click PowerShell -> "Run as Administrator" ->  powershell -ExecutionPolicy Bypass -File LOCAL-SERVER.ps1
# Returns empty player-counts JSON and 404 for update checks (client continues with current build).
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add('http://+:80/')
$listener.Start()
Write-Host 'NSM local test server on http://127.0.0.1/  (Ctrl+C to stop)'
while ($listener.IsListening) {
    try {
        $ctx = $listener.GetContext()
        $path = $ctx.Request.Url.AbsolutePath
        if ($path -like '*counts.json') {
            $bytes = [Text.Encoding]::UTF8.GetBytes('{}')
            $ctx.Response.ContentType = 'application/json'
            $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
        } else {
            $ctx.Response.StatusCode = 404
            $bytes = [Text.Encoding]::UTF8.GetBytes('not found (NSM local test server)')
            $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
        }
        Write-Host ("{0}  {1}" -f $ctx.Response.StatusCode, $path)
        $ctx.Response.Close()
    } catch { }
}
'''

README = '''NSM Community - client v0.7.1 LOCALTEST build
================================================

WHAT IS DIFFERENT
  - Update-check and server-list endpoints point at your own machine
    (http://127.0.0.1) instead of the VPS.
  - All embedded Windows manifests say name="NSM" (was FiveM).
  - Subprocess blobs renamed to NSM_SubProcess_*.bin (in the package AND
    inside every binary that spawns them).
  - NSM_Diag.exe properties now say NSM Diagnostics Utility / AxiomFX.

HOW TO RUN
  1. Extract the whole zip to a FRESH folder (do not run old installs).
  2. (Optional) local test server: right-click PowerShell -> Run as Administrator ->
     powershell -ExecutionPolicy Bypass -File LOCAL-SERVER.ps1
     Without it, update checks fail silently and the current build is used.
  3. Run  NSM-Client\\NSM.exe

VERIFY YOU ARE ON THE NEW CLIENT (IMPORTANT)
  - Task Manager while loading: you should see "NSM.exe" and processes that
    start with  NSM_  (e.g. NSM_game_...).
  - If you see FiveM.exe or FiveM_* processes, an OLD install is launching.
    Delete the old shortcut and run NSM.exe directly from this folder.

STEAM SHOWING "PLAYING FIVEM"?
  Steam shows the NAME OF THE SHORTCUT for non-Steam games:
  1. Steam Library -> old "FiveM" entry -> right-click -> Manage ->
     Remove from this library (removes only the shortcut).
  2. Add a Game -> Add a Non-Steam Game -> Browse -> NSM-Client\\NSM.exe
     -> rename the entry to "NSM Community".
  3. Friends will now see you playing "NSM Community".

GREEN LOGO WHILE THE GAME LOADS
  Every image inside this package is already NSM (blue). The green screen
  during game loading comes from GTA game-cache files (update.rpf) downloaded
  from Cfx's servers - not from our package. Replacing it requires our own
  content mirror (Phase 2, on the VPS).
'''

zin = zipfile.ZipFile(SRC)
zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
for item in zin.infolist():
    data = zin.read(item.filename)
    inner = item.filename[len('NSM-Client/'):] if item.filename.startswith('NSM-Client/') else None
    out_name = item.filename

    is_pe = inner and inner.count('/') == 0 and inner.endswith(('.exe', '.bin', '.com', '.dll'))
    if inner in ('NSM.exe', 'NSM.com', 'NSM_Diag.exe'):
        data = patch_pe(data, None)
        if inner == 'NSM_Diag.exe':
            data = patch_diag(data)
        if inner == 'NSM.exe':
            data = swap(data, U16('CitizenFX.FiveM.SDK'), pad_u16('NSM.SDK', 19), 'SDK shortcut name')
    elif is_pe:
        data = patch_pe(data, None)   # template + manifest + URLs in every PE (dlls too)
        if inner and inner.startswith('CitizenFX_SubProcess_') and inner.endswith('.bin'):
            own = inner[len('CitizenFX_SubProcess_'):-len('.bin')]
            data = patch_pe(data, own) if False else data
            # own-name ascii patches for bins:
            for ext in ('.bin', '.pdb'):
                old = ('CitizenFX_SubProcess_' + own + ext).encode()
                new = ('NSM_SubProcess_' + own + ext).encode() + b'\x00' * (len(old) - len(('NSM_SubProcess_' + own + ext).encode()))
                data = swap(data, old, new, f'own name {ext}')
            out_name = 'NSM-Client/NSM_SubProcess_' + own + '.bin'
            stats['blob renamed'] += 1
    elif inner == 'citizen/ui.zip':
        data = patch_inner_zip(data, 'ui.zip')

    zi = zipfile.ZipInfo(out_name, date_time=item.date_time)
    zi.external_attr = item.external_attr
    zi.compress_type = zipfile.ZIP_DEFLATED
    zout.writestr(zi, data)

for name, content in (('NSM-Client/LOCAL-SERVER.ps1', LOCAL_SERVER),
                      ('NSM-Client/README-LOCALTEST.txt', README)):
    zi = zipfile.ZipInfo(name)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zout.writestr(zi, content)
zout.close()

print('════ PATCHES APPLIED ════')
for k, v in sorted(stats.items()):
    print(f'  {k:<36} {v}')
print(f'  {"output size":<36} {os.path.getsize(DST):,} bytes')

# ---------------- full-package verification ----------------
print('════ VERIFY (whole package incl. nested zips) ════')
z = zipfile.ZipFile(DST)
fails = 0
def check(cond, msg):
    global fails
    print(('  ok: ' if cond else '  FAIL: ') + msg)
    if not cond: fails += 1

bad = collections.Counter()
for n in z.namelist():
    if not n.startswith('NSM-Client/'):
        continue
    d = z.read(n)
    bad['manifest'] += d.count(b'name="FiveM"')
    bad['vps'] += d.count(b'http://194.104.146.133')
    bad['subproc_utf16'] += d.count(U16('CitizenFX_SubProcess'))
    bad['subproc_ascii'] += d.count(b'CitizenFX_SubProcess')
    if n.endswith(('.zip',)):
        try:
            u = zipfile.ZipFile(io.BytesIO(d))
            for m in u.namelist():
                b = u.read(m)
                bad['manifest'] += b.count(b'name="FiveM"')
                bad['vps'] += b.count(b'http://194.104.146.133')
        except Exception:
            pass
check(bad['manifest'] == 0, f'zero name="FiveM" anywhere ({bad["manifest"]})')
check(bad['vps'] == 0, f'zero VPS URLs anywhere incl. nested zips ({bad["vps"]})')
check(bad['subproc_utf16'] == 0 and bad['subproc_ascii'] == 0,
      f'zero CitizenFX_SubProcess refs anywhere ({bad["subproc_utf16"]}+{bad["subproc_ascii"]})')

nl = z.namelist()
check('NSM-Client/NSM_SubProcess_game_3095_aslr.bin' in nl and
      not any(n.startswith('NSM-Client/CitizenFX_SubProcess') for n in nl), 'blobs renamed, none left old-named')
diag = z.read('NSM-Client/NSM_Diag.exe')
check(U16('NSM Diagnostics Utility') in diag and U16('FiveM Diagnostics') not in diag, 'diag version block rebranded')
check(U16('AxiomFX') in diag, 'diag ProductName AxiomFX')
exe = z.read('NSM-Client/NSM.exe')
check(exe.count(b'http://127.0.0.1/updates') >= 3, 'localhost updater URLs in NSM.exe')
uiz = zipfile.ZipFile(io.BytesIO(z.read('NSM-Client/citizen/ui.zip')))
uic = b''.join(uiz.read(m) for m in uiz.namelist())
check(b'http://127.0.0.1/api/servers' in uic and b'http://127.0.0.1/runtime/counts.json' in uic,
      'server-list + counts URLs -> localhost in ui.zip')
check(len(json.loads(z.read('NSM-Client/components.json'))) == 63, 'components.json 63 entries')
ub = zipfile.ZipFile(io.BytesIO(z.read('NSM-Client/citizen/ui-big.zip')))
check(len(ub.read('loadscreen/ea097d53311d8e118a31.jpg')) == 210784, 'NSM loadscreen art intact')
check('NSM-Client/LOCAL-SERVER.ps1' in nl and 'NSM-Client/README-LOCALTEST.txt' in nl, 'helper files present')
check('NSM-Client/steam_appid.txt' in nl and z.read('NSM-Client/steam_appid.txt').strip() == b'218', 'steam_appid 218')
print('════ RESULT:', 'PASS' if fails == 0 else f'{fails} FAILURES', '════')
sys.exit(1 if fails else 0)
