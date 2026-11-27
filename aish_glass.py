"""Jade materials sampled from the approved Aish design."""

from dataclasses import dataclass
from functools import lru_cache
from math import exp, sin

from kivy.graphics.texture import Texture


@dataclass(frozen=True)
class Material:
    reflection: tuple
    deep_green: float
    top_light: float
    lower_light: float
    rim: float


MATERIALS = {
    "frosted": Material((143, 203, 189), .28, .13, .10, .15),
    "field": Material((162, 215, 202), .25, .17, .12, .20),
    "emerald": Material((142, 245, 198), .40, .33, .29, .45),
    "lit": Material((163, 255, 217), .54, .28, .48, .85),
    "mint": Material((191, 255, 230), .12, .44, .06, .43),
    "settings": Material((143, 203, 189), .21, .09, .12, .12),
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
        for col in range(width):
            x = col / (width - 1)
            shade = .32 + .68 * exp(-((y - .50) / .35) ** 2)
            key = exp(-((y - 1) / .23) ** 2 - ((x - .14) / .65) ** 2)
            bounce = exp(-(y / .23) ** 2 - ((x - .82) / .61) ** 2)
            side = exp(-(x / .075) ** 2) * exp(-((y - .48) / .47) ** 2)
            reflection = material.top_light * key + material.lower_light * bounce
            reflection += .20 * material.lower_light * side
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
            highlight = exp(-((x - .14) / .35) ** 2 - ((y - 1) / .28) ** 2)
            bounce = exp(-((x - .74) / .54) ** 2 - (y / .24) ** 2)
            alpha = material.rim * (.16 + .84 * max(highlight, bounce))
            pixels.extend((*material.reflection, round(alpha * 255)))
    return texture_from_rgba(width, height, pixels)


@lru_cache(maxsize=2)
def liquid_backdrop(footer=False):
    """Model the folded glass ribbons behind the home emblem and settings."""
    width, height = 480, 224
    pixels = bytearray()
    for row in range(height):
        y = row / (height - 1)
        for col in range(width):
            x = col / (width - 1)
            if footer:
                crest = .03 + .47 * x + .24 * sin(4.8 * x - .41)
                thickness = .13 + .10 * sin(3.2 * x)
                upper = crest + thickness
                focus = .29 + .71 * exp(-((x - .50) / .40) ** 2)
                light = .45
            else:
                crest = .28 + .105 * sin(7.7 * x - .21) + .078 * x
                thickness = .082 + .063 * sin(6.2 * x + .55) ** 2
                upper = crest + thickness
                focus = .26 + .74 * (exp(-((x - .08) / .20) ** 2) + .70 * exp(-((x - .90) / .16) ** 2))
                light = .61
            body = exp(-((y - (crest + thickness * .26)) / (thickness * .81)) ** 2)
            edge = exp(-((y - crest) / (.009 + .004 * x)) ** 2)
            inner = exp(-((y - upper) / .019) ** 2)
            spill = exp(-((y - crest - .025) / .115) ** 2)
            rear = exp(-((y - (.64 + .25 * sin(3.4 * x - .47))) / .065) ** 2)
            rear *= exp(-((x - .69) / .39) ** 2)
            alpha = (.56 * body + .31 * edge + .16 * inner + .19 * spill) * focus
            alpha += .18 * rear if not footer else 0
            alpha *= min(1, y * 9, (1 - y) * 8)
            shine = min(1, (edge * .67 + inner * .36 + body * .16) * focus)
            pixels.extend((round(21 + 140 * shine), round(102 + 143 * shine),
                           round(80 + 119 * shine), round(min(1, alpha * (1 + light)) * 255)))
    return texture_from_rgba(width, height, pixels)
