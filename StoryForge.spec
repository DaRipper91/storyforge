# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for StoryForge.exe — the unified desktop launcher.

Bundles the FastAPI brain (Python) into a single .exe. The Godot cinematic
client is a separate binary (StoryForge_client.exe) produced by the Godot
editor export step and placed alongside this launcher at release time.

Build:
    uv run python scripts/build.py
    # or directly:
    uv run pyinstaller StoryForge.spec
"""
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# ── Data files ──────────────────────────────────────────────────────
datas = [
    ('data/seeds', 'data/seeds'),
    ('src/storyforge/ai/prompts', 'storyforge/ai/prompts'),
]
if os.path.exists('client_secret.json'):
    datas.append(('client_secret.json', '.'))

# ── Hidden imports ───────────────────────────────────────────────────
hiddenimports = [
    # Pydantic v2 validators loaded at runtime
    'pydantic.deprecated.class_validators',
    'pydantic.deprecated.config',
    # Google auth transport
    'google.auth.transport.requests',
    'google.oauth2.id_token',
    'google.oauth2.credentials',
    'google.auth._default',
    # Uvicorn extras
    'uvicorn.logging',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan.on',
    # Storyforge encounters (dynamically imported by route modules)
    'storyforge.encounters.shopkeeper_jon',
    'storyforge.encounters.samael',
    'storyforge.encounters.haylie',
    'storyforge.encounters.queen_danna',
    'storyforge.encounters.redvelvet',
    'storyforge.encounters.kodrik',
    'storyforge.encounters.bryne',
    'storyforge.encounters.nathis',
    # JWT crypto backend
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.backends.openssl',
]

# ── Collected packages ───────────────────────────────────────────────
binaries = []

for pkg in ('fastapi', 'uvicorn', 'starlette', 'anyio', 'google.genai', 'websockets'):
    d, b, h = collect_all(pkg)
    datas    += d
    binaries += b
    hiddenimports += h

datas += collect_data_files('storyforge', subdir='ai/prompts')

# ── Analysis ─────────────────────────────────────────────────────────
a = Analysis(
    ['src/storyforge/launcher.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pywebview', 'webview', 'PyQt6', 'PyQt6WebEngine',
        'tkinter', 'matplotlib', 'numpy', 'PIL',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StoryForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
