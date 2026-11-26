"""Package the Windows application and its SDL, Kivy, and image resources."""

import argparse
import importlib
import os
from pathlib import Path
import platform
import re
import sys


def build():
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("The Windows x64 package must be built with 64-bit Windows Python.")
    os.environ["KIVY_LOG_MODE"] = "PYTHON"
    # PyInstaller probes imports in child processes. Keep those probes off the GPU.
    os.environ["KIVY_GL_BACKEND"] = "mock"
    from PyInstaller.__main__ import run
    from kivy.tools.packaging.pyinstaller_hooks import hookspath
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default="bin")
    parser.add_argument("--work", default="build/windows")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    version = re.search(r'^APP_VERSION = "(\d+)"$', (root / "main.py").read_text(encoding="utf-8"), re.M)[1]
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    options = ["--noconfirm", "--onefile", "--windowed", "--noupx", "--log-level", "INFO", "--name", f"Aish-v{version}-Windows-x64",
               "--distpath", str(Path(args.dist).resolve()), "--workpath", str(work), "--specpath", str(work),
               "--add-data", f"{root / 'assets'}{os.pathsep}assets",
               "--add-data", f"{root / 'aish-welcome-art.png'}{os.pathsep}."]
    # The default PyInstaller Kivy hook opens a GL window to detect providers.
    # Specify the actual Windows providers so the package also builds on CI without graphics.
    for path in hookspath():
        options.extend(("--additional-hooks-dir", path))
    for provider in ("window.window_sdl2", "text.text_sdl2", "image.img_sdl2", "image.img_pil",
                     "image.img_tex", "clipboard.clipboard_winctypes", "clipboard.clipboard_sdl2"):
        options.extend(("--hidden-import", "kivy.core." + provider))
    for provider in ("sdl2", "glew", "angle"):
        dependency = importlib.import_module(f"kivy_deps.{provider}")
        paths = set(map(Path, dependency.dep_bins))
        paths.add(Path(dependency.__file__).resolve().parents[2] / "share" / provider / "bin")
        for binary in sorted({dll for path in paths for dll in path.glob("*.dll")}):
            options.extend(("--add-binary", f"{binary}{os.pathsep}."))
    run([*options, str(root / "windows_launcher.py")])


if __name__ == "__main__":
    build()
