[app]
title = StoryForge
package.name = storyforge
package.domain = org.storyforge
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,res/xml/*
version = 0.1.0
icon.filename = %(source.dir)s/icon.png

# Thin WebView client — server runs on desktop/LAN, not bundled in the APK.
requirements = python3,kivy,android

orientation = landscape
fullscreen = 1
android.archs = arm64-v8a
android.permissions = INTERNET
android.manifest.application.usesCleartextTraffic = True
android.res_dir = res/
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
