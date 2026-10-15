#!/bin/bash
# Not-found diagnostics test: server ONLINE, packs\ exists, mp1.pack MISSING (user's scenario)
cd /home/user/nsm
export WINEDEBUG=-all
W=/usr/lib/wine/wine64
# --- services prefix (TEST MODE: started by this script, never by NSM) ---
S=wineprefix-svc
rm -rf $S wineprefix-nf; mkdir -p $S
WINEPREFIX=/home/user/nsm/$S $W wineboot -i >/dev/null 2>&1; sleep 2
mkdir -p $S/drive_c/svc/masterlist $S/drive_c/svc/server
cp mocks/mock_masterlist.exe $S/drive_c/svc/masterlist/masterlist.exe
cp mocks/mock_server.exe     $S/drive_c/svc/server/gtamp-server.exe
(cd $S/drive_c/svc/masterlist && WINEPREFIX=/home/user/nsm/$S $W masterlist.exe >/tmp/nf-ml.log 2>&1 &)
(cd $S/drive_c/svc/server     && WINEPREFIX=/home/user/nsm/$S $W gtamp-server.exe >/tmp/nf-srv.log 2>&1 &)
sleep 6
# --- launcher prefix ---
Xvfb :99 -screen 0 1600x1000x24 >/dev/null 2>&1 &
XV=$!
sleep 1
P=wineprefix-nf
mkdir -p $P
export DISPLAY=:99 WINEPREFIX=/home/user/nsm/$P
$W wineboot -i >/dev/null 2>&1
sleep 2
T=$P/drive_c/nsmtest/client-new
mkdir -p $T/packs
cp bin/NSM.exe bin/connect.exe bin/discord_rpc.dll mocks/discord_rpc_real.dll $T/
printf '218' > $T/steam_appid.txt
printf "gta_path = 'C:\\\\nsmtest\\\\fakeGTA'\n\nmasterlist_url = 'http://127.0.0.1:8080'\n\nembed_game_window = true\n" > $T/.config
# packs folder deliberately contains NO mp1.pack (user's scenario)
( cd $T && $W NSM.exe >/dev/null 2>&1 & )
sleep 14
curl -s -m 3 -X POST http://127.0.0.1:9987/api/connect -H "Content-Type: application/json" -d '{"host":"127.0.0.1","port":"7788","name":"NF Test"}' >/dev/null
sleep 10
CL=$P/drive_c/users/user/AppData/Local/39a4cb14b4afd8c1eef1667c74e3b5936238c44f/logs/connect.log
sed 's/\r//' "$CL" > /tmp/nf-clean.log
echo "=== LAST LOG LINES ==="
tail -14 /tmp/nf-clean.log
echo "=== CHECKS ==="
grep -q "NSM.exe is running from" /tmp/nf-clean.log && echo "CHECK1 running-from: OK" || echo "CHECK1 running-from: MISSING"
grep -q "Searched paths" /tmp/nf-clean.log && echo "CHECK2 searched-paths: OK" || echo "CHECK2 searched-paths: MISSING"
grep -qE "\(folder is EMPTY\)|cannot list dir|\.exe \(.*B\)" /tmp/nf-clean.log && echo "CHECK3 dir-listing: OK" || echo "CHECK3 dir-listing: MISSING"
kill $XV 2>/dev/null
pkill -x NSM.exe 2>/dev/null; pkill -x connect.exe 2>/dev/null
pkill -x masterlist.exe 2>/dev/null; pkill -x gtamp-server.exe 2>/dev/null
sleep 1
WINEPREFIX=/home/user/nsm/$S $W wineserver -k >/dev/null 2>&1
WINEPREFIX=/home/user/nsm/$P $W wineserver -k >/dev/null 2>&1
sleep 1
rm -rf $S $P
echo "DONE"
