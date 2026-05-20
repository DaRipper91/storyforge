"""
Android / desktop entry point for Buildozer.

On Android: starts FastAPI in a background thread, then displays the UI in a
native WebView via Kivy.
On desktop (ImportError from android.*): falls back to the pywebview gui.
"""
import socket
import threading
import time


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


PORT = 8765


def _run_server():
    import uvicorn
    from storyforge.main import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


server_thread = threading.Thread(target=_run_server, daemon=True)
server_thread.start()

try:
    from android.runnable import run_on_ui_thread  # noqa: E402  (Android only)
    from jnius import autoclass  # noqa: E402

    WebView = autoclass("android.webkit.WebView")
    WebViewClient = autoclass("android.webkit.WebViewClient")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")

    @run_on_ui_thread
    def _show_webview(dt=None):
        activity = PythonActivity.mActivity
        wv = WebView(activity)
        settings = wv.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setAllowFileAccess(True)
        wv.setWebViewClient(WebViewClient())
        wv.loadUrl(f"http://127.0.0.1:{PORT}")
        activity.setContentView(wv)

    from kivy.app import App  # noqa: E402
    from kivy.clock import Clock  # noqa: E402
    from kivy.uix.widget import Widget  # noqa: E402

    class StoryForgeApp(App):
        def build(self):
            Clock.schedule_once(_show_webview, 0.5)
            return Widget()

    StoryForgeApp().run()

except ImportError:
    # Desktop fallback — use pywebview gui
    from storyforge.gui import main
    main()
