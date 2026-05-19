[app]
title = StoryForge
package.name = storyforge
package.domain = org.storyforge
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,js,css,html,svg,md,json
source.include_patterns = data/*,frontend/*,src/*
version = 0.1.0
requirements = python3,kivy,fastapi,uvicorn,pydantic,pydantic-settings,google-genai,websockets,python-multipart,pywebview,android
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a
android.permissions = INTERNET
# Note: FastAPI on Android requires uvicorn and some networking setup.
# This spec assumes the main.py or a wrapper can run under python-for-android.
python-for-android.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
