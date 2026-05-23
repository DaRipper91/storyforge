# StoryForge — Windows Setup Guide

This guide takes you from a fresh Windows machine to a running game server that your players can reach from any browser.

---

## What You Need

| Tool | Why |
|------|-----|
| Python 3.12+ | Runs the server |
| uv | Python package manager (replaces pip/venv) |
| Git | Downloads the project |
| ngrok | Gives your server a public URL players can reach |
| A Gemini API key | Powers the AI Dungeon Master |

---

## Step 1 — Install Prerequisites

Open **PowerShell as Administrator** for all commands in this guide.
Right-click the Start button → "Windows PowerShell (Admin)" or "Terminal (Admin)."

### Python 3.12+

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest Python 3.12 or 3.13 installer.
2. Run the installer. **Check "Add python.exe to PATH"** before clicking Install.
3. Verify: close and reopen PowerShell, then run:
   ```powershell
   python --version
   ```
   You should see `Python 3.12.x` or higher.

### uv (Package Manager)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell after this, then verify:
```powershell
uv --version
```

### Git

1. Download from [git-scm.com/download/win](https://git-scm.com/download/win).
2. Run the installer with default settings.
3. Verify:
   ```powershell
   git --version
   ```

---

## Step 2 — Get a Gemini API Key

1. Go to [aistudio.google.com](https://aistudio.google.com) and sign in with a Google account.
2. Click **"Get API key"** → **"Create API key"**.
3. Copy the key — you'll paste it in Step 4. It looks like: `AIzaSy...`

---

## Step 3 — Download StoryForge

Navigate to where you want the project folder (e.g., your Desktop or Documents):

```powershell
cd "$env:USERPROFILE\Desktop"
git clone https://github.com/DaRipper91/storyforge.git
cd storyforge
```

Install dependencies:
```powershell
uv sync
```

This takes about a minute the first time.

---

## Step 4 — Create the Config File

In the `storyforge` folder, create a file named `.env`. You can do this in PowerShell:

```powershell
notepad .env
```

Paste this into Notepad, filling in your key:

```
STORYFORGE_GEMINI_API_KEY=AIzaSy_PASTE_YOUR_KEY_HERE
STORYFORGE_CAMPAIGN_ID=family_campaign_01
```

Save and close Notepad. The `.env` file must be in the `storyforge` folder (same level as `pyproject.toml`).

---

## Step 5 — Start the Server

```powershell
uv run uvicorn storyforge.main:app --host 0.0.0.0 --port 8765
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8765 (Press CTRL+C to quit)
```

**Leave this window open.** The server must keep running for the game to work.

Test it locally — open a browser and go to:
```
http://localhost:8765
```

You should see the StoryForge title screen.

---

## Step 6 — Install ngrok

ngrok gives your server a public web address that players on other computers can reach.

1. Go to [ngrok.com](https://ngrok.com) and create a free account.
2. After signing in, go to **Your Authtoken** on the dashboard and copy it.
3. Download the Windows installer from [ngrok.com/download](https://ngrok.com/download).
4. Run the `.exe` installer (or extract the `.zip` — it's a single file). Move `ngrok.exe` somewhere easy to find, like `C:\ngrok\ngrok.exe`.
5. Add your authtoken (replace `YOUR_TOKEN` with what you copied):
   ```powershell
   C:\ngrok\ngrok.exe config add-authtoken YOUR_TOKEN_HERE
   ```

---

## Step 7 — Expose the Server with ngrok

Open a **second PowerShell window** (keep the server running in the first one).

```powershell
C:\ngrok\ngrok.exe http 8765
```

You'll see a screen like this:
```
Session Status                online
Account                       your@email.com (Plan: Free)
Forwarding                    https://a1b2c3d4.ngrok-free.app -> http://localhost:8765
```

**Copy the `https://...ngrok-free.app` URL** — this is what you give to players.

> **Note:** On the free plan, this URL changes every time you restart ngrok. You'll need to update the config file (Step 8) and share the new URL with players each session.

---

## Step 8 — Add the ngrok URL to Your Config

The server blocks requests from unknown origins for security. You need to tell it to allow your ngrok URL.

1. Stop the server with **Ctrl+C** in the first PowerShell window.
2. Open `.env` again:
   ```powershell
   notepad .env
   ```
3. Add the `STORYFORGE_ALLOWED_ORIGINS` line with your ngrok URL:
   ```
   STORYFORGE_GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE
   STORYFORGE_CAMPAIGN_ID=family_campaign_01
   STORYFORGE_ALLOWED_ORIGINS=http://localhost:8765 http://127.0.0.1:8765 https://a1b2c3d4.ngrok-free.app
   ```
   Replace `a1b2c3d4.ngrok-free.app` with your actual ngrok URL (without a trailing slash).
4. Save and close.
5. Restart the server:
   ```powershell
   uv run uvicorn storyforge.main:app --host 0.0.0.0 --port 8765
   ```

---

## Step 9 — Players Join

Share the ngrok URL with your players (e.g., via text or Discord):

```
https://a1b2c3d4.ngrok-free.app
```

Players open that URL in any modern browser (Chrome, Firefox, Edge) on any device — phone, tablet, or PC. No app install needed.

When a player opens the URL, ngrok may show a warning page first:
> "You are about to visit a site served by ngrok..."

Players click **"Visit Site"** to continue.

---

## Each Session — Quick Checklist

When you sit down to run a session, do this in order:

1. **Open PowerShell** in the `storyforge` folder:
   ```powershell
   cd "$env:USERPROFILE\Desktop\storyforge"
   ```

2. **Start ngrok** (new terminal window):
   ```powershell
   C:\ngrok\ngrok.exe http 8765
   ```

3. **Copy the new ngrok URL** from the ngrok window.

4. **Update `.env`** — replace the old ngrok URL in `STORYFORGE_ALLOWED_ORIGINS` with the new one.

5. **Start the server**:
   ```powershell
   uv run uvicorn storyforge.main:app --host 0.0.0.0 --port 8765
   ```

6. **Share the URL** with your players.

---

## Troubleshooting

**"python is not recognized"**
Reinstall Python and make sure to check "Add python.exe to PATH" during install. Then close and reopen PowerShell.

**"uv is not recognized"**
Close all PowerShell windows and open a fresh one. The installer updated your PATH but the old window doesn't see it.

**Server starts but the browser says "Cannot connect"**
Make sure you used `--host 0.0.0.0` when starting uvicorn, not `--host 127.0.0.1`.

**Players see a CORS error or a blank page after the ngrok warning**
The ngrok URL in your `.env` file doesn't match the one ngrok generated this session. Update `STORYFORGE_ALLOWED_ORIGINS` in `.env` and restart the server.

**ngrok warning page blocks players**
This is ngrok's free-tier browser warning. Players just click "Visit Site." It only appears once per browser session.

**"ModuleNotFoundError" or similar on server start**
Run `uv sync` again — a dependency may not have installed correctly.

**Campaign data location**
Save files are stored at `storyforge\data\campaigns\family_campaign_01\` on your machine. Back this folder up if you want to preserve your campaign between reinstalls.
