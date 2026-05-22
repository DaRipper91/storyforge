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
    '--add-data=client_secret.json:.',
    '--collect-all=webview',
    '--collect-all=fastapi',
    '--collect-all=uvicorn',
]

# Add platform-specific options if needed
if platform.system() == 'Windows':
    pass # Icon conversion with SVG is failing on CI

PyInstaller.__main__.run(args)
