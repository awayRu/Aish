#!/usr/bin/env bash
set -euo pipefail

apk=$1
app=org.aichat.aichat
activity="$app/org.kivy.android.PythonActivity"
previous=$(mktemp --suffix=.apk)

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

curl -fL --retry 3 -o "$previous" 'https://github.com/awayRu/Aish/releases/download/v46/aichat-1.46-arm64-v8a-debug.apk'
adb install --no-streaming "$previous"
adb install --no-streaming -r "$apk"
launch_and_check
