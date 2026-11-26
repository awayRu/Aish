"""Launch the packaged app with separate test data and check that it shuts down cleanly."""

from contextlib import closing
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep


def find_window():
    handles = []
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def check(handle, _data):
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(handle, title, len(title))
        if title.value == "Aish" and user32.IsWindowVisible(handle):
            handles.append(handle)
        return True

    user32.EnumWindows(check, 0)
    return set(handles)


def smoke(exe):
    old = find_window()
    with TemporaryDirectory(prefix="aish-smoke-") as scratch:
        root = Path(scratch)
        env = dict(os.environ, AISH_DATA_DIR=str(root), KIVY_HOME=str(root / "kivy"))
        app = subprocess.Popen([str(exe)], env=env)
        window = None
        try:
            deadline = monotonic() + 35
            while monotonic() < deadline:
                if app.poll() is not None:
                    raise RuntimeError(f"Aish stopped during startup with status {app.returncode}.")
                added = find_window() - old
                if added and (root / "chat.db").is_file():
                    window = added.pop()
                    break
                sleep(.35)
            if window is None:
                error = root / "startup-error.log"
                raise RuntimeError(error.read_text(encoding="utf-8")[-2500:] if error.is_file() else "Aish did not open its window.")
            with closing(sqlite3.connect(root / "chat.db")) as db:
                assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            ctypes.windll.user32.PostMessageW(window, 0x10, 0, 0)
            if app.wait(timeout=20) != 0:
                raise RuntimeError(f"Aish stopped with status {app.returncode}.")
            print(f"{exe.name}: window, SQLite and graceful shutdown verified.")
        finally:
            if app.poll() is None:
                subprocess.run(["taskkill", "/PID", str(app.pid), "/T", "/F"], capture_output=True, check=False)
                app.wait(timeout=10)


if __name__ == "__main__":
    smoke(Path(sys.argv[1]).resolve(strict=True))
