#!/usr/bin/env python3
"""Execute rebrand Waves 1-4 on the axiomfx-complete-rebrand worktree.

DRIVE RULES (user-endorsed):
- Scripting API / runtime IDs / internal symbols / legal / vendor / paths: NEVER touched.
- QBCore, ESX, and every FiveM script must keep working -> zero changes to
  Citizen.*, CitizenFX.* namespaces, citizen: natives, fxmanifest, component names.
- Functional endpoints (content.cfx.re, runtime.fivem.net) stay until own mirror.
- msgid lines in .po files are lookup keys -> only msgstr (display) is edited.

After editing, re-classifies the whole tree and verifies every KEEP-* bucket
count is unchanged. Aborts loudly if any KEEP line was modified.
"""
import re, os, sys, collections

WT = '/var/tmp/nsm-wt'
INV = '/home/user/nsm/branding/inventory/ALL-MATCHES.txt'
os.chdir(WT)

# ---------------- guards ----------------
IDENT = re.compile(
    r'CitizenFX::|namespace CitizenFX|CitizenFX\.(Core|Client|Server|FiveM|Native|UI)|'
    r'\bCitizen\.[A-Za-z_]|\bcitizen:|\bCfx[A-Z]|\bCFX_|\bcfx[A-Z_]|fxmanifest|fx_version|'
    r'citizenfx/|fivem-source|platinum-cfx')
LEGAL = re.compile(
    r'[Cc]opyright|Platform Agreement|LGPL|Take-Two|Rockstar|Creator Platform|THIRD_PARTY|licen[cs]e')
PROV  = re.compile(r'Origin:|snapshot of|imported via|provenance')
FUNC_URL = re.compile(r'content\.cfx\.re|runtime\.fivem\.net|aka\.cfx\.re|static\.cfx\.re|users\.cfx\.re|\.cfx\.re/|fivem\.net/|cfx\.re')
SKIP_FILES = {
    # build-path logic (/build/fivem on the CI mount) - not branding
    'code/client/launcher/Minidump.Symbolication.cpp',
    # console component target binary name - not in our build; renaming changes output artifact
    'code/client/console/premake5.lua',
}
SKIP_PATTERNS = [re.compile(p) for p in (
    r"^\.gitattributes$", r"^\.github/workflows/.*$"# workflows handled separately (logic danger)
)]

def brand_replace(text):
    for a, b in (('FiveM.com', 'NSM Community'), ('FiveM', 'NSM'),
                 ('fivem://', 'nsm://'), ('CitizenFX', 'AxiomFX'),
                 ('FXServer', 'NSM Server'), ('FiveReborn', 'NSM'),
                 ('fivereborn', 'nsm')):
        text = text.replace(a, b)
    # standalone lowercase 'fivem' in prose only (never fivem-builder/fivem/ urls)
    text = re.sub(r'\bfivem\b(?![-_/.])', 'nsm', text)
    return text

COSMETIC_URL = re.compile(r'https?://(?:docs\.fivem\.net|forum\.(?:cfx\.re|fivem\.net)|wiki\.fivem\.net)[^\s"\']*')

def ext_of(path):
    base = path.rsplit('/', 1)[-1]
    return base.rsplit('.', 1)[-1].lower() if '.' in base else ''

CODE_EXTS = {'cpp','h','hpp','cc','c','cs','rc','idl','inl','m','mm'}
SCRIPT_EXTS = {'py','sh','yml','yaml','ps1','psm1','cmake','mk','gradle','rb','pl'}

def is_comment(ext, s):
    if ext in CODE_EXTS: return s.startswith('//') or s.startswith('/*') or s.startswith('*')
    if ext == 'lua': return s.startswith('--') or s.startswith('--')
    if ext in SCRIPT_EXTS: return s.startswith('#')
    if ext in ('md','txt','rst','po','pot','gitignore'): return True
    return False

# ---------------- load inventory ----------------
plan = collections.defaultdict(dict)
for line in open(INV):
    m = re.match(r'([^:]+):(\d+) \[([^\]]+)\] (.*)', line.rstrip('\n'))
    if m:
        plan[m.group(1)][int(m.group(2))] = (m.group(3), m.group(4))

stats = collections.Counter()
files_changed = set()
mismatch = []

def apply_line(path, idx, line, cat):
    ext = ext_of(path)
    s = line.lstrip()
    if cat.startswith('KEEP'):
        return line
    if LEGAL.search(line) or PROV.search(line) or IDENT.search(line):
        stats[f'skip-guard:{cat}'] += 1; return line
    if cat == 'REBRAND-url':
        if FUNC_URL.search(line) and not COSMETIC_URL.search(line):
            stats['skip-functional-url'] += 1; return line
        if COSMETIC_URL.search(line):
            new = COSMETIC_URL.sub('https://discord.gg/UXj5QfCX88', line)
            if not IDENT.search(new):
                stats['changed:url'] += 1; return new
        stats[f'skip-url-other'] += 1; return line
    # visible / docs / review from here
    if ext in ('po','pot'):
        return line  # handled by dedicated .po pass
    if cat == 'REBRAND-visible':
        if ext in CODE_EXTS or ext == 'lua':
            # only edit inside string literals
            def qrep(mo):
                inner = brand_replace(mo.group(1))
                stats['changed:visible-string'] += 1
                return '"%s"' % inner
            new = re.sub(r'"([^"\n]*)"', qrep, line)
            return new if not IDENT.search(new) else line
        if ext in SCRIPT_EXTS:
            if 'description' in line.lower() or is_comment(ext, s):
                new = brand_replace(line)
                stats['changed:visible-script'] += 1 if new != line else 0
                return new
            stats['skip-script-logic'] += 1; return line
        new = brand_replace(line)
        if new != line: stats['changed:visible-doc'] += 1
        return new
    if cat in ('REBRAND-docs',):
        if FUNC_URL.search(line) or 'http' in line:
            stats['skip-doc-url'] += 1; return line
        if is_comment(ext, s):
            new = brand_replace(line)
            if new != line: stats['changed:docs'] += 1
            return new
        stats['skip-docs-notcomment'] += 1; return line
    if cat == 'REVIEW':
        if path.startswith('.github/ISSUE_TEMPLATE'):
            new = brand_replace(line)
            if new != line: stats['changed:review-templates'] += 1
            return new
        if ext in SCRIPT_EXTS and (is_comment(ext, s) or 'description' in line.lower()):
            new = brand_replace(line)
            if new != line: stats['changed:review-ci-text'] += 1
            return new
        stats['skip-review'] += 1; return line
    stats[f'skip-uncat:{cat}'] += 1
    return line

# ---------------- pass 1: line-addressed edits ----------------
for path, entries in plan.items():
    if path in SKIP_FILES or any(p.match(path) for p in SKIP_PATTERNS):
        stats['skip-file'] += len(entries); continue
    if ext_of(path) in ('po','pot'):
        continue  # dedicated pass
    if not os.path.exists(path):
        stats['missing'] += 1; continue
    try:
        with open(path, encoding='utf-8', errors='surrogateescape', newline='') as f:
            lines = f.readlines()
    except OSError:
        stats['unreadable'] += 1; continue
    dirty = False
    for lineno, (cat, content) in sorted(entries.items()):
        if lineno - 1 >= len(lines):
            mismatch.append((path, lineno, 'oob')); continue
        cur = lines[lineno - 1]
        if cur.rstrip('\r\n') != content.rstrip('\r\n'):
            mismatch.append((path, lineno, 'drift')); continue
        new = apply_line(path, lineno, cur, cat)
        if new != cur:
            lines[lineno - 1] = new; dirty = True
    if dirty:
        with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
            f.writelines(lines)
        files_changed.add(path); stats['files'] += 1

# ---------------- pass 2: .po msgstr state machine ----------------
po_files = [p for p in plan if ext_of(p) in ('po',)]
for path in po_files:
    if not os.path.exists(path): continue
    with open(path, encoding='utf-8', errors='surrogateescape', newline='') as f:
        lines = f.readlines()
    state = None; dirty = False; n = 0
    for i, line in enumerate(lines):
        if line.startswith('msgid '): state = 'id'
        elif line.startswith('msgstr '): state = 'str'
        if state == 'str' and ('FiveM' in line or 'CitizenFX' in line or 'fivem' in line):
            new = brand_replace(line)
            if new != line: lines[i] = new; dirty = True; n += 1
    if dirty:
        with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
            f.writelines(lines)
        files_changed.add(path); stats['files'] += 1
        stats['changed:po-msgstr'] += n

# ---------------- pass 3: targeted code-aware edits ----------------
def targeted(path, old, new, why):
    if not os.path.exists(path): stats[f'missing-target:{why}'] += 1; return
    with open(path, encoding='utf-8', errors='surrogateescape', newline='') as f:
        t = f.read()
    if old not in t:
        stats[f'nomatch-target:{why}'] += 1; return
    t = t.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(t)
    files_changed.add(path); stats['files'] += 1; stats['changed:targeted'] += 1

# W1: launcher manifest identity
targeted('code/client/launcher/launcher.manifest',
         'name="FiveM"', 'name="NSM"', 'manifest-name')
# W1: diag utility description
targeted('code/client/diag/diagutil.rc',
         '"FiveM Diagnostics Utility"', '"NSM Diagnostics Utility"', 'diagdesc')
# W1: MiniDump - recognize NSM.exe crash hashes (keep fivem.exe+ for legacy dumps)
targeted('code/client/launcher/MiniDump.cpp',
         '_wcsnicmp(hash.c_str(), L"fivem.exe+", 10) == 0 ||',
         '_wcsnicmp(hash.c_str(), L"fivem.exe+", 10) == 0 ||\n\t\t_wcsnicmp(hash.c_str(), L"NSM.exe+", 8) == 0 ||',
         'minidump-nsm')
# W1: p2-build description (input VALUES untouched)
targeted('.github/workflows/p2-build.yml',
         "description: 'Product to build (fxserver = server, fivem = client)'",
         "description: 'Product to build (NSM server or client)'", 'wf-desc')

# W1: icon file renames + rc refs (build-internal brand assets)
import subprocess
for old, new in (('fivem.ico', 'nsm.ico'), ('fivem_sp.ico', 'nsm_sp.ico'),
                 ('fivem_sdk.ico', 'nsm_sdk.ico')):
    p = 'code/client/launcher/' + old
    if os.path.exists(p):
        subprocess.run(['git', 'mv', p, 'code/client/launcher/' + new], check=True)
        stats['renamed-icons'] += 1
targeted('code/client/launcher/launcher.rc', '"fivem.ico"', '"nsm.ico"', 'rc-icon1')
targeted('code/client/launcher/launcher.rc', '"fivem_sp.ico"', '"nsm_sp.ico"', 'rc-icon2')
targeted('code/client/launcher/launcher.rc', '"fivem_sdk.ico"', '"nsm_sdk.ico"', 'rc-icon3')

print('════ EDIT SUMMARY ════')
for k, v in sorted(stats.items()):
    print(f'  {k:<28} {v}')
print(f'  files changed (unique):     {len(files_changed)}')
print(f'  inventory line mismatches:  {len(mismatch)}')
for p, l, w in mismatch[:8]:
    print(f'    {p}:{l} ({w})')

# ---------------- verification: KEEP buckets must be unchanged ----------------
def classify(path, content):
    """Same classifier as sweep_inventory.py (must stay in sync)."""
    pl = path.lower()
    if re.search(r'(licen[cs]e|notice|third[_-]?party|copying|patent|authors)', pl):
        return 'KEEP-legal'
    if re.search(r'(^|/)vendor/|/vendor/|(^|/)dependencies/|(^|/)ext/sdk/|(^|/)submodules/', pl):
        return 'KEEP-vendor'
    if pl.endswith(('.po', '.pot')):
        return 'REBRAND-visible'
    if re.search(r'CitizenFX\.(Core|Server|Client|FiveM|Native|UI|Graphics|Math|Streaming|Sync|System|FileSystem|Blip|Player|Ped|Vehicle|Weapon|Color|Vector)', content):
        return 'KEEP-scripting-api'
    if re.search(r'\bCitizen\.[A-Za-z_]', content):
        return 'KEEP-scripting-api'
    if re.search(r'fxmanifest|fx_version|__resource_manifest', content, re.I):
        return 'KEEP-scripting-api'
    if re.search(r'citizen:', content):
        return 'KEEP-runtime-id'
    if re.search(r'citizen[-_](server|scripting|net|game|level)|citicore|resources[-_]core|state[-_](fivesv|rdr3sv)|vfs-core|pool-sizes|svadhesive|adhesive|conhost|monitor[-_]component|fxdk', content, re.I):
        return 'KEEP-runtime-id'
    if re.search(r'namespace CitizenFX|CitizenFX::|using namespace CitizenFX|\bCfx[A-Z]|\bCFX_|\bcfx[A-Z_]', content):
        return 'KEEP-internal-symbol'
    if re.search(r'https?://|cfx\.re|fivem\.net|citizen\.re', content, re.I):
        return 'REBRAND-url'
    if re.search(r'["\'`][^"\'`\n]*(fivem|fivereborn)[^"\'`\n]*["\'`]', content, re.I):
        return 'REBRAND-visible'
    if re.match(r'\s*(//|/\*|\*|#|--|;)', content):
        return 'REBRAND-docs'
    if pl.endswith(('.md', '.txt', '.rst')):
        return 'REBRAND-docs'
    return 'REVIEW'

grep = subprocess.run(['git', 'grep', '-n', '-I', '-i', '-E',
                       'citizenfx|citizen|cfx|fivem|fivereborn|fxserver', '--', '.'],
                      capture_output=True, text=True).stdout.splitlines()
after = collections.Counter()
for ln in grep:
    m = re.match(r'([^:]+):(\d+):(.*)', ln)
    if m:
        after[classify(m.group(1), m.group(3))] += 1

expected_keep = {'KEEP-scripting-api': 930, 'KEEP-runtime-id': 470,
                 'KEEP-internal-symbol': 712, 'KEEP-vendor': 189, 'KEEP-legal': 7}
print('════ VERIFY: KEEP buckets before -> after ════')
fail = False
for k, before_n in expected_keep.items():
    a = after.get(k, 0)
    status = 'OK' if a == before_n else '*** CHANGED ***'
    if a != before_n: fail = True
    print(f'  {k:<24} {before_n:>5} -> {a:<5} {status}')
print('════ remaining matches by category (after) ════')
for k, v in after.most_common():
    print(f'  {k:<24} {v}')
print('════ RESULT:', 'FAIL - KEEP bucket modified!' if fail else 'PASS - compatibility surface untouched')
sys.exit(1 if fail else 0)
