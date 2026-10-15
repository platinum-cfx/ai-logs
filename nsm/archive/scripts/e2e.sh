#!/bin/bash
# E2E: NSM.exe full flow under Wine with mocks.
set -u
cd /home/user/nsm
WINE=/usr/lib/wine/wine64
export WINEPREFIX=/home/user/nsm/wineprefix WINEDEBUG=-all DISPLAY=:99 WINEDLLOVERRIDES="mscoree=d;mshtml=d"

echo "== init wine prefix"
rm -rf wineprefix e2e_result.txt
mkdir -p wineprefix
Xvfb :99 -screen 0 1600x1000x24 >/dev/null 2>&1 &
XVFB_PID=$!
sleep 1
$WINE wineboot -i >/dev/null 2>&1
sleep 2

C="wineprefix/drive_c"
T="$C/nsmtest"
mkdir -p "$T/client-new/packs" "$T/server" "$T/masterlist" "$T/fakeGTA" "$T/altv-runtime/39a4cb14b4afd8c1eef1667c74e3b5936238c44f/libs"

# client-new = the launcher folder (as shipped in the ZIP)
cp build/NSM.exe build/connect.exe build/discord_rpc.dll mocks/discord_rpc_real.dll "$T/client-new/"
cp build/packs/*.pack "$T/client-new/packs/"
printf '218' > "$T/client-new/steam_appid.txt"
cat > "$T/client-new/.config" <<'EOF'
gta_path = 'C:\nsmtest\fakeGTA'

masterlist_url = 'http://127.0.0.1:8080'

# Show the game inside the NSM window (false = GTA V opens in its own window)
embed_game_window = true
EOF

# server + masterlist folders (as in the ZIP)
cp mocks/mock_server.exe "$T/server/gtamp-server.exe"
cp mocks/mock_masterlist.exe "$T/masterlist/masterlist.exe"

# altv-runtime folder (as in the ZIP) - mock engine + mock game
RT="$T/altv-runtime/39a4cb14b4afd8c1eef1667c74e3b5936238c44f"
cp mocks/altv.exe mocks/GTA5.exe "$RT/"
printf 'timeout = 30' > "$RT/altv.toml"
printf 'dummy' > "$RT/libs/libce2.dll"

# fake GTA install for gta_path validation (file only, never run)
printf 'dummy-gta5' > "$T/fakeGTA/GTA5.exe"

echo "== start NSM.exe"
cd "$T/client-new"
$WINE NSM.exe > /tmp/nsm_stdout.log 2>&1 &
NSM_PID=$!
cd /home/user/nsm

echo "== wait for launcher API (port 9987)"
API=0
for i in $(seq 1 40); do
  if curl -s -m 2 http://127.0.0.1:9987/api/gamestate >/dev/null 2>&1; then API=1; break; fi
  sleep 1
done
echo "API up: $API"
[ "$API" = "1" ] || { echo "FAIL: launcher API never came up"; cat /tmp/nsm_stdout.log | tail -20; kill $XVFB_PID; exit 1; }
curl -s http://127.0.0.1:9987/api/gamestate; echo

echo "== POST connect (this drives the whole flow)"
curl -s -X POST http://127.0.0.1:9987/api/connect -H "Content-Type: application/json" -d '{"host":"127.0.0.1","port":"7788","name":"Local Test Server"}'; echo

echo "== poll for outcomes (up to 120s)"
CL="wineprefix/drive_c/users/$USER/AppData/Local/39a4cb14b4afd8c1eef1667c74e3b5936238c44f/logs/connect.log"
for i in $(seq 1 120); do
  if [ -f "$CL" ] && grep -q "Launching:" "$CL" 2>/dev/null && grep -q "game exited\|embed: DONE" "$T/client-new/nsm-embed-debug.log" 2>/dev/null; then break; fi
  sleep 1
done

echo "===== connect.log ====="
cat "$CL" 2>/dev/null
echo "===== nsm-embed-debug.log ====="
cat "$T/client-new/nsm-embed-debug.log" 2>/dev/null
echo "===== installed runtime (targetDir) ====="
ls "$(dirname "$(dirname "$CL")")" 2>/dev/null | head -15
echo "===== state after ====="
sleep 2; curl -s http://127.0.0.1:9987/api/gamestate 2>/dev/null; echo

# save results, clean up
kill $NSM_PID 2>/dev/null
pkill -f mock_server 2>/dev/null; pkill -f mock_masterlist 2>/dev/null
wineserver -k 2>/dev/null
kill $XVFB_PID 2>/dev/null
echo "E2E_SCRIPT_DONE"
