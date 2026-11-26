"""Package the complete WebP decoder for the pinned Android toolchain."""

from os import cpu_count
from pathlib import Path

import sh
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import shprint


class LibwebpRecipe(Recipe):
    version = "1.6.0"
    url = "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-{version}.tar.gz"
    built_libraries = dict.fromkeys(
        ("libwebp.so", "libwebpdecoder.so", "libwebpdemux.so", "libwebpmux.so", "libsharpyuv.so"),
        "installation/lib",
    )

    def build_arch(self, arch):
        source = Path(self.get_build_dir(arch.arch))
        build = source / "build"
        installation = source / "installation"
        toolchain = Path(self.ctx.ndk_dir) / "build" / "cmake" / "android.toolchain.cmake"
        env = self.get_recipe_env(arch)
        shprint(
            sh.cmake, "-S", str(source), "-B", str(build),
            f"-DANDROID_ABI={arch.arch}", f"-DANDROID_PLATFORM=android-{self.ctx.ndk_api}",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}", f"-DCMAKE_INSTALL_PREFIX={installation}",
            "-DCMAKE_INSTALL_LIBDIR=lib", "-DBUILD_SHARED_LIBS=ON", "-DCMAKE_BUILD_TYPE=Release",
            "-DWEBP_BUILD_ANIM_UTILS=OFF", "-DWEBP_BUILD_CWEBP=OFF", "-DWEBP_BUILD_DWEBP=OFF",
            "-DWEBP_BUILD_GIF2WEBP=OFF", "-DWEBP_BUILD_IMG2WEBP=OFF", "-DWEBP_BUILD_VWEBP=OFF",
            "-DWEBP_BUILD_WEBPINFO=OFF", "-DWEBP_BUILD_WEBPMUX=OFF", "-DWEBP_BUILD_EXTRAS=OFF",
            _env=env,
        )
        shprint(sh.cmake, "--build", str(build), "--parallel", str(cpu_count() or 2), _env=env)
        shprint(sh.cmake, "--install", str(build), _env=env)


recipe = LibwebpRecipe()
