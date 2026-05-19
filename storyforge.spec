# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Paths are relative to the location of the spec file
frontend_path = ('frontend', 'frontend')
prompts_path = ('src/storyforge/ai/prompts', 'src/storyforge/ai/prompts')
seeds_path = ('data/seeds', 'data/seeds')

added_files = [
    frontend_path,
    prompts_path,
    seeds_path,
]

a = Analysis(
    ['src/storyforge/desktop.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan.on',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'fastapi',
        'websockets.legacy.server',
        'storyforge.api.routes_state',
        'storyforge.api.routes_action',
        'storyforge.api.routes_lobby',
        'storyforge.api.ws_session',
        'google.genai',
        'pydantic_settings',
        'webview.platforms.winforms',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StoryForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='frontend/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StoryForge',
)
