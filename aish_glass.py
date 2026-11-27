"""Jade materials sampled from the approved Aish design."""

from dataclasses import dataclass
from functools import lru_cache
from math import exp
from pathlib import Path

from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture


ASSETS = Path(__file__).resolve().parent / "assets"


@dataclass(frozen=True)
class Material:
    reflection: tuple
    deep_green: float
    top_light: float
    lower_light: float
    rim: float


MATERIALS = {
    "frosted": Material((139, 202, 183), .28, .15, .11, .13),
    "field": Material((161, 212, 197), .20, .19, .17, .22),
    "emerald": Material((130, 242, 190), .42, .32, .38, .38),
    "lit": Material((144, 254, 200), .52, .37, .70, .88),
    "mint": Material((169, 254, 222), .24, .76, .12, .30),
    "settings": Material((137, 194, 177), .20, .082, .13, .11),
    "shortcut": Material((154, 208, 193), .34, .24, .24, .22),
    "history": Material((128, 205, 186), .22, .16, .13, .10),
    "badge": Material((117, 248, 188), .40, .21, .43, .29),
    "answer": Material((141, 217, 195), .26, .15, .20, .14),
    "profile": Material((136, 245, 194), .38, .29, .39, .21),
    "control": Material((160, 217, 199), .37, .21, .20, .22),
    "nav": Material((136, 205, 182), .22, .15, .07, .10),
    "nav-selected": Material((104, 238, 177), .36, .42, .06, .11),
    "composer": Material((131, 189, 171), .28, .19, .21, .12),
    "switch": Material((169, 249, 207), .36, .55, .04, .23),
    "thumb": Material((235, 255, 248), .07, .72, .04, .29),
}


def texture_from_rgba(width, height, pixels):
    texture = Texture.create(size=(width, height), colorfmt="rgba")
    texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
    return texture


@lru_cache(maxsize=len(MATERIALS))
def glass_film(name):
    """Bake the transmitted shade and reflected light once per material."""
    material = MATERIALS[name]
    width, height = 96, 64
    pixels = bytearray()
    for row in range(height):
        y = row / (height - 1)
        if name in ("mint", "switch", "thumb", "nav-selected"):
            y = 1 - y
        for col in range(width):
            x = col / (width - 1)
            shade = .22 + .78 * exp(-((y - .44) / .33) ** 2 - ((x - .56) / .64) ** 2)
            key = exp(-((y - 1.03 + .067 * x) / .20) ** 2 - ((x - .16) / .77) ** 2)
            focus = .42 if name in ("lit", "badge") else .83
            lower_falloff = .15 if name in ("lit", "shortcut") else .19
            bounce = exp(-(y / lower_falloff) ** 2 - ((x - focus) / .62) ** 2)
            side = exp(-(x / .079) ** 2) * exp(-((y - .53) / .49) ** 2)
            reflection = material.top_light * key + material.lower_light * bounce
            reflection += .29 * material.lower_light * side
            reflection += material.top_light * .13 * exp(-((y - .81 + .24 * x) / .12) ** 2)
            if name in ("lit", "shortcut"):
                reflected_edge = exp(-((y - .052) / .046) ** 2 - ((x - .46) / .53) ** 2)
                reflection += .23 * material.lower_light * reflected_edge
            reflection = min(.87, reflection)
            tint = material.deep_green * shade
            alpha = tint + reflection * (1 - tint)
            rgb = tuple(round((dark * tint + light * reflection * (1 - tint)) / alpha)
                        for dark, light in zip((0, 15, 12), material.reflection))
            pixels.extend((*rgb, round(255 * alpha)))
    return texture_from_rgba(width, height, pixels)


@lru_cache(maxsize=len(MATERIALS))
def edge_film(name):
    """The bevel catches light near the upper left and lower right."""
    material = MATERIALS[name]
    width, height = 64, 32
    pixels = bytearray()
    for row in range(height):
        y = row / (height - 1)
        for col in range(width):
            x = col / (width - 1)
            highlight = exp(-((x - .14) / .28) ** 2 - ((y - 1) / .30) ** 2)
            bounce = exp(-((x - .62) / .51) ** 2 - (y / .23) ** 2)
            alpha = material.rim * (.12 + .88 * max(highlight, bounce))
            pixels.extend((*material.reflection, round(alpha * 255)))
    return texture_from_rgba(width, height, pixels)


@lru_cache(maxsize=2)
def halo_film(shadow=False):
    pixels = bytearray()
    for row in range(32):
        height = row / 31
        intensity = .46 + .54 * exp(-((height - .24) / .53) ** 2)
        for column in range(64):
            distance = column / 63
            shade = (1 - distance) ** 2.7
            rgb = (0, 0, 0) if shadow else (57, 222, 155)
            pixels.extend((*rgb, round((132 if shadow else 108) * shade * intensity)))
    return texture_from_rgba(64, 32, pixels)


@lru_cache(maxsize=2)
def liquid_backdrop(footer=False):
    """Load the transparent decorative ribbon independently of the UI."""
    filename = "aish-settings-wave.png" if footer else "aish-home-wave.png"
    return CoreImage(str(ASSETS / filename)).texture
