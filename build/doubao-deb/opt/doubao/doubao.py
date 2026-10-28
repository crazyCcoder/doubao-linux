#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆包桌面客户端（Linux 版）

以原生窗口（GTK3 + WebKit2GTK）承载豆包网页版，对应 Windows 客户端
doubao_client 的桌面壳能力：会话保持、下载、外链跳转、快捷键。
"""

import os
import sys
import html
import urllib.parse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")

from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2

APP_ID = "com.doubao.Desktop"
HOME_URL = os.environ.get("DOUBAO_URL", "https://www.doubao.com/chat/")
ICON_PATH = "/usr/share/icons/hicolor/256x256/apps/doubao.png"
LOCAL_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doubao.png")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36 DoubaoDesktop/1.0.0"
)

ERROR_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#f6f7fb;color:#1f2329;font-family:"Noto Sans CJK SC","Source Han Sans SC",sans-serif}}
.box{{text-align:center}}
h1{{font-size:20px;font-weight:600;margin:0 0 12px}}
p{{font-size:14px;color:#646a73;margin:0 0 24px}}
a{{display:inline-block;padding:9px 28px;border-radius:6px;background:#1664ff;color:#fff;
text-decoration:none;font-size:14px}}
</style></head><body><div class="box">
<h1>暂时无法加载豆包</h1>
<p>{reason}</p><a href="{url}">重新加载</a>
</div></body></html>"""


class DoubaoWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="豆包")
        self.set_default_size(1280, 820)
        self.set_position(Gtk.WindowPosition.CENTER)
        self._error_shown = False

        icon = ICON_PATH if os.path.exists(ICON_PATH) else LOCAL_ICON
        if os.path.exists(icon):
            try:
                self.set_icon_from_file(icon)
            except GLib.Error:
                pass

        self.view = WebKit2.WebView()
        settings = self.view.get_settings()
        settings.set_user_agent(UA)
        settings.set_property("enable-page-cache", True)
        settings.set_property("enable-webgl", True)
        settings.set_property("enable-media-stream", True)
        settings.set_property("enable-mediasource", True)
        settings.set_property("javascript-can-open-windows-automatically", False)
        settings.set_property("allow-file-access-from-file-urls", False)

        self.view.connect("load-failed", self._on_load_failed)
        self.view.connect("load-changed", self._on_load_changed)
        self.view.connect("create", self._on_create)
        self.view.connect("permission-request", self._on_permission_request)

        context = self.view.get_context()
        context.connect("download-started", self._on_download_started)

        self.add(self.view)
        self.show_all()
        self.view.grab_focus()
        self.view.load_uri(HOME_URL)

    # ---- 导航与错误处理 ----
    def _on_load_changed(self, view, event):
        if event == WebKit2.LoadEvent.FINISHED:
            self._error_shown = False

    def _on_load_failed(self, view, event, uri, error):
        if self._error_shown:
            return True
        self._error_shown = True
        reason = html.escape(error.message or "网络连接失败")
        view.load_html(ERROR_PAGE.format(reason=reason, url=HOME_URL), HOME_URL)
        return True

    def _on_create(self, view, navigation_action):
        request = navigation_action.get_request()
        uri = request.get_uri() or ""
        if "doubao.com" in uri:
            view.load_uri(uri)
        elif uri.startswith(("http://", "https://")):
            Gio.AppInfo.launch_default_for_uri(uri, None)
        return None

    def _on_permission_request(self, view, request):
        if not isinstance(request, WebKit2.UserMediaPermissionRequest):
            return False
        origin = view.get_uri() or ""
        if origin.startswith("https://www.doubao.com"):
            request.allow()
        else:
            request.deny()
        return True

    # ---- 下载 ----
    def _on_download_started(self, context, download):
        chooser = Gtk.FileChooserDialog(
            title="保存文件",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        chooser.add_buttons(
            "取消", Gtk.ResponseType.CANCEL, "保存", Gtk.ResponseType.ACCEPT
        )
        chooser.set_do_overwrite_confirmation(True)
        chooser.set_current_name(self._download_name(download))
        response = chooser.run()
        name = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.ACCEPT and name:
            download.set_destination(name)
        else:
            download.cancel()

    @staticmethod
    def _download_name(download):
        getter = getattr(download, "get_suggested_filename", None)
        if getter is not None:
            try:
                name = getter()
                if name:
                    return name
            except Exception:
                pass
        request = download.get_request()
        path = urllib.parse.unquote(urllib.parse.urlparse(request.get_uri() or "").path)
        return os.path.basename(path) or "doubao-download"

    # ---- 快捷键 ----
    def reload_page(self):
        self._error_shown = False
        self.view.reload()

    def go_home(self):
        self._error_shown = False
        self.view.load_uri(HOME_URL)

    def zoom(self, delta):
        if delta == 0:
            self.view.set_zoom_level(1.0)
        else:
            level = min(3.0, max(0.5, self.view.get_zoom_level() + delta))
            self.view.set_zoom_level(level)


class DoubaoApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        actions = [
            ("reload", self._reload, ["<Control>r", "<Control>F5"]),
            ("home", self._home, ["<Alt>Home"]),
            ("zoom-in", lambda: self.window and self.window.zoom(0.1), ["<Control>plus"]),
            ("zoom-out", lambda: self.window and self.window.zoom(-0.1), ["<Control>minus"]),
            ("zoom-reset", lambda: self.window and self.window.zoom(0), ["<Control>0"]),
            ("quit", lambda: self.quit(), ["<Control>q"]),
        ]
        for name, callback, accels in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_: callback())
            self.add_action(action)
            self.set_accels_for_action("app." + name, accels)

    def _reload(self):
        if self.window:
            self.window.reload_page()

    def _home(self):
        if self.window:
            self.window.go_home()

    def do_activate(self):
        if self.window is None:
            self.window = DoubaoWindow(self)
            self.window.connect("destroy", self._on_window_destroy)
        self.window.present()

    def _on_window_destroy(self, _window):
        self.window = None


def main():
    GLib.set_prgname("doubao")
    Gdk.set_program_class("doubao")
    GLib.set_application_name("豆包")
    Gtk.init(None)
    app = DoubaoApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
