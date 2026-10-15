#!/usr/bin/env python3
"""
NSM Phase 1 packaging: server v0.7 + client v0.4 on release 412737383.

Real base layouts (verified 2026-10-15):
  NSM-server-v0.6.zip        -> everything under NSM-Server/ (634 files,
                                exe = nsm-server.exe, components.json 26 upstream)
  NSM-client-v0.3-preview.zip-> everything under NSM-Client/ (544 files,
                                CitizenFX.exe + citizen/ + bin/88,
                                components.json 63 sticky)

Never RETAIL: consumes only p2-* artifacts (built with CFX_DRY_RUN=true).
"""
import argparse, io, json, os, re, shutil, sys, urllib.request, zipfile

TOKEN = os.environ.get('GH_TOKEN')
if not TOKEN:
    raise RuntimeError('Set GH_TOKEN in the environment')
REPO_API = 'https://api.github.com/repos/platinum-cfx/NSM-FIVEM'
RELEASE_ID = 412737383
OLD_SERVER_ASSET = 644338212   # NSM-server-v0.7.1.zip (base for future)
OLD_CLIENT_ASSET = 644549632   # NSM-client-v0.6-preview.zip (restored, base for future)
VPS = b'194.104.146.133'
WORK = '/var/tmp/phase1-pack'
NSM_ICO = '/home/user/nsm/branding/server.ico'
NEW_DISCORD_APP = b'1560111337923805305'
OLD_DISCORD_APP = b'1473308775258525930'

def api(method, path, body=None, raw=False, headers=None):
    h = {'Authorization': f'token {TOKEN}', 'User-Agent': 'nsm-pack'}
    if not raw:
        h['Accept'] = 'application/vnd.github+json'
    if headers:
        h.update(headers)
    req = urllib.request.Request(REPO_API + path if path.startswith('/') else path,
                                 method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=h)
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return data if raw else json.loads(data or b'{}')

def download(url, dest, accept='application/octet-stream'):
    print(f'  downloading {url.split("?")[0]} -> {dest}', flush=True)
    req = urllib.request.Request(url, headers={'Authorization': f'token {TOKEN}',
                                               'User-Agent': 'nsm-pack',
                                               'Accept': accept})
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        r = opener.open(req, timeout=600)
    except urllib.error.HTTPError as e:
        loc = e.headers.get('Location')
        if e.code in (301, 302, 303, 307) and loc:
            # signed URL - must NOT send auth/accept headers to the redirect host
            r = urllib.request.urlopen(
                urllib.request.Request(loc, headers={'User-Agent': 'nsm-pack'}), timeout=600)
        else:
            raise
    with r, open(dest, 'wb') as f:
        shutil.copyfileobj(r, f)
    print(f'    {os.path.getsize(dest):,} bytes', flush=True)

def unpack_artifact(run_id, name, dest):
    arts = api('GET', f'/actions/runs/{run_id}/artifacts')['artifacts']
    for a in arts:
        if a['name'] == name and not a['expired']:
            zip_path = os.path.join(WORK, f'{name}.zip')
            if not os.path.exists(zip_path):
                # artifacts API rejects octet-stream; wants JSON accept then 302 -> signed URL
                download(a['archive_download_url'], zip_path, accept='application/vnd.github+json')
            os.makedirs(dest, exist_ok=True)
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(dest)
            print(f'  extracted -> {dest}', flush=True)
            return
    sys.exit(f'ERROR: artifact {name} not found on run {run_id}')

def check(cond, msg):
    if not cond:
        sys.exit('ASSERT FAILED: ' + msg)
    print('  ok:', msg, flush=True)

def walk_files(root):
    for r, _, files in os.walk(root):
        for f in files:
            yield os.path.join(r, f)

# ---------------------------------------------------------------------------
def build_server_v07(fxserver_run):
    print('\n=== NSM-Server v0.7 ===', flush=True)
    sdir = os.path.join(WORK, 'server')
    base_zip = os.path.join(sdir, 'NSM-server-v0.6.zip')
    os.makedirs(os.path.dirname(base_zip), exist_ok=True)
    if not os.path.exists(base_zip):
        download(f'{REPO_API}/releases/assets/{OLD_SERVER_ASSET}', base_zip)
    out = os.path.join(sdir, 'v07')
    if os.path.exists(out):
        shutil.rmtree(out)
    with zipfile.ZipFile(base_zip) as z:
        z.extractall(out)
    names_before = set(os.path.relpath(p, out).replace(os.sep, '/') for p in walk_files(out))
    print(f'  v0.6 base: {len(names_before)} files under NSM-Server/', flush=True)

    art = os.path.join(WORK, 'fxserver-art')
    if not os.path.exists(os.path.join(art, '.build-cache')):
        unpack_artifact(fxserver_run, 'p2-fxserver-output', art)
    bindir = os.path.join(art, '.build-cache', 'bin')
    check(os.path.isdir(bindir), 'artifact has .build-cache/bin')
    # fxserver artifacts nest everything under server/windows/release -
    # that subtree maps 1:1 onto the NSM-Server/ package root
    reldir = os.path.join(bindir, 'server', 'windows', 'release')
    if not os.path.isdir(reldir):
        reldir = bindir

    skip_names = {'dbg', 'CitiTest', 'lib', 'exp'}
    overlay = 0
    for src in walk_files(reldir):
        rel = os.path.relpath(src, reldir)
        parts = rel.replace(os.sep, '/').split('/')
        stems = {os.path.splitext(p)[0] for p in parts}
        if parts[-1] == 'components.json':
            pass  # handled below: overlay fixed 26-entry upstream list (e42715309c6)
        if (set(parts) | stems) & skip_names:
            continue
        rel = rel.replace(os.sep, '/')
        if rel == 'FXServer.exe':
            rel = 'nsm-server.exe'   # package name stays NSM
        dst = os.path.join(out, 'NSM-Server', rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        overlay += 1
    check(overlay > 20, f'overlaid {overlay} files from fresh build')

    # components.json is repo data (never in the artifact) - the v0.6 base zip
    # carries the broken 25-entry list that crashed v0.7 at startup. Write the
    # fixed list: upstream 26 (e42715309c6) minus svadhesive (cfx-internal,
    # not in source tree, DLL never built - v0.7.1).
    shutil.copy2('/home/user/nsm/branding/components-server.json',
                 os.path.join(out, 'NSM-Server', 'components.json'))

    # --- asserts ---
    exe_p = os.path.join(out, 'NSM-Server', 'nsm-server.exe')
    check(os.path.exists(exe_p), 'NSM-Server/nsm-server.exe present')
    check(not os.path.exists(os.path.join(out, 'NSM-Server', 'FXServer.exe')), 'no stray FXServer.exe')
    exe = open(exe_p, 'rb').read()
    check(b'NSM Server (AxiomFX)' in exe, 'exe: "NSM Server (AxiomFX)" version line')
    check('NSM Server'.encode('utf-16-le') in exe, 'exe: UTF-16 "NSM Server" (title/rc)')
    check('NSM Community'.encode('utf-16-le') in exe, 'exe: UTF-16 "NSM Community" (rc CompanyName)')
    check('nsm-server.exe'.encode('utf-16-le') in exe, 'exe: UTF-16 "nsm-server.exe" (rc)')
    ico_b = open(NSM_ICO, 'rb').read()
    check(ico_b[0:6] in exe, 'exe: embedded NSM multi-size icon')
    impl_p = os.path.join(out, 'NSM-Server', 'citizen-server-impl.dll')
    impl = open(impl_p, 'rb').read()
    check(impl.count(VPS) == 3, f'citizen-server-impl.dll: {impl.count(VPS)}x VPS IP (expect 3)')
    check(b'NSM-Server-' in impl, 'citizen-server-impl.dll: NSM-Server- version prefix')
    mon_p = os.path.join(out, 'NSM-Server', 'citizen-server-monitor.dll')
    check(b'NSM-Server-' in open(mon_p, 'rb').read(), 'citizen-server-monitor.dll: NSM-Server- prefix')
    cfg = open(os.path.join(out, 'NSM-Server', 'server.cfg'), 'rb').read()
    check(b'sv_lan "true"' in cfg, 'server.cfg: sv_lan "true"')
    comps = json.load(open(os.path.join(out, 'NSM-Server', 'components.json')))
    check(len(comps) == 25, f'components.json: {len(comps)} entries (expect 25 = upstream 26 minus svadhesive)')
    check('citizen:devtools' not in comps, 'components.json: devtools not force-loaded')
    check('citizen:server:state:rdr3sv' in comps, 'components.json: rdr3sv state present')
    # v0.7.1 lesson: every listed component must actually have its DLL in the
    # package (svadhesive listed but absent = 'error code 2' at user boot)
    for c in comps:
        dll = c.replace(':', '-') + '.dll'
        check(os.path.exists(os.path.join(out, 'NSM-Server', dll)),
              f'components.json: {c} -> {dll} missing from package')

    names_after = set(os.path.relpath(p, out).replace(os.sep, '/') for p in walk_files(out))
    added = names_after - names_before
    removed = names_before - names_after
    print(f'  vs v0.6: +{len(added)} new, -{len(removed)} removed')
    for n in sorted(added)[:10]:
        print('    +', n)
    for n in sorted(removed)[:10]:
        print('    -', n)

    out_zip = os.path.join(sdir, 'NSM-server-v0.7.zip')
    if os.path.exists(out_zip):
        os.remove(out_zip)
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(walk_files(out)):
            z.write(p, os.path.relpath(p, out).replace(os.sep, '/'))
    print(f'  BUILT {out_zip} ({os.path.getsize(out_zip):,} bytes)', flush=True)
    return out_zip

# ---------------------------------------------------------------------------
X_LINK_OLD = [b'https://x.com/FiveM/status/', b'https://x.com/NSM/status/']
X_LINK_NEW = b'https://x.com/scravenz101/status/'

def patch_ui_xlinks(ui_bytes):
    """Rewrite the hardcoded status-link template inside ui.zip so feed items
    link to the NSM owner's X handle instead of FiveM's."""
    src = zipfile.ZipFile(io.BytesIO(ui_bytes))
    buf = io.BytesIO()
    patched = 0
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for n in src.namelist():
            data = src.read(n)
            if n.endswith('.js'):
                for old in X_LINK_OLD:
                    patched += data.count(old)
                    data = data.replace(old, X_LINK_NEW)
            out.writestr(n, data)
    return buf.getvalue(), patched


def patch_discord_oauth(b):
    """Rebrand the OAuth AUTHORIZE template baked into discord.dll (Discord
    SDK wrapper: scopes guilds.join / client_id <old FiveM id> / redirect_url
    https://cfx.re). Same-length byte swaps only - the strings are
    NUL-terminated pool entries, so equal-length replacement cannot move RVAs.
    Both app ids are 19 bytes -> the template gets our REAL id; the 14-byte
    cfx.re redirect becomes nsm.invalid (NUL-terminated dead end + padding,
    since no oauth redirect is registered for the NSM Discord app yet).
    The ACTIVE RPC id (pointer-referenced, injected by the build) is already
    ours and is not touched."""
    OLD_ID = b'1473308775258525930'        # 19 bytes
    NEW_ID = b'1560111337923805305'        # 19 bytes
    OLD_RDR = b'https://cfx.re'            # 14 bytes
    NEW_RDR = b'nsm.invalid\x00\x00\x00'   # 14 bytes (NUL-terminated + pad)
    n, r = b.count(OLD_ID), b.count(OLD_RDR)
    assert n == 1 and r == 1, f'discord.dll oauth blob not as expected: id={n} rdr={r}'
    assert len(NEW_ID) == len(OLD_ID) and len(NEW_RDR) == len(OLD_RDR)
    b = b.replace(OLD_ID, NEW_ID).replace(OLD_RDR, NEW_RDR)
    return b, n, r


def patch_citizen_refs(b):
    """Rename references to the launcher exe inside binaries: 'CitizenFX.exe'
    (13 B, NUL-terminated, exactly 1 occurrence per file) -> 'NSM.exe' + NUL
    padding. Same-length in-place swap, so no RVAs/offsets move."""
    OLD = b'CitizenFX.exe'
    NEW = b'NSM.exe\x00\x00\x00\x00\x00\x00'
    assert len(NEW) == len(OLD)
    n = b.count(OLD)
    b = b.replace(OLD, NEW)
    return b, n


def patch_ui_big_loadscreen(data):
    """Swap the boot loading-screen background (stock FiveM art with the
    wordmark baked in) for the NSM boot screen inside citizen/ui-big.zip."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    replaced = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for item in src.infolist():
            b = src.read(item.filename)
            if item.filename == 'loadscreen/ea097d53311d8e118a31.jpg':
                b = open('/home/user/nsm/branding/nsm-loadscreen.jpg', 'rb').read()
                replaced += 1
            z.writestr(item, b)
    assert replaced == 1, f'loadscreen bg not found in ui-big.zip ({replaced})'
    return out.getvalue()

RENAMED_FROM = {'NSM.exe': 'CitizenFX.exe', 'NSM.com': 'FiveM.com', 'NSM_Diag.exe': 'FiveM_Diag.exe'}

def build_client_v04(fivem_run):
    print('\n=== NSM-Client v0.4 ===', flush=True)
    cdir = os.path.join(WORK, 'client')
    base_zip = os.path.join(cdir, 'NSM-client-v0.3-preview.zip')
    os.makedirs(os.path.dirname(base_zip), exist_ok=True)
    if not os.path.exists(base_zip):
        download(f'{REPO_API}/releases/assets/{OLD_CLIENT_ASSET}', base_zip)

    art = os.path.join(WORK, 'fivem-art')
    if not os.path.exists(os.path.join(art, 'caches')):
        unpack_artifact(fivem_run, 'p2-fivem-output', art)
    fb = os.path.join(art, 'caches', 'fivereborn')
    check(os.path.isdir(fb), 'artifact has caches/fivereborn')

    out_zip = os.path.join(cdir, 'NSM-client-v0.7.zip')
    if os.path.exists(out_zip):
        os.remove(out_zip)
    replaced = kept_sticky = refs_patched = 0
    xlink_patched = 0
    new_files = []
    with zipfile.ZipFile(base_zip) as zin:
        base_names = zin.namelist()
        with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
            seen_names = set()
            for item in zin.infolist():
                if item.filename in seen_names:
                    continue  # skip duplicate zip entries carried in the base
                seen_names.add(item.filename)
                data = zin.read(item.filename)
                inner = item.filename[len('NSM-Client/'):] if item.filename.startswith('NSM-Client/') else None
                if inner and inner != 'components.json':   # components.json = sticky repo copy
                    src = RENAMED_FROM.get(inner, inner)     # NSM.exe etc. come from legacy names
                    cand = os.path.join(fb, src)
                    if os.path.isfile(cand):
                        data = open(cand, 'rb').read()
                        replaced += 1
                elif inner == 'components.json':
                    kept_sticky += 1
                if item.filename == 'NSM-Client/citizen/ui.zip':
                    data, n = patch_ui_xlinks(data)
                    xlink_patched += n
                if item.filename == 'NSM-Client/citizen/ui-big.zip':
                    data = patch_ui_big_loadscreen(data)
                if item.filename == 'NSM-Client/discord.dll':
                    data, did, drdr = patch_discord_oauth(data)
                out_name = item.filename
                if out_name == 'NSM-Client/CitizenFX.exe':
                    out_name = 'NSM-Client/NSM.exe'   # user-visible launcher name
                if out_name == 'NSM-Client/FiveM.com':
                    out_name = 'NSM-Client/NSM.com'   # crash handler helper
                if out_name == 'NSM-Client/FiveM_Diag.exe':
                    out_name = 'NSM-Client/NSM_Diag.exe'
                if out_name == 'NSM-Client/NSM.exe' or (inner and inner.startswith('CitizenFX_SubProcess') and inner.endswith('.bin')):
                    data, nref = patch_citizen_refs(data)
                    refs_patched += nref
                if out_name != item.filename:
                    zi = zipfile.ZipInfo(out_name, date_time=item.date_time)
                    zi.external_attr = item.external_attr
                    zout.writestr(zi, data)
                else:
                    zout.writestr(item, data)
            for p in walk_files(fb):
                rel = os.path.relpath(p, fb).replace(os.sep, '/')
                if rel == 'components.json':
                    continue  # sticky
                if rel in RENAMED_FROM.values():
                    continue  # consumed via the rename translation above
                if f'NSM-Client/{rel}' not in base_names:
                    if rel.startswith('CitizenFX_SubProcess') and rel.endswith('.bin'):
                        d, nref = patch_citizen_refs(open(p, 'rb').read())
                        zout.writestr(f'NSM-Client/{rel}', d)
                        refs_patched += nref
                    else:
                        zout.write(p, f'NSM-Client/{rel}')
                    new_files.append(rel)
            if 'NSM-Client/steam_appid.txt' not in base_names:
                zout.writestr('NSM-Client/steam_appid.txt', '218')
    print(f'  replaced {replaced} files from fresh build, sticky components.json kept ({kept_sticky})')
    for n in new_files[:15]:
        print('    + new:', n)
    check(replaced > 50, 'replaced a meaningful number of cache files')
    print(f'  ui.zip: {xlink_patched} x.com link template(s) repointed at packaging'
          ' (0 is fine - the in-build patcher rule already handles it)', flush=True)
    print(f'  exe rename: CitizenFX.exe -> NSM.exe; {refs_patched} binary references repointed')
    print('  discord.dll: oauth AUTHORIZE blob rebranded '
          f'(client_id -> NSM app id x{did}, cfx.re redirect -> nsm.invalid x{drdr})', flush=True)

    # --- asserts on the produced zip ---
    with zipfile.ZipFile(out_zip) as z:
        names = z.namelist()
        unique_base = len(set(base_names))
        expected = unique_base + (0 if 'NSM-Client/steam_appid.txt' in base_names else 1) + len(new_files)
        check(len(names) == len(set(names)) == expected, f'{len(names)} entries (base {unique_base} + steam_appid + {len(new_files)} new, no dupes)')
        check('NSM-Client/steam_appid.txt' in names, 'steam_appid.txt present beside CitizenFX.exe')
        check(z.read('NSM-Client/steam_appid.txt') == b'218', 'steam_appid.txt == 218')
        check('NSM-Client/NSM.exe' in names, 'launcher renamed to NSM.exe')
        check('NSM-Client/NSM.com' in names and 'NSM-Client/NSM_Diag.exe' in names,
              'FiveM.com/FiveM_Diag.exe renamed to NSM.com/NSM_Diag.exe')
        check(not any(('FiveM.com' in n) or ('FiveM_Diag' in n) for n in names),
              'no FiveM-named files left in the package')
        with zipfile.ZipFile(io.BytesIO(z.read('NSM-Client/citizen/ui-big.zip'))) as ub:
            check(ub.read('loadscreen/ea097d53311d8e118a31.jpg') ==
                  open('/home/user/nsm/branding/nsm-loadscreen.jpg', 'rb').read(),
                  'boot loading screen replaced with NSM art')
        check('NSM-Client/CitizenFX.exe' not in names, 'no CitizenFX.exe left in the package root')
        exe = z.read('NSM-Client/NSM.exe')
        check(exe.count(VPS) >= 6, f'NSM.exe: {exe.count(VPS)}x VPS URL (expect >=6)')
        stale_refs = 0
        for n in names:
            inner = n[len('NSM-Client/'):]
            if inner == 'NSM.exe' or (inner.startswith('CitizenFX_SubProcess') and inner.endswith('.bin')):
                stale_refs += z.read(n).count(b'CitizenFX.exe')
        check(stale_refs == 0, f'zero CitizenFX.exe refs in exe/subprocess blobs (got {stale_refs})')
        dd = z.read('NSM-Client/discord.dll')
        check(NEW_DISCORD_APP in dd, 'discord.dll: new NSM Discord app id present')
        check(OLD_DISCORD_APP not in dd, 'discord.dll: old FiveM app id gone')
        check(b'https://cfx.re' not in dd, 'discord.dll: no cfx.re redirect left')
        check(b'nsm.invalid' in dd, 'discord.dll: oauth redirect neutralized')
        ui = z.read('NSM-Client/citizen/ui.zip')
        js_cfx = 0
        wm = 0
        blue = 0
        nmark = 0
        xlink = 0
        with zipfile.ZipFile(io.BytesIO(ui)) as u:
            for n in u.namelist():
                if not (n.endswith('.js') or n.endswith('.css')):
                    continue
                b = u.read(n)
                if n.endswith('.js'):
                    js_cfx += len(re.findall(rb'FiveM|CitizenFX|Cfx\.re', b))
                    wm += b.count(b'data:image/png;base64')
                    nmark += b.count(b'M3 22V2H7.2')
                    xlink += b.count(X_LINK_NEW)
                else:
                    blue += b.count(b'#2f7bff') + b.count(b'#a8c7ff')
        check(js_cfx == 0, f'ui.zip JS: zero FiveM/CitizenFX/Cfx.re (got {js_cfx})')
        check(wm >= 2, f'ui.zip JS: {wm} embedded wordmarks (expect >=2)')
        check(blue >= 1, f'ui.zip CSS: {blue} blue accent pairs (expect >=1)')
        check(nmark >= 1, f'ui.zip JS: {nmark} NSM N-marks (expect >=1)')
        check(xlink >= 1, f'ui.zip JS: {xlink} scravenz101 status-link templates (expect >=1)')
        comps = json.loads(z.read('NSM-Client/components.json'))
        check(len(comps) == 63, f'components.json still {len(comps)} entries (expect 63)')
    print(f'  BUILT {out_zip} ({os.path.getsize(out_zip):,} bytes)', flush=True)
    return out_zip

# ---------------------------------------------------------------------------
def upload(zip_path, name, old_asset_id=None):
    print(f'\n=== upload {name} ===', flush=True)
    # delete any live asset with the same name (id may have changed since)
    for ass in api('GET', f'/releases/{RELEASE_ID}/assets'):
        if ass['name'] == name:
            try:
                api('DELETE', f'/releases/assets/{ass["id"]}')
                print(f"  deleted old asset {ass['id']}")
            except Exception as e:
                print('  old asset delete failed:', e)
    up = urllib.request.Request(
        f'https://uploads.github.com/repos/platinum-cfx/NSM-FIVEM/releases/{RELEASE_ID}/assets?name={name}',
        method='POST', data=open(zip_path, 'rb').read(),
        headers={'Authorization': f'token {TOKEN}', 'Content-Type': 'application/zip',
                 'User-Agent': 'nsm-pack'})
    with urllib.request.urlopen(up) as r:
        print('  uploaded:', json.loads(r.read())['browser_download_url'], flush=True)

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--server-run', required=True)
    ap.add_argument('--client-run', required=True)
    ap.add_argument('--upload', action='store_true')
    ap.add_argument('--only', choices=['server', 'client'])
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    server_zip = client_zip = None
    if a.only in (None, 'server'):
        server_zip = build_server_v07(a.server_run)
    if a.only in (None, 'client'):
        client_zip = build_client_v04(a.client_run)
    if a.upload:
        if server_zip:
            upload(server_zip, 'NSM-server-v0.7.zip')
        if client_zip:
            upload(client_zip, 'NSM-client-v0.7.zip')
    print('\nDONE. (upload %s)' % ('DONE' if a.upload else 'SKIPPED (no --upload)'), flush=True)
