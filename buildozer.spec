[app]
title = AI Chat
package.name = aichat
package.domain = org.aichat

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

# ИСПРАВЛЕНО: добавлен jnius с указанием версии
requirements = python3,kivy==2.2.1,jnius>=1.4.0

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
# ИСПРАВЛЕНО: добавлена версия build tools
android.build_tools_version = 33.0.2

[buildozer]
log_level = 2
warn_on_root = 1
