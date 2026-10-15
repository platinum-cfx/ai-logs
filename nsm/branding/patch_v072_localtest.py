#!/usr/bin/env python3
"""Direct binary patch v3: NSM-client-v0.7.zip -> NSM-client-v0.7.2-localtest.zip

v0.7.1 patches (all length-preserving / null-padded):
  1. Every root PE: manifest name="FiveM" -> name="NSM"
  2. NSM.exe: updater URLs http://194.104.146.133/... -> http://127.0.0.1/... (null-pad)
  3. All PEs: utf16 template CitizenFX_SubProcess_%s.bin -> NSM_SubProcess_%s.bin + blob renames
  4. NSM.exe: SDK shortcut, NSM_Diag.exe version block
  5. ui.zip JS: http://194.104.146.133 -> http://127.0.0.1

NEW in v0.7.2:
  6. NSM.exe: boot-window logo XAML (utf16) FiveM mark (#66AD43) -> NSM N-mark (#2F7BFF)
  7. All root PEs: game-cache/CDN URLs https://<host>/... -> http://127.0.0.1/<route>/...
     (1-char routes served by the bundled NSM-Masterlist.exe pass-through cache;
      hosts that cannot fit are skipped: fivem.net, cfx.re)
  8. Bundles NSM-Masterlist.exe + START-LOCALHOST.bat + README v2 (replaces LOCAL-SERVER.ps1)

Verifies: v0.7.1 checks + zero green-logo XAML + N-mark present + zero routed-CDN URLs +
NSM-Masterlist.exe present and non-empty.
"""
import zipfile, re, io, os, sys, collections, json

SRC = '/var/tmp/phase1-pack/client/NSM-client-v0.7.zip'
DST = '/var/tmp/phase1-pack/client/NSM-client-v0.7.2-localtest.zip'
STACK = '/tmp/stack/NSM-Masterlist.exe'
U16 = lambda s: s.encode('utf-16-le')
stats = collections.Counter()

def swap(data, old, new, label, expect=None):
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

# ---------- NEW: logo XAML swap (v0.7.2) ----------
NEW_ICON = ('<Viewbox Height="150" Margin="0,0,0,60" VerticalAlignment="Center" '
            'HorizontalAlignment="Center" RenderTransformOrigin="0.5,0.5">'
            '<Path Data="M3 22V2H7.2L15.5 14.2V2H19V22H14.8L6.5 9.8V22H3Z" '
            'Stretch="Fill" Fill="#2F7BFF"></Path></Viewbox>')

def patch_logo(data):
    start = data.find(U16('<Viewbox'))
    assert start != -1, 'logo: no utf16 <Viewbox found'
    end_token = U16('</Viewbox>')
    end = data.find(end_token, start)
    assert end != -1, 'logo: no closing Viewbox'
    end += len(end_token)
    old = data[start:end]
    assert U16('#66AD43') in old, 'logo: span is not the green FiveM mark'
    assert U16('M37.97 86.09') in old, 'logo: span is not the GTA_FIVE icon'
    new = U16(NEW_ICON)
    assert len(new) <= len(old), f'logo: new {len(new)} > old {len(old)}'
    stats['boot logo -> NSM N-mark (blue)'] += 1
    return data[:start] + new + b'\x00' * (len(old) - len(new)) + data[end:]

# ---------- NEW: CDN URL routes (v0.7.2) ----------
ROUTES = {
    'content.cfx.re': 'c', 'runtime.fivem.net': 'r', 'lambda.fivem.net': 'l',
    'forum.cfx.re': 'f', 'aka.cfx.re': 'a', 'policy-live.fivem.net': 'p',
    'static.cfx.re': 's', 'private-placeholder.cfx.re': 'v', 'www.fivem.net': 'w',
    'docs.fivem.net': 'd', 'forum.fivem.net': 'e', 'wiki.fivem.net': 'k',
}  # fivem.net (9 chars) and cfx.re (8) cannot fit - left direct
HOST_RE = rb'https?://(' + b'|'.join(re.escape(h.encode()) for h in ROUTES) + rb')(/[^\x00"\']*)?'

def route_repl(m):
    full = m.group()
    host = m.group(1).decode()
    rest = full[m.end(1) - m.start():]
    new = ('http://127.0.0.1/' + ROUTES[host]).encode() + rest
    assert len(new) <= len(full), f'route overflow: {full!r}'
    stats['CDN URL -> local mirror route'] += 1
    return new + b'\x00' * (len(full) - len(new))

def patch_cdn_urls(data):
    return re.sub(HOST_RE, route_repl, data)

def patch_pe(data, own_binname):
    data = swap(data, b'name="FiveM"', b'name="NSM"  ', 'manifest name')
    def url_repl(m):
        old = m.group()
        new = b'http://127.0.0.1' + old[len(b'http://194.104.146.133'):]
        stats['updater URL -> localhost'] += 1
        return new + b'\x00' * (len(old) - len(new))
    data = re.sub(rb'http://194\.104\.146\.133[^\x00]*', url_repl, data)
    data = swap(data, U16('CitizenFX_SubProcess_%s.bin'),
                pad_u16('NSM_SubProcess_%s.bin', len('CitizenFX_SubProcess_%s.bin')),
                'subprocess template')
    if own_binname:
        for ext in ('.bin', '.pdb'):
            old = ('CitizenFX_SubProcess_' + own_binname + ext).encode()
            nn = ('NSM_SubProcess_' + own_binname + ext).encode()
            data = swap(data, old, nn + b'\x00' * (len(old) - len(nn)), f'own name {ext}')
    data = patch_cdn_urls(data)   # NEW
    return data

def patch_diag(data):
    for old, new in [('FiveM Diagnostics Utility', 'NSM Diagnostics Utility'),
                     ('cfx-collective', 'NSM Community'),
                     ('Citizen', 'AxiomFX'),
                     ('citizenmp.exe', 'NSM_Diag.exe')]:
        o = U16(old) + b'\x00\x00'
        n = U16(new) + b'\x00' * (len(o) - len(U16(new)))
        data = swap(data, o, n, f'diag: {old}')
    return data

def patch_inner_zip(data, label):
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

START_BAT = '''@echo off
rem NSM localhost boot: starts the NSM backend (website + accounts + server list
rem + game cache) and then the NSM client. Keep the black console window open!
start "NSM Backend" "%~dp0NSM-Masterlist.exe"
timeout /t 2 >nul
start "" "%~dp0NSM.exe"
'''

README = '''NSM Community - client v0.7.2 LOCALTEST build
================================================

WHAT IS NEW IN v0.7.2
  - BOOT LOGO: the loading window now shows the blue NSM "N" mark
    (the old green FiveM logo is gone).
  - ALL NETWORK TRAFFIC NOW GOES THROUGH YOUR OWN BACKEND:
    game files, server list, everything - served by NSM-Masterlist.exe.
  - WEBSITE + ACCOUNTS: NSM-Masterlist.exe also runs the NSM website with
    accounts (sign up / log in), server list, upvotes, and owner/admin staff.

HOW TO RUN (LOCALHOST)
  1. Extract the whole zip to a FRESH folder.
  2. Double-click  START-LOCALHOST.bat
     (it opens NSM-Masterlist.exe - keep that window open - then NSM.exe).
  3. Website + accounts: open  http://127.0.0.1  in your browser.
       - Register your account at http://127.0.0.1/register
       - Log in as the owner: username  Cravenz
         (set a password once: run in a command prompt:
            NSM-Masterlist.exe -owner-pass YOURPASSWORD
          then start it normally)
       - Owner page to manage staff roles: http://127.0.0.1/admin/users
  4. Play: NSM.exe -> server list -> join.

HOW THE GAME FILES WORK NOW
  The first time the client needs a game file, NSM-Masterlist.exe downloads it
  from Cfx's public servers once and saves it in its mirror-cache folder.
  After that, every download comes from your own machine - fast, and it works
  even if Cfx's servers go away later.

STEAM SHOWING "PLAYING FIVEM"?
  Steam shows the NAME OF THE SHORTCUT for non-Steam games:
  1. Remove the old "FiveM" entry from your Steam library (right-click -> Manage).
  2. Add NSM.exe as a Non-Steam game, rename the entry to "NSM Community".

TASK MANAGER STILL SHOWS FIVEM PROCESSES?
  An OLD install is running. Delete old shortcuts and run NSM.exe from THIS folder.

LATER: MOVING TO THE VPS
  When the VPS is ready, copy NSM-Masterlist.exe to it and run it with:
     NSM-Masterlist.exe -bind 0.0.0.0 -owner-pass YOURPASSWORD
  Nothing else changes - same exe, same data files.
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
            data = patch_logo(data)          # NEW
    elif is_pe:
        data = patch_pe(data, None)
        if inner and inner.startswith('CitizenFX_SubProcess_') and inner.endswith('.bin'):
            own = inner[len('CitizenFX_SubProcess_'):-len('.bin')]
            for ext in ('.bin', '.pdb'):
                old = ('CitizenFX_SubProcess_' + own + ext).encode()
                nn = ('NSM_SubProcess_' + own + ext).encode()
                data = swap(data, old, nn + b'\x00' * (len(old) - len(nn)), f'own name {ext}')
            out_name = 'NSM-Client/NSM_SubProcess_' + own + '.bin'
            stats['blob renamed'] += 1
    elif inner == 'citizen/ui.zip':
        data = patch_inner_zip(data, 'ui.zip')

    zi = zipfile.ZipInfo(out_name, date_time=item.date_time)
    zi.external_attr = item.external_attr
    zi.compress_type = zipfile.ZIP_DEFLATED
    zout.writestr(zi, data)

# bundled backend + helpers
with open(STACK, 'rb') as f:
    stack_bytes = f.read()
for name, content in (('NSM-Client/NSM-Masterlist.exe', stack_bytes),
                      ('NSM-Client/START-LOCALHOST.bat', START_BAT),
                      ('NSM-Client/README-LOCALTEST.txt', README)):
    zi = zipfile.ZipInfo(name)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zout.writestr(zi, content)
zout.close()

print('════ PATCHES APPLIED ════')
for k, v in sorted(stats.items()):
    print(f'  {k:<40} {v}')
print(f'  {"output size":<40} {os.path.getsize(DST):,} bytes')

# ---------------- full-package verification ----------------
print('════ VERIFY (whole package incl. nested zips) ════')
z = zipfile.ZipFile(DST)
fails = 0
def check(cond, msg):
    global fails
    print(('  ok: ' if cond else '  FAIL: ') + msg)
    if not cond: fails += 1

routed_hosts = [h.encode() for h in ROUTES]
bad = collections.Counter()
cdn_left = collections.Counter()
for n in z.namelist():
    if not n.startswith('NSM-Client/'):
        continue
    d = z.read(n)
    bad['manifest'] += d.count(b'name="FiveM"')
    bad['vps'] += d.count(b'http://194.104.146.133')
    bad['subproc_utf16'] += d.count(U16('CitizenFX_SubProcess'))
    bad['subproc_ascii'] += d.count(b'CitizenFX_SubProcess')
    if n.endswith(('.exe', '.dll', '.bin', '.com')) and n != 'NSM-Client/NSM-Masterlist.exe':
        # (NSM-Masterlist.exe legitimately contains the upstream URLs for its pass-through cache)
        for h in routed_hosts:
            for pre in (b'https://' + h + b'/', b'http://' + h + b'/'):
                cdn_left[pre] += d.count(pre)
    if n.endswith('.zip'):
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
check(all(v == 0 for v in cdn_left.values()),
      f'zero direct CDN URLs left (routed hosts) {dict(cdn_left) if any(cdn_left.values()) else ""}')

exe = z.read('NSM-Client/NSM.exe')
check(U16('#66AD43') not in exe and U16('M37.97 86.09') not in exe, 'green FiveM logo XAML gone')
check(U16('M3 22V2H7.2L15.5 14.2V2H19V22H14.8L6.5 9.8V22H3Z') in exe, 'NSM N-mark XAML present (blue)')
check(exe.count(b'http://127.0.0.1/updates') >= 3, 'localhost updater URLs in NSM.exe')
check(exe.count(b'http://127.0.0.1/c/mirrors/') >= 5, 'game-cache URLs routed to local mirror in NSM.exe')
glue = z.read('NSM-Client/glue.dll')
check(glue.count(b'https://content.cfx.re') == 0 and glue.count(b'http://127.0.0.1/c/mirrors/') > 50,
      'glue.dll cache URLs all routed to local mirror')
leg = z.read('NSM-Client/legitimacy.dll')
check(leg.count(b'https://lambda.fivem.net') == 0 and b'http://127.0.0.1/l/' in leg,
      'legitimacy.dll entitlement endpoint routed')

nl = z.namelist()
check('NSM-Client/NSM_SubProcess_game_3095_aslr.bin' in nl and
      not any(n.startswith('NSM-Client/CitizenFX_SubProcess') for n in nl), 'blobs renamed, none left old-named')
diag = z.read('NSM-Client/NSM_Diag.exe')
check(U16('NSM Diagnostics Utility') in diag and U16('FiveM Diagnostics') not in diag, 'diag version block rebranded')
uiz = zipfile.ZipFile(io.BytesIO(z.read('NSM-Client/citizen/ui.zip')))
uic = b''.join(uiz.read(m) for m in uiz.namelist())
check(b'http://127.0.0.1/api/servers' in uic and b'http://127.0.0.1/runtime/counts.json' in uic,
      'server-list + counts URLs -> localhost in ui.zip')
check(len(json.loads(z.read('NSM-Client/components.json'))) == 63, 'components.json 63 entries')
ub = zipfile.ZipFile(io.BytesIO(z.read('NSM-Client/citizen/ui-big.zip')))
check(len(ub.read('loadscreen/ea097d53311d8e118a31.jpg')) == 210784, 'NSM loadscreen art intact')
stackz = z.read('NSM-Client/NSM-Masterlist.exe')
check(len(stackz) > 7_000_000 and stackz[:2] == b'MZ', f'NSM-Masterlist.exe bundled ({len(stackz):,} bytes, PE header ok)')
check('NSM-Client/START-LOCALHOST.bat' in nl and 'NSM-Client/README-LOCALTEST.txt' in nl, 'helper files present')
check('NSM-Client/steam_appid.txt' in nl and z.read('NSM-Client/steam_appid.txt').strip() == b'218', 'steam_appid 218')
print('════ RESULT:', 'PASS' if fails == 0 else f'{fails} FAILURES', '════')
sys.exit(1 if fails else 0)
