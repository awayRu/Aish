"""Backport SDL's Android sensor polling fix to the pinned SDL2 recipe."""

from pythonforandroid.recipes.sdl2 import LibSDL2Recipe


class AndroidSDL2Recipe(LibSDL2Recipe):
    patches = ["android-sensor-poll-once.patch"]


recipe = AndroidSDL2Recipe()
