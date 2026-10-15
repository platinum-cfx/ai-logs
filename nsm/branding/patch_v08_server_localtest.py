#!/usr/bin/env python3
"""Server patch: NSM-server-v0.7.1.zip -> NSM-server-v0.8-localtest.zip

Patches (all length-preserving / null-padded):
  1. citizen-server-impl.dll: masterlist/announce + ticket + pool-size endpoints
     http://194.104.146.133/... -> http://127.0.0.1/...  (our NSM-Masterlist.exe)
  2. citizen-server-impl.dll + citizen-server-state-fivesv.dll: aka.cfx.re
     mitigations -> http://127.0.0.1/a/... (mirror route)
  3. Bundles README-SERVER-LOCALTEST.txt

Left direct on purpose (cannot fit / not needed locally):
  bare cfx.re links (api/register telemetry, join links) - external links only.
"""
import zipfile, re, io, os, sys, collections

SRC = '/var/tmp/phase1-pack/server/NSM-server-v0.7.1.zip'
DST = '/var/tmp/phase1-pack/server/NSM-server-v0.8-localtest.zip'
stats = collections.Counter()

def vps_repl(m):
    old = m.group()
    new = b'http://127.0.0.1' + old[len(b'http://194.104.146.133'):]
    stats['VPS -> localhost'] += 1
    return new + b'\x00' * (len(old) - len(new))

def aka_repl(m):
    old = m.group()
    rest = old[len(b'https://aka.cfx.re'):]
    new = b'http://127.0.0.1/a' + rest
    assert len(new) <= len(old)
    stats['aka.cfx.re -> mirror route /a'] += 1
    return new + b'\x00' * (len(old) - len(new))

README = '''NSM Server v0.8 LOCALTEST
=========================

WHAT IS DIFFERENT
  - Your server now announces (heartbeats) to YOUR OWN masterlist on
    127.0.0.1 - the bundled NSM-Masterlist.exe from the client package.
  - It appears on your own website (http://127.0.0.1/servers), in the NSM
    client server list, and gets player counts there.

HOW TO RUN (LOCALHOST)
  1. Start the backend first: NSM-Masterlist.exe (from the client package,
     or copy it here). Keep the window open.
  2. Configure your server.cfg as usual (set the port you want).
  3. Run  NSM-Server.exe  as usual.
  4. Open http://127.0.0.1/servers - your server appears within ~30 seconds
     (heartbeat interval) with live player counts.

  The server and the backend must run on the SAME machine for this local test.
  When the VPS is ready, NSM-Masterlist.exe runs on the VPS instead and the
  server announce URLs get pointed there in the next build.

NOTE
  txAdmin never runs - it is not part of NSM Server.
'''

zin = zipfile.ZipFile(SRC)
zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
for item in zin.infolist():
    data = zin.read(item.filename)
    inner = item.filename[len('NSM-Server/'):] if item.filename.startswith('NSM-Server/') else item.filename
    if inner.endswith(('.dll', '.exe')) and inner.count('/') == 0:
        n1 = data.count(b'http://194.104.146.133')
        data = re.sub(rb'http://194\.104\.146\.133[^\x00]*', vps_repl, data)
        n2 = len(re.findall(rb'https://aka\.cfx\.re/[^\x00]*', data))
        data = re.sub(rb'https://aka\.cfx\.re/[^\x00]*', aka_repl, data)
        if n1 or n2:
            print(f'  {inner}: VPS={n1} aka={n2}')
    zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
    zi.external_attr = item.external_attr
    zi.compress_type = zipfile.ZIP_DEFLATED
    zout.writestr(zi, data)

zi = zipfile.ZipInfo('NSM-Server/README-SERVER-LOCALTEST.txt')
zi.compress_type = zipfile.ZIP_DEFLATED
zout.writestr(zi, README)
zout.close()

print('════ PATCHES APPLIED ════')
for k, v in sorted(stats.items()):
    print(f'  {k:<36} {v}')
print(f'  {"output size":<36} {os.path.getsize(DST):,} bytes')

# ---------------- verification ----------------
print('════ VERIFY ════')
z = zipfile.ZipFile(DST)
fails = 0
def check(cond, msg):
    global fails
    print(('  ok: ' if cond else '  FAIL: ') + msg)
    if not cond: fails += 1

impl = z.read('NSM-Server/citizen-server-impl.dll')
check(impl.count(b'http://194.104.146.133') == 0, 'no VPS URLs left in citizen-server-impl.dll')
check(impl.count(b'http://127.0.0.1/api/serverlist/ingress') == 1, 'ingress -> localhost masterlist')
check(impl.count(b'http://127.0.0.1/api/ticket/pubkey') == 1, 'ticket pubkey -> localhost')
check(impl.count(b'http://127.0.0.1/v1/public/pool-size-limits/') == 1, 'pool-size -> localhost')
sv = z.read('NSM-Server/citizen-server-state-fivesv.dll')
check(sv.count(b'http://127.0.0.1/a/') >= 1 and sv.count(b'https://aka.cfx.re') == 0, 'rcmitigation -> mirror route')
total = collections.Counter()
for n in z.namelist():
    if n.endswith(('.dll', '.exe')):
        d = z.read(n)
        total['vps'] += d.count(b'http://194.104.146.133')
        total['aka'] += d.count(b'https://aka.cfx.re')
check(total['vps'] == 0, f'zero VPS URLs in all server binaries ({total["vps"]})')
check(total['aka'] == 0, f'zero aka.cfx.re URLs in all server binaries ({total["aka"]})')
check('NSM-Server/README-SERVER-LOCALTEST.txt' in z.namelist(), 'README present')
print('════ RESULT:', 'PASS' if fails == 0 else f'{fails} FAILURES', '════')
sys.exit(1 if fails else 0)
