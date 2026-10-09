[app]
title = AI Chat
package.name = aichat
package.domain = org.aichat

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

# --- Ключевые зависимости для решения проблем ---
requirements = python3,kivy==2.2.1,pyjnius

# --- Настройки Android ---
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 31
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
