[app]
title = AI Chat
package.name = aichat
package.domain = org.aichat

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,db

version = 0.1
requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
