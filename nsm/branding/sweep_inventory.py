#!/usr/bin/env python3
"""Mission Phase 6 deep inventory sweep — NSM-FIVEM a1-rebrand tree.

Searches EVERY text file in the tree for legacy FiveM / CitizenFX / cfx
identifiers and classifies each match:

  KEEP-scripting-api    what QBCore/ESX/scripts call at runtime (DO NOT TOUCH)
  KEEP-runtime-id       component names, natives paths, DLL/source dir names
  KEEP-internal-symbol  C++ namespace CitizenFX, Cfx* classes, CFX_ macros
  KEEP-legal            LICENSE / THIRD_PARTY_NOTICES / copyright lines
  KEEP-vendor           vendored third-party code
  KEEP-path             file/dir NAMES containing the terms (build refs)
  REBRAND-visible       user-visible strings (UI, console, locale, crash text)
  REBRAND-url           cfx.re / fivem.net URLs
  REBRAND-docs          comments, docs, readmes (cosmetic)
  REVIEW                everything else - needs a human look

Outputs (workspace): inventory/ALL-MATCHES.txt, inventory/FILENAMES.txt,
inventory/WAVE1-FILES.txt + stdout summary. Reproducible: run inside bare clone.
"""
import subprocess, re, os, sys, collections

BARE = sys.argv[1] if len(sys.argv) > 1 else '/var/tmp/nsm-bare.git'
OUT = '/home/user/nsm/branding/inventory'
os.makedirs(OUT, exist_ok=True)
os.chdir(BARE)

TERMS = ['citizenfx', 'citizen', 'cfx', 'fivem', 'fivereborn', 'fxserver']

def classify(path, content):
    pl = path.lower()
    if re.search(r'(licen[cs]e|notice|third[_-]?party|copying|patent|authors)', pl):
        return 'KEEP-legal'
    if re.search(r'(^|/)vendor/|/vendor/|(^|/)dependencies/|(^|/)ext/sdk/|(^|/)submodules/', pl):
        return 'KEEP-vendor'
    if pl.endswith(('.po', '.pot')):                      # locale = user-visible
        return 'REBRAND-visible'
    if re.search(r'CitizenFX\.(Core|Server|Client|FiveM|Native|UI|Graphics|Math|Streaming|Sync|System|FileSystem|Blip|Player|Ped|Vehicle|Weapon|Color|Vector)', content):
        return 'KEEP-scripting-api'
    if re.search(r'\bCitizen\.[A-Za-z_]', content):        # Citizen.CreateThread etc.
        return 'KEEP-scripting-api'
    if re.search(r'fxmanifest|fx_version|__resource_manifest', content, re.I):
        return 'KEEP-scripting-api'
    if re.search(r'citizen:', content):                    # natives paths + component names
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

proc = subprocess.run(['git', 'grep', '-n', '-I', '-i', '-E',
                       '|'.join(TERMS), 'HEAD', '--'],
                      capture_output=True, text=True)
raw = proc.stdout.splitlines()

cat_lines = collections.Counter()
cat_files = collections.defaultdict(set)
term_lines = collections.Counter()
ext_lines = collections.Counter()
file_totals = collections.Counter()
total = 0
out_lines = []

for ln in raw:
    if not ln.startswith('HEAD:'):
        continue
    rest = ln[len('HEAD:'):]
    m = re.match(r'([^:]+):(\d+):(.*)', rest)
    if not m:
        continue
    path, lineno, content = m.group(1), m.group(2), m.group(3)
    total += 1
    cat = classify(path, content)
    cat_lines[cat] += 1
    cat_files[cat].add(path)
    file_totals[path] += 1
    ext = path.rsplit('.', 1)[-1].lower() if '.' in path.rsplit('/', 1)[-1] else '(noext)'
    ext_lines[ext] += 1
    hit_terms = [t for t in TERMS if re.search(t, content, re.I)]
    for t in hit_terms:
        term_lines[t] += 1
    out_lines.append(f'{path}:{lineno} [{cat}] {content}')

with open(os.path.join(OUT, 'ALL-MATCHES.txt'), 'w') as f:
    f.write('\n'.join(out_lines) + '\n')

# files whose PATH itself contains a legacy term
ls = subprocess.run(['git', 'ls-tree', '-r', 'HEAD', '--name-only'],
                    capture_output=True, text=True).stdout.splitlines()
name_hits = [f for f in ls if re.search(r'(?i)(citizen|cfx|fivem|fxserver|fivereborn)', f)]
with open(os.path.join(OUT, 'FILENAMES.txt'), 'w') as f:
    f.write('# files/dirs whose NAME contains a legacy term -> KEEP-path '
            '(renaming breaks #includes/build/runtime refs; zero user visibility)\n')
    f.write('\n'.join(name_hits) + '\n')

# wave 1 rebrand targets: user-visible + urls (the set we actually change first)
wave1 = sorted(cat_files['REBRAND-visible'] | cat_files['REBRAND-url'])
with open(os.path.join(OUT, 'WAVE1-FILES.txt'), 'w') as f:
    f.write('# WAVE 1 rebrand targets (user-visible strings + URLs)\n')
    f.write('\n'.join(wave1) + '\n')

all_files_with_hits = set(file_totals)
print(f'TOTAL text matches: {total} in {len(all_files_with_hits)} of {len(ls)} files '
      f'({len(ls)-len(all_files_with_hits)} files clean)')
print()
print('== BY CATEGORY (lines / unique files) ==')
for c, n in cat_lines.most_common():
    print(f'  {c:<22} {n:>6} lines  {len(cat_files[c]):>5} files')
print()
print('== BY TERM (line hits, overlapping) ==')
for t in TERMS:
    print(f'  {t:<12} {term_lines[t]:>6}')
print()
print('== TOP EXTENSIONS ==')
for e, n in ext_lines.most_common(12):
    print(f'  .{e:<12} {n:>6}')
print()
print('== TOP 15 FILES BY MATCH COUNT ==')
for p, n in file_totals.most_common(15):
    print(f'  {n:>5}  {p}')
print()
print(f'path-name hits: {len(name_hits)} files (KEEP-path)')
print(f'WAVE 1 rebrand targets: {len(wave1)} files '
      f'({cat_lines["REBRAND-visible"]} visible-string lines + {cat_lines["REBRAND-url"]} URL lines)')
print(f'REVIEW bucket: {cat_lines["REVIEW"]} lines in {len(cat_files["REVIEW"])} files')
