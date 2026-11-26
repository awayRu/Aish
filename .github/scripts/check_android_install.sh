#!/usr/bin/env bash
set -euo pipefail

apk=$1
app=org.aichat.aichat
activity="$app/org.kivy.android.PythonActivity"
previous=$(mktemp --suffix=.apk)
trap 'rm -f "$previous"' EXIT
# This job owns a fresh emulator. Never remove a pre-existing installation.
[[ "$(adb shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ||
   "$(adb shell getprop ro.boot.qemu | tr -d '\r')" == 1 ]]
if adb shell pm path "$app" | grep -q '^package:'; then
  echo "Aish is already installed on this device. Use an empty test emulator."
  exit 1
fi

launch_and_check() {
  adb logcat -c
  adb shell am start -W -n "$activity"
  local pid
  for _ in $(seq 1 45); do
    pid=$(adb shell pidof -s "$app" 2>/dev/null | tr -d '\r' || true)
    if [[ -n "$pid" ]] && adb logcat -d --pid="$pid" | grep -F 'Start application main loop' > /dev/null; then
      echo "Aish started successfully under Android (PID $pid)."
      return
    fi
    sleep 2
  done
  adb logcat -d -s python AndroidRuntime ActivityManager
  return 1
}

adb shell getprop ro.product.cpu.abilist
adb install --no-streaming "$apk"
launch_and_check
adb uninstall "$app"

curl -fL --retry 3 -o "$previous" 'https://github.com/awayRu/Aish/releases/download/v50/Aish-v50-Android.apk'
printf '%s  %s\n' 'fb6a3856357480c02b12ffb0f431080a86239c0951a5bad887d325cd779f3686' "$previous" | sha256sum -c -
adb install --no-streaming "$previous"
launch_and_check
adb shell am force-stop "$app"
adb root
adb wait-for-device
[[ "$(adb shell id -u | tr -d '\r')" == 0 ]]
data="/data/user/0/$app/files/aish-data"
# Release APKs are not debuggable. The Google APIs emulator's root shell can run as the fixture owner.
owner=$(adb shell stat -c %u "$data/chat.db" | tr -d '\r')
[[ "$owner" =~ ^[0-9]+$ && "$owner" -ge 10000 ]]
adb shell -T "su $owner sqlite3 $data/chat.db" <<'SQL'
.bail on
INSERT INTO notes(text, ts) VALUES ('Aish upgrade fixture', '2026-01-01 00:00:00');
SQL
adb shell "su $owner sh -c 'echo Aish-media-fixture > $data/images/upgrade-fixture.txt'"
adb install --no-streaming -r "$apk"
launch_and_check
adb shell am force-stop "$app"
note_count=$(adb shell -T "sqlite3 -readonly $data/chat.db" <<<"SELECT COUNT(*) FROM notes WHERE text='Aish upgrade fixture';")
[[ "${note_count//$'\r'/}" == 1 ]]
[[ "$(adb shell cat "$data/images/upgrade-fixture.txt" | tr -d '\r')" == Aish-media-fixture ]]
old_extension="/data/user/0/$app/files/app/_python_bundle/site-packages/chardet/_kernel.so"
adb shell "test ! -e $old_extension"
echo 'The v50 note and attachment survived replacement and startup.'
