"""Use the correctly typed FreeType finalizers in SDL_ttf's pinned HarfBuzz."""

from pythonforandroid.recipes.sdl2_ttf import LibSDL2TTF


class AndroidSDL2TTFRecipe(LibSDL2TTF):
    patches = ["harfbuzz-finalizers.patch"]


recipe = AndroidSDL2TTFRecipe()
