"""Entry point for the Windows x64 distribution."""

import ctypes
import os
from pathlib import Path
import sys
import traceback


def run():
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    data_dir = Path(os.environ.setdefault("AISH_DATA_DIR", str(local_data / "Aish")))
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("KIVY_HOME", str(data_dir / "kivy"))
    os.environ.setdefault("KIVY_NO_ARGS", "1")

    try:
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except AttributeError:
            pass
        from kivy.config import Config

        Config.set("graphics", "width", "1032")
        Config.set("graphics", "height", "764")
        Config.set("graphics", "minimum_width", "350")
        Config.set("graphics", "minimum_height", "440")
        Config.set("graphics", "resizable", "1")
        from main import ChatApp

        ChatApp().run()
    except Exception:
        report = data_dir / "startup-error.log"
        report.write_text(traceback.format_exc(), encoding="utf-8")
        ctypes.windll.user32.MessageBoxW(None, f"Не удалось запустить Aish.\n\n{report}", "Aish", 0x10)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
