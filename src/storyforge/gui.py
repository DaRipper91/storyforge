import threading
import time
import socket
import uvicorn
import webview
from webview.menu import Menu, MenuAction, MenuSeparator
from storyforge.main import app


class StoryForgeAPI:
    """Exposed to JS as window.pywebview.api.*"""

    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def quit(self):
        if self._window:
            self._window.destroy()

    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()

    def minimize(self):
        if self._window:
            self._window.minimize()

    def open_controls(self):
        if self._window:
            self._window.evaluate_js("window.toggleKeymap && window.toggleKeymap()")

    def reload(self):
        if self._window:
            self._window.evaluate_js("window.location.reload()")


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_server(port):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    port = find_free_port()

    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    time.sleep(2)

    api = StoryForgeAPI()
    window = webview.create_window(
        "StoryForge",
        f"http://127.0.0.1:{port}",
        width=1280,
        height=800,
        min_size=(800, 600),
        js_api=api,
    )
    api.set_window(window)
    window.events.loaded += lambda: window.maximize()

    menu = [
        Menu("File", [
            MenuAction("Reload / New Game", api.reload),
            MenuSeparator(),
            MenuAction("Quit", api.quit),
        ]),
        Menu("View", [
            MenuAction("Toggle Fullscreen", api.toggle_fullscreen),
            MenuAction("Minimize", api.minimize),
        ]),
        Menu("Help", [
            MenuAction("Show Controls", api.open_controls),
        ]),
    ]

    webview.start(menu=menu)


if __name__ == "__main__":
    main()
