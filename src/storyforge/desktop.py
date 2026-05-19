import sys
import threading
import time
import uvicorn
import webview
import logging
from storyforge.main import app

# Suppress uvicorn logging to keep it clean
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)

def start_server():
    """Run the FastAPI backend in a background thread."""
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")

def main():
    """Main entrypoint for the desktop application."""
    # Start server thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Give the server a moment to start
    time.sleep(1.5)

    # Create and start the webview window
    window = webview.create_window(
        title="StoryForge",
        url="http://127.0.0.1:8765",
        width=1280,
        height=900,
        min_size=(1024, 768)
    )
    
    # This will block until the window is closed
    webview.start()

if __name__ == "__main__":
    main()
