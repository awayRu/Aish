[app]
title = Aish
package.name = aichat
package.domain = org.aichat

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,gif,kv,atlas,ttf,txt
source.exclude_dirs = .github,android_recipes
source.exclude_patterns = android_build_hook.py,windows_launcher.py

# Public app release version and Android in-place update code.
version = 1.52
android.numeric_version = 52

# p4a installs pip requirements on the build host with --no-deps.
# These universal wheels avoid host-native extensions and supply the Requests codecs.
requirements = chardet==5.2.0,charset-normalizer==2.1.1,python3,kivy==2.1.0,pyjnius,plyer,certifi,libwebp==1.6.0,pillow,pypdf

orientation = portrait, landscape
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24
android.archs = arm64-v8a,armeabi-v7a
android.release_artifact = apk
android.accept_sdk_license = True

p4a.branch = v2024.01.21
p4a.hook = android_build_hook.py
p4a.local_recipes = android_recipes

[buildozer]
log_level = 2
warn_on_root = 1
