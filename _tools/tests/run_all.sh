#!/usr/bin/env bash
# كل اختبارات منصة العازي بأمر واحد. يشغّل المحاكي و http.server لو مطفيين (بـ setsid عشان ما يموتون مع نهاية الأمر).
#   bash _tools/tests/run_all.sh
cd "$(dirname "$0")/../.."
EMU=${EMU_DIR:-/tmp/emu}
if ! curl -s -m 3 localhost:9000 >/dev/null; then
  mkdir -p "$EMU" && [ -f "$EMU/firebase.json" ] || echo '{"database":{"rules":"rules.json"},"emulators":{"database":{"port":9000}}}' > "$EMU/firebase.json"
  [ -f "$EMU/rules.json" ] || echo '{"rules":{".read":true,".write":true}}' > "$EMU/rules.json"
  (cd "$EMU" && setsid firebase emulators:start --only database --project demo-el3 >/tmp/emu.log 2>&1 </dev/null &) >/dev/null 2>&1
  for i in $(seq 60); do curl -s -m 3 localhost:9000 >/dev/null && break; sleep 2; done
fi
curl -s -m 3 localhost:8765 >/dev/null || (setsid python3 -m http.server 8765 >/tmp/http.log 2>&1 </dev/null &)
sleep 1
fail=0
for t in test_scoring test_rules test_fans_build ui_mano ui_q ui_stat ui_grid test_bus; do
  r=$(python3 _tools/tests/$t.py 2>&1); line=$(echo "$r" | grep -E "^النتيجة" | tail -1)
  echo "$t: ${line:-❌ ما خلص (شوف الخطأ تحت)}"
  echo "$r" | grep -E "^❌" | head -5
  echo "$line" | grep -q " 0 فشل" || { fail=1; [ -z "$line" ] && echo "$r" | tail -5; }
done
rm -rf _tools/tests/__pycache__ _tools/*/__pycache__
exit $fail
