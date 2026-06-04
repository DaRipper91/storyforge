@echo off
setlocal enabledelayedexpansion

echo ========================================
echo StoryForge Windows Build Script
echo ========================================

:: Check for uv
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 'uv' not found. Please install it from https://astral.sh/uv
    exit /b 1
)

echo [1/3] Syncing dependencies...
uv sync

echo [2/3] Building executable with PyInstaller...
uv run pyinstaller storyforge.spec --clean -y

echo [3/3] Checking for Inno Setup...
where iscc >nul 2>nul
if %ERRORLEVEL% eq 0 (
    echo Found Inno Setup, building installer...
    iscc storyforge.iss
) else (
    echo [INFO] Inno Setup (iscc) not found. 
    echo Skipping installer creation. You can still find the 
    echo standalone files in dist\StoryForge
)

echo.
echo ========================================
echo Done!
echo =%~dp0dist\StoryForge
echo ========================================
pause
