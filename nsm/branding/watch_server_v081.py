#!/usr/bin/env python3
"""Wait for the server CI build, package v0.8.1-localtest, verify, and upload.

Adds a new, uniquely named release asset; never deletes or replaces v0.8.
"""
from __future__ import annotations
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

REPO = "platinum-cfx/NSM-FIVEM"
RUN_ID = 38795556491
EXPECTED_HEAD = "3562e833c08af5f28421b5e339f0b30d3aaf40db"
RELEASE_ID = 412737383
BASE_ASSET = 644733387  # NSM-server-v0.8-localtest.zip
ASSET_NAME = "NSM-server-v0.8.1-localtest.zip"
ROOT = pathlib.Path("/home/user/nsm")
TOKEN_SOURCE = ROOT / "branding/dispatch_phase1.sh"
LOG = ROOT / "branding/server-v081-build.log"
WORK = pathlib.Path("/var/tmp/phase1-pack")
ART_DIR = WORK / "fxserver-art-v081"
BASE_ZIP = WORK / "server/NSM-server-v0.8-localtest.zip"
OUT_DIR = ROOT / "releases"
OUT_ZIP = OUT_DIR / ASSET_NAME
PACKAGE = ROOT / "branding/package_phase1.py"

m = re.search(r"ghp_[A-Za-z0-9]{20,}", TOKEN_SOURCE.read_text(encoding="utf-8"))
if not m:
    raise SystemExit("No GitHub credential available; no network request made.")
TOKEN = m.group(0)
API = f"https://api.github.com/repos/{REPO}"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "NSM-server-v081-packager",
}


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def api_get(path: str):
    req = urllib.request.Request(API + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def wait_for_ci() -> None:
    log(f"watching server CI run {RUN_ID}")
    while True:
        run = api_get(f"/actions/runs/{RUN_ID}")
        status, conclusion = run.get("status"), run.get("conclusion")
        log(f"CI status={status} conclusion={conclusion}")
        if run.get("head_sha") != EXPECTED_HEAD:
            raise SystemExit("server CI run is not building the reviewed fix commit; stop")
        if status == "completed":
            if conclusion != "success":
                raise SystemExit(f"server CI ended with {conclusion}; no package made")
            return
        time.sleep(60)


def download_asset(asset_id: int, dest: pathlib.Path) -> None:
    url = f"{API}/releases/assets/{asset_id}"
    req = urllib.request.Request(url, headers={**HEADERS, "Accept": "application/octet-stream"})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(req, timeout=600)
    except urllib.error.HTTPError as exc:
        loc = exc.headers.get("Location")
        if exc.code not in (301, 302, 303, 307) or not loc:
            raise
        response = urllib.request.urlopen(urllib.request.Request(loc, headers={"User-Agent": "NSM-server-v081-packager"}), timeout=600)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)
    log(f"downloaded v0.8 base ({dest.stat().st_size:,} bytes)")


def patch_local_urls(data: bytes) -> bytes:
    def vps_repl(m):
        old = m.group()
        new = b"http://127.0.0.1" + old[len(b"http://194.104.146.133"):]
        if len(new) > len(old):
            raise ValueError("localhost rewrite would overflow string")
        return new + b"\x00" * (len(old) - len(new))
    def aka_repl(m):
        old = m.group()
        new = b"http://127.0.0.1/a" + old[len(b"https://aka.cfx.re"):]
        if len(new) > len(old):
            raise ValueError("aka rewrite would overflow string")
        return new + b"\x00" * (len(old) - len(new))
    data = re.sub(rb"http://194\.104\.146\.133[^\x00]*", vps_repl, data)
    data = re.sub(rb"https://aka\.cfx\.re/[^\x00]*", aka_repl, data)
    return data


def package() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        raise SystemExit(f"refusing to overwrite existing output: {OUT_ZIP}")
    if ART_DIR.exists():
        shutil.rmtree(ART_DIR)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    if BASE_ZIP.exists():
        BASE_ZIP.unlink()
    download_asset(BASE_ASSET, BASE_ZIP)

    # Reuse the established artifact downloader, with this exact successful CI run.
    sys.path.insert(0, str(ROOT / "branding"))
    os.environ["GH_TOKEN"] = TOKEN
    import package_phase1 as p
    p.unpack_artifact(RUN_ID, "p2-fxserver-output", str(ART_DIR))
    relroot = ART_DIR / ".build-cache/bin/server/windows/release"
    built_dll = relroot / "citizen-server-impl.dll"
    if not built_dll.is_file():
        raise SystemExit(f"rebuilt DLL missing from artifact: {built_dll}")
    new_impl = built_dll.read_bytes()
    if len(new_impl) < 1_000_000:
        raise SystemExit(f"rebuilt DLL unexpectedly small: {len(new_impl)} bytes")
    log(f"rebuilt citizen-server-impl.dll: {len(new_impl):,} bytes")

    tmp_zip = OUT_ZIP.with_suffix(".zip.part")
    with zipfile.ZipFile(BASE_ZIP) as zin, zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        names = zin.namelist()
        target = "NSM-Server/citizen-server-impl.dll"
        if target not in names:
            raise SystemExit(f"base zip missing {target}")
        if len(names) != len(set(names)):
            raise SystemExit("base zip contains duplicate names")
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == target:
                data = new_impl
            elif item.filename == "NSM-Server/README-SERVER-LOCALTEST.txt":
                text = data.decode("utf-8", "replace")
                text = text.replace("NSM Server v0.8 LOCALTEST", "NSM Server v0.8.1 LOCALTEST")
                text += "\n\nVersion 0.8.1 contains the rebuilt startup/masterlist changes. Local-test build; runtime verification is still pending.\n"
                data = text.encode("utf-8")
            if item.filename.lower().endswith((".dll", ".exe")):
                data = patch_local_urls(data)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.external_attr = item.external_attr
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, data)
    tmp_zip.replace(OUT_ZIP)

    with zipfile.ZipFile(OUT_ZIP) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f"package CRC failed at {bad}")
        names = z.namelist()
        impl = z.read("NSM-Server/citizen-server-impl.dll")
        all_pe = b"".join(z.read(n) for n in names if n.lower().endswith((".dll", ".exe")))
        checks = {
            "new DLL is the CI artifact with local URLs patched": impl == patch_local_urls(new_impl),
            "local heartbeat endpoint embedded": b"http://127.0.0.1/api/serverlist/ingress" in impl,
            "no VPS address remains in server binaries": b"http://194.104.146.133" not in all_pe,
            "no direct aka route remains in server binaries": b"https://aka.cfx.re" not in all_pe,
            "local server config retained": b'sv_lan "true"' in z.read("NSM-Server/server.cfg"),
            "no svadhesive DLL": not any(n.lower().endswith("svadhesive.dll") for n in names),
            "v0.8.1 README present": b"v0.8.1" in z.read("NSM-Server/README-SERVER-LOCALTEST.txt"),
        }
        for label, ok in checks.items():
            log(("PASS " if ok else "FAIL ") + label)
        if not all(checks.values()):
            raise SystemExit("package verification failed")

    # The release asset name is unique. Refuse to replace anything already published.
    assets = api_get(f"/releases/{RELEASE_ID}/assets?per_page=100")
    if any(a["name"] == ASSET_NAME for a in assets):
        raise SystemExit(f"release already has {ASSET_NAME}; refusing overwrite")
    upload = urllib.request.Request(
        f"https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name={ASSET_NAME}",
        data=OUT_ZIP.read_bytes(), method="POST",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/zip", "User-Agent": "NSM-server-v081-packager"},
    )
    with urllib.request.urlopen(upload, timeout=900) as resp:
        asset = json.load(resp)
    log(f"uploaded new asset {asset['name']} ({asset['size']:,} bytes): {asset['browser_download_url']}")


if __name__ == "__main__":
    wait_for_ci()
    package()
