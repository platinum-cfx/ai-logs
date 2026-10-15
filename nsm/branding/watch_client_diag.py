#!/usr/bin/env python3
"""Wait for the client CI run, build a diagnostic package, and upload a new asset.

Uploads only after successful build and package verification. It never replaces
an existing release asset. The artifact is used only after CI reports success.
"""
from __future__ import annotations
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

REPO = "platinum-cfx/NSM-FIVEM"
BRANCH = "axiomfx-complete-rebrand"
RUN_ID = 38801965172
SERVER_RUN_ID = 38795556491  # required CLI arg; not used with --only client
ROOT = pathlib.Path("/home/user/nsm")
TOKEN_SOURCE = ROOT / "branding/dispatch_phase1.sh"
LOG = ROOT / "branding/client-diag-build.log"
WORK = pathlib.Path("/var/tmp/phase1-pack")
ASSET_NAME = "NSM-client-v0.7.4-diagnostic-localtest.zip"
RELEASE_ID = 412737383
OUT_DIR = WORK / "client"
OUT_ZIP = OUT_DIR / ASSET_NAME
PACKAGE = ROOT / "branding/package_phase1.py"
PATCHER = ROOT / "branding/patch_v074_localtest.py"
STACK_EXE = ROOT / "stack/NSM-Masterlist-v1.1.exe"

source = TOKEN_SOURCE.read_text(encoding="utf-8")
match = re.search(r"ghp_[A-Za-z0-9]{20,}", source)
if not match:
    raise SystemExit("No GitHub credential available; no network request made.")
TOKEN = match.group(0)
API = f"https://api.github.com/repos/{REPO}"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "NSM-client-diagnostic-builder",
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
    log(f"watching client CI run {RUN_ID}")
    while True:
        run = api_get(f"/actions/runs/{RUN_ID}")
        status = run.get("status")
        conclusion = run.get("conclusion")
        log(f"CI status={status} conclusion={conclusion}")
        if status == "completed":
            if conclusion != "success":
                raise SystemExit(f"client CI ended with {conclusion}; no package made")
            return
        time.sleep(60)


def build_package() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        raise SystemExit(f"refusing to overwrite diagnostic package: {OUT_ZIP}")
    # Clear only disposable build scratch from this exact run, never user files.
    for stale in [WORK / "fivem-art", WORK / "client/NSM-client-v0.7.zip",
                  WORK / "client/NSM-client-v0.7.4-localtest.zip"]:
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()
    if not STACK_EXE.is_file():
        raise SystemExit(f"required bundled stack missing: {STACK_EXE}")
    stack_dir = pathlib.Path("/tmp/stack")
    stack_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STACK_EXE, stack_dir / "NSM-Masterlist.exe")

    env = os.environ.copy()
    env["GH_TOKEN"] = TOKEN
    log("packaging client from successful CI artifact")
    subprocess.run([
        sys.executable, str(PACKAGE), "--server-run", str(SERVER_RUN_ID),
        "--client-run", str(RUN_ID), "--only", "client",
    ], env=env, check=True)
    log("applying the verified v0.7.4 localtest rebrand patch to the new build")
    subprocess.run([sys.executable, str(PATCHER)], env=env, check=True)

    built = WORK / "client/NSM-client-v0.7.4-localtest.zip"
    if not built.is_file():
        raise SystemExit(f"expected package not created: {built}")
    # Keep the tested baseline asset untouched; add a plain-English note so
    # this diagnostic build cannot be mistaken for a final client release.
    shutil.copy2(built, OUT_ZIP)
    note = (
        "NSM CLIENT DIAGNOSTIC BUILD\r\n"
        "This is not the final client fix. It adds launch tracing so we can see\r\n"
        "whether the game process starts and what exit code it returns.\r\n"
        "Keep your current NSM folder unchanged; extract this zip into a new folder.\r\n"
        "Look in the logs folder for lines beginning 'NSM launch diagnostic'.\r\n"
    )
    with zipfile.ZipFile(OUT_ZIP, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("NSM-Client/DIAGNOSTIC-NOTES.txt", note)
    with zipfile.ZipFile(OUT_ZIP) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f"package CRC failed at {bad}")
        sticky = z.read("NSM-Client/sticky.dll")
        if b"NSM launch diagnostic" not in sticky:
            raise SystemExit("diagnostic strings missing from packaged sticky.dll")
        if "NSM-Client/DIAGNOSTIC-NOTES.txt" not in z.namelist():
            raise SystemExit("diagnostic notes missing from package")

    # Upload a distinct asset; never delete or replace v0.7.4 or another asset.
    assets = api_get(f"/releases/{RELEASE_ID}/assets?per_page=100")
    if any(a["name"] == ASSET_NAME for a in assets):
        raise SystemExit(f"release already contains {ASSET_NAME}; refusing overwrite")
    sys.path.insert(0, str(ROOT / "branding"))
    os.environ["GH_TOKEN"] = TOKEN
    import package_phase1 as p
    p.upload(str(OUT_ZIP), ASSET_NAME)
    log(f"uploaded diagnostic asset to release {RELEASE_ID}: {ASSET_NAME}")
    OUT_ZIP.unlink()


if __name__ == "__main__":
    LOG.parent.mkdir(parents=True, exist_ok=True)
    wait_for_ci()
    build_package()
