import subprocess
import time
import os

process = subprocess.Popen(["uv", "run", "uvicorn", "storyforge.main:app", "--host", "127.0.0.1", "--port", "8765"], env={"STORYFORGE_GEMINI_API_KEY": "test_key", **os.environ})
time.sleep(5)
print("Server started")
