"""Check Android native libraries and assets before releasing the APK."""

from io import BytesIO
from pathlib import Path
import struct
import sys
import tarfile
from zipfile import ZipFile


def verify_library(name, library, arch):
    elf_class, machine = {"arm64-v8a": (2, 183), "armeabi-v7a": (1, 40)}[arch]
    if (library[:6] != b"\x7fELF" + bytes((elf_class, 1))
            or struct.unpack_from("<H", library, 18)[0] != machine):
        raise ValueError(f"Wrong ELF architecture for {arch}: {name}")
    if arch == "armeabi-v7a":
        return
    header_start = struct.unpack_from("<Q", library, 32)[0]
    header_size, header_count = struct.unpack_from("<HH", library, 54)
    for offset in range(header_start, header_start + header_size * header_count, header_size):
        kind, _, file_offset, address, _, _, _, alignment = struct.unpack_from("<IIQQQQQQ", library, offset)
        if kind == 1 and (alignment < 16384 or (file_offset - address) % 16384):
            raise ValueError(f"{name} has a load segment incompatible with 16 KB memory pages")


def verify(apk_path):
    with ZipFile(apk_path) as apk:
        damaged = apk.testzip()
        if damaged:
            raise ValueError(f"APK contains a damaged member: {damaged}")
        for arch in ("arm64-v8a", "armeabi-v7a"):
            prefix = f"lib/{arch}/"
            for name in ("libmain.so", "libSDL2.so", "libpython3.11.so", "libwebp.so", "libwebpdemux.so"):
                apk.getinfo(prefix + name)
            for entry in apk.namelist():
                if entry.startswith(prefix) and entry.endswith(".so") and entry != prefix + "libpybundle.so":
                    verify_library(entry, apk.read(entry), arch)
            with tarfile.open(fileobj=BytesIO(apk.read(prefix + "libpybundle.so")), mode="r:*") as python:
                libraries = [member for member in python.getmembers() if member.isfile() and member.name.endswith(".so")]
                if not any("/PIL/_webp" in member.name for member in libraries):
                    raise ValueError(f"The Python WebP decoder for {arch} is missing")
                for member in libraries:
                    verify_library(member.name, python.extractfile(member).read(), arch)
        with tarfile.open(fileobj=BytesIO(apk.read("assets/private.tar")), mode="r:*") as app:
            for name in ("Inter-Regular.ttf", "Inter-Bold.ttf", "aish-glass-reference.png"):
                if app.extractfile(f"assets/{name}").read() != (Path("assets") / name).read_bytes():
                    raise ValueError(f"Bundled asset differs from source: {name}")
    print("Verified both ARM architectures, 16 KB ARM64 ELF alignment, WebP codecs, and UI assets.")


if __name__ == "__main__":
    verify(sys.argv[1])
