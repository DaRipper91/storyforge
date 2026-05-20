"""
Android entry point for Buildozer.

Thin WebView client — connects to a StoryForge server on the LAN.
Falls back to the pywebview desktop GUI when not on Android.
"""
import os

try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.textinput import TextInput
    from kivy.uix.widget import Widget

    _PREFS_FILE = "/data/data/org.storyforge/files/server_url.txt"
    _DEFAULT_URL = "http://192.168.1.100:8765"

    def _load_url():
        try:
            if os.path.exists(_PREFS_FILE):
                with open(_PREFS_FILE) as f:
                    url = f.read().strip()
                if url:
                    return url
        except Exception:
            pass
        return _DEFAULT_URL

    def _save_url(url):
        try:
            os.makedirs(os.path.dirname(_PREFS_FILE), exist_ok=True)
            with open(_PREFS_FILE, "w") as f:
                f.write(url.strip())
        except Exception:
            pass

    @run_on_ui_thread
    def _open_webview(url):
        # autoclass calls must happen here (on UI thread, after app init)
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        wv = WebView(activity)
        settings = wv.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setAllowFileAccess(True)
        wv.setWebViewClient(WebViewClient())
        wv.loadUrl(url)
        activity.setContentView(wv)

    class ConnectScreen(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(orientation="vertical", padding=40, spacing=20, **kwargs)
            self.add_widget(Label(text="StoryForge", font_size="32sp", size_hint=(1, 0.2)))
            self.add_widget(Label(text="Enter server address:", size_hint=(1, 0.1)))
            self.url_input = TextInput(
                text=_load_url(),
                multiline=False,
                size_hint=(1, 0.15),
                font_size="18sp",
            )
            self.add_widget(self.url_input)
            btn = Button(text="Connect", size_hint=(1, 0.15), font_size="20sp")
            btn.bind(on_press=self.connect)
            self.add_widget(btn)
            self.add_widget(Widget())

        def connect(self, _):
            url = self.url_input.text.strip()
            _save_url(url)
            _open_webview(url)

    class StoryForgeApp(App):
        def build(self):
            return ConnectScreen()

    StoryForgeApp().run()

except Exception:
    # Desktop fallback — use pywebview GUI
    from storyforge.gui import main
    main()
