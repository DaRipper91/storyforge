import multiprocessing
import threading
import time
import socket
import sys
import os
import uvicorn
import webview
from storyforge.main import app

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def run_server(port):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

def main():
    # Use a free port to avoid collisions
    port = find_free_port()
    
    # Start the FastAPI server in a separate thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    
    # Wait a bit for the server to start
    time.sleep(2)
    
    # Create the webview window
    window = webview.create_window(
        'StoryForge', 
        f'http://127.0.0.1:{port}',
        width=1280,
        height=800,
        min_size=(800, 600)
    )
    
    # Start the webview
    webview.start()

if __name__ == '__main__':
    # On Windows, we need this for PyInstaller + multiprocessing
    multiprocessing.freeze_support()
    main()
