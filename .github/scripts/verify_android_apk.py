"""Check Android native libraries and assets before releasing the APK."""

from io import BytesIO
from pathlib import Path
import struct
import sys
import tarfile
from zipfile import ZipFile


def verify_arm64_alignment(name, library):
    if library[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", library, 18)[0] != 183:
        raise ValueError(f"Expected a 64-bit ARM ELF library in {name}")
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
        for arch, machine in (("arm64-v8a", 183), ("armeabi-v7a", 40)):
            prefix = f"lib/{arch}/"
            for name in ("libmain.so", "libSDL2.so", "libpython3.11.so", "libwebp.so", "libwebpdemux.so"):
                library = apk.read(prefix + name)
                if library[:4] != b"\x7fELF" or struct.unpack_from("<H", library, 18)[0] != machine:
                    raise ValueError(f"Wrong CPU architecture for {prefix + name}")
            with tarfile.open(fileobj=BytesIO(apk.read(prefix + "libpybundle.so")), mode="r:*") as python:
                libraries = [member for member in python.getmembers() if member.isfile() and member.name.endswith(".so")]
                if not any("/PIL/_webp" in member.name for member in libraries):
                    raise ValueError(f"The Python WebP decoder for {arch} is missing")
                if arch == "arm64-v8a":
                    for member in libraries:
                        verify_arm64_alignment(member.name, python.extractfile(member).read())
        for entry in apk.namelist():
            if entry.startswith("lib/arm64-v8a/") and entry.endswith(".so") and not entry.endswith("/libpybundle.so"):
                verify_arm64_alignment(entry, apk.read(entry))
        with tarfile.open(fileobj=BytesIO(apk.read("assets/private.tar")), mode="r:*") as app:
            for name in ("Inter-Regular.ttf", "Inter-Bold.ttf", "aish-glass-reference.png"):
                if app.extractfile(f"assets/{name}").read() != (Path("assets") / name).read_bytes():
                    raise ValueError(f"Bundled asset differs from source: {name}")
    print("Verified both ARM architectures, 16 KB ARM64 ELF alignment, WebP codecs, and UI assets.")


if __name__ == "__main__":
    verify(sys.argv[1])
