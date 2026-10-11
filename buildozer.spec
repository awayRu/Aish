[app]
title = AI Chat GameVerse Nexus Smooth
package.name = aichat
package.domain = org.aichat

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,gif,kv,atlas

# Public app release version and Android in-place update code.
version = 1.42
android.numeric_version = 42

requirements = python3,kivy==2.1.0,pyjnius,certifi,pillow,pypdf

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
