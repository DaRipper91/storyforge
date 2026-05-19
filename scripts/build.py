import PyInstaller.__main__
import os
import platform

# Base PyInstaller command
args = [
    'src/storyforge/gui.py',
    '--name=StoryForge',
    '--onefile',
    '--windowed',
    '--add-data=frontend:frontend',
    '--add-data=data:data',
    '--add-data=src/storyforge/ai/prompts:storyforge/ai/prompts',
    '--collect-all=webview',
    '--collect-all=fastapi',
    '--collect-all=uvicorn',
]

# Add platform-specific icons or options if needed
if platform.system() == 'Windows':
    args.append('--icon=frontend/icon.svg') # Note: might need .ico for Windows

PyInstaller.__main__.run(args)
