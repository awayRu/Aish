"""Native controls and artwork rendering for the Aish interface."""
from functools import lru_cache
from math import cos, exp, pi, sin
from pathlib import Path
from weakref import WeakSet

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.graphics import (Canvas, Color, Ellipse, Line, Mesh, PopMatrix, PushMatrix,
                           Rectangle, RoundedRectangle, Scale, Triangle)
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex, platform
from aish_glass import edge_film, glass_film, halo_film, liquid_backdrop


ASSETS = Path(__file__).resolve().parent / "assets"
WORDMARK = "Aish"
UI_FONT = "Roboto"
if (ASSETS / "Inter-Regular.ttf").is_file() and (ASSETS / "Inter-Bold.ttf").is_file():
    UI_FONT = "AishInter"
    LabelBase.register(UI_FONT, fn_regular=str(ASSETS / "Inter-Regular.ttf"),
                       fn_bold=str(ASSETS / "Inter-Bold.ttf"))

PALETTE = {key: tuple(get_color_from_hex(value)) for key, value in {
    "bg_top": "#041110", "bg_bot": "#040f0e",
    "panel": "#0a1a18", "panel2": "#102725", "panel3": "#203632",
    "settings_panel": "#091817", "divider": "#1a2c28",
    "search_glass": "#142a27", "profile_glass": "#08201b",
    "history_glass": "#0a1f1b", "history_badge": "#164f3a",
    "switch_track": "#35906d", "switch_thumb": "#c4f8e2", "send": "#4bb089",
    "text": "#f8f8f8", "text_dim": "#c3ccca", "text_faint": "#9eaeaa",
    "accent": "#63c69e", "accent_text": "#06251b", "accent_soft": "#133c31",
    "bubble_me": "#0f3428", "bubble_ai": "#0a1917", "bubble_text": "#f8f8f8",
    "chip": "#0e2420", "chip_text": "#c4e8dc", "avatar_me": "#215742", "avatar_ai": "#0e392c",
    "ring_bg": "#315a4c", "danger": "#ff9c9e", "danger_bg": "#392227",
    "success": "#9ceecf", "success_bg": "#1a4238", "star": "#ffd080", "star_bg": "#342b1c",
    "online": "#9ceecf", "shadow": "#0000004d",
}.items()}
MINT_LIGHT = tuple(get_color_from_hex("#a7f2d8"))
EMBLEM_CROP = (30, 5, 249, 199)


def _rgba_texture(width, height, pixels):
    texture = Texture.create(size=(width, height), colorfmt="rgba")
    texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
    return texture


@lru_cache(maxsize=2)
def jade_waves(footer=False):
    """Two soft refracted ribbons with transparent edges for the jade screens."""
    width, height = 320, 150
    pixels = bytearray()
    for row in range(height):
        y = row / (height - 1)
        for column in range(width):
            x = column / (width - 1)
            if footer:
                ridge = .26 + .54 * x + .16 * sin(2 * pi * (x - .17))
            else:
                ridge = .34 + .19 * sin(2 * pi * (x - .05)) + .22 * x
            distance = y - ridge
            rim = exp(-(distance / .011) ** 2)
            face = exp(-((distance + .06) / .075) ** 2)
            halo = exp(-((distance - .04) / .16) ** 2)
            reflection = exp(-((distance + .21 + .08 * sin(x * 11)) / .055) ** 2)
            focus = .30 + .70 * (.5 + .5 * sin(x * 11 + .30))
            edge = min(1, y * 8, (1 - y) * 8)
            alpha = (.29 * rim + .64 * face + .21 * halo + .20 * reflection) * focus * edge
            pixels.extend((round(26 + 104 * rim), round(128 + 97 * rim),
                           round(102 + 96 * rim), round(min(1, alpha) * 255)))
    return _rgba_texture(width, height, pixels)


@lru_cache(maxsize=1)
def _glass_reflection():
    pixels = bytearray()
    for row in range(32):
        y = row / 31
        for column in range(32):
            x = column / 31
            light = .81 * exp(-((1 - y) / .22) ** 2) * (.22 + .78 * (1 - x))
            light += .57 * exp(-((y - .02) / .22) ** 2) * (.30 + .70 * x)
            pixels.extend((216, 255, 239, round(light * 255)))
    return _rgba_texture(32, 32, pixels)


@lru_cache(maxsize=1)
def _press_light():
    pixels = bytearray()
    for row in range(48):
        for col in range(48):
            distance_squared = ((row - 23.5) / 23.5) ** 2 + ((col - 23.5) / 23.5) ** 2
            alpha = max(0, 1 - distance_squared) ** 2
            pixels.extend((255, 255, 255, round(alpha * 255)))
    return _rgba_texture(48, 48, pixels)


_hoverable = WeakSet()
_pointer_bound = False
_effects_level = "full"


@lru_cache(maxsize=1)
def _android_haptic():
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    @run_on_ui_thread
    def tick():
        try:
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            activity.getWindow().getDecorView().performHapticFeedback(3)
        except Exception:
            pass

    return tick


def set_effects(level):
    global _effects_level
    _effects_level = level


def _pointer_move(_window, point):
    for control in tuple(_hoverable):
        hovered = bool(control.get_root_window() and control.opacity > 0 and not control.disabled
                       and control.collide_point(*control.to_widget(*point)))
        if control._hovered != hovered:
            control._hovered = hovered
            control._press_effect()


class PressFeedback:
    scale_feedback = NumericProperty(1)
    glow_feedback = NumericProperty(0)
    wave_feedback = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hovered = False
        self._wave_origin = (.5, .5)
        with self.canvas.before:
            PushMatrix()
            self._press_scale = Scale(1, 1, 1, origin=self.center)
        with self.canvas.after:
            self._press_ink = Color(*MINT_LIGHT[:3], 0)
            self._press_reflection = RoundedRectangle(texture=_glass_reflection(), radius=[dp(12)])
            self._wave_ink = Color(*MINT_LIGHT[:3], 0)
            self._press_wave = RoundedRectangle(texture=_press_light(), radius=[dp(12)])
            PopMatrix()
        self.bind(pos=self._place_feedback, size=self._place_feedback, state=self._press_effect,
                  parent=self._track_pointer, scale_feedback=self._paint_feedback,
                  glow_feedback=self._paint_feedback, wave_feedback=self._paint_feedback)
        if platform == "android":
            self.bind(on_press=self._touch_feedback)
        self._place_feedback()

    def _place_feedback(self, *_):
        self._press_scale.origin = self.center
        self._press_reflection.pos = self._press_wave.pos = self.pos
        self._press_reflection.size = self._press_wave.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.width and self.height and not touch.is_mouse_scrolling:
            self._wave_origin = ((touch.x - self.x) / self.width, (touch.y - self.y) / self.height)
        return super().on_touch_down(touch)

    def _track_pointer(self, _widget, parent):
        if platform != "win":
            return
        global _pointer_bound
        if parent is None:
            _hoverable.discard(self)
            self._hovered = False
            return
        if not _pointer_bound:
            from kivy.core.window import Window
            Window.bind(mouse_pos=_pointer_move)
            _pointer_bound = True
        _hoverable.add(self)

    def _paint_feedback(self, *_):
        self._press_scale.x = self._press_scale.y = self.scale_feedback
        self._press_ink.a = self.glow_feedback
        reach = self.wave_feedback
        self._wave_ink.a = self.glow_feedback * .65 if reach < 1 else 0
        if self._wave_ink.a:
            x, y = self._wave_origin
            left, right = .5 - x / reach, .5 + (1 - x) / reach
            bottom, top = .5 - y / reach, .5 + (1 - y) / reach
            self._press_wave.tex_coords = (left, bottom, right, bottom, right, top, left, top)

    @staticmethod
    def _touch_feedback(*_):
        if _effects_level != "off":
            try:
                _android_haptic()()
            except ImportError:
                pass

    def _press_effect(self, *_):
        down = self.state == "down"
        target = .972 if down else 1
        glow = .22 if down else .09 if self._hovered else 0
        Animation.cancel_all(self, "scale_feedback", "glow_feedback", "wave_feedback")
        if _effects_level == "off":
            self.scale_feedback = 1
            self.glow_feedback = 0
            self.wave_feedback = 1
            return
        duration = .12 if down else .18
        Animation(scale_feedback=target if _effects_level == "full" else 1,
                  glow_feedback=glow, d=duration, t="out_quad").start(self)
        if _effects_level == "full":
            if down:
                self.wave_feedback = .24
            Animation(wave_feedback=.82 if down else 1, d=.19, t="out_quad").start(self)
        else:
            self.wave_feedback = 1


class GlassTextButton(PressFeedback, Button):
    """Text action for dialogs, settings and segmented controls."""

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", UI_FONT)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_disabled_normal", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        super().__init__(**kwargs)


@lru_cache(maxsize=4)
def _artwork_fade(rgb):
    """Build a reusable edge gradient so the illustration blends into its surface."""
    side = 64
    pixels = bytearray()

    def fade(distance, length):
        value = min(1, distance / length)
        return value * value * (3 - 2 * value)

    for row in range(side):
        y = row / (side - 1)
        vertical = fade(y, .24) * fade(1 - y, .18)
        for column in range(side):
            x = column / (side - 1)
            horizontal = fade(x, .13) * fade(1 - x, .13)
            pixels.extend((*rgb, round(255 * (1 - horizontal * vertical))))
    return _rgba_texture(side, side, pixels)


@lru_cache(maxsize=1)
def _emblem_texture(path):
    """Blend the supplied opaque PNG into the app without baking in a background color."""
    from PIL import Image

    with Image.open(path) as source:
        image = source.convert("RGBA").transpose(getattr(Image, "Transpose", Image).FLIP_TOP_BOTTOM)
    width, height = image.size
    data = bytearray(image.tobytes())
    left, top, right, bottom = EMBLEM_CROP if image.size == (268, 212) else (0, 0, width, height)
    for row in range(height):
        y = height - row - 1
        for col in range(width):
            edge = max(0, min(1, (col - left) / 22, (right - col) / 20,
                              (y - top) / 9, (bottom - y) / 19))
            base = (row * width + col) * 4
            strength = max(.04, min(1, (max(data[base:base + 3]) - 35) / 76))
            data[base + 3] = round(255 * strength * edge * edge * (3 - 2 * edge))
    return _rgba_texture(width, height, data)


class GlassArtwork(Widget):
    """Draw the reference's glass emblem without drawing the surrounding UI."""

    def __init__(self, path, background=None, muted=False, zoom=1, **kwargs):
        super().__init__(**kwargs)
        image_path = Path(path)
        emblem = image_path.name == "aish-premium-symbol.png"
        cutout = image_path.with_name("aish-emblem-cutout.png")
        if emblem and cutout.is_file():
            self.texture = _cutout_texture(cutout)
        else:
            self.texture = _emblem_texture(image_path) if emblem else CoreImage(str(image_path)).texture
        backdrop = PALETTE["bg_top"] if background is None else background
        rgb = tuple(round(channel * 255) for channel in backdrop[:3])
        self._fade = None if emblem else _artwork_fade(rgb)
        self._tick = None
        self._phase = 0.0
        self._alpha = .9 if muted else 1
        self._zoom = zoom
        self._breath = 1
        self._art_size, self._art_coords = self._crop(image_path.name, muted)
        with self.canvas:
            self.ink = Color(1, 1, 1, self._alpha)
            self.picture = Rectangle(texture=self.texture, tex_coords=self._art_coords)
            Color(1, 1, 1, 1)
            self.edge = Rectangle(texture=self._fade) if self._fade is not None else None
        self.bind(pos=self.layout_art, size=self.layout_art, parent=self._parent_changed)
        self.layout_art()

    def _crop(self, name, muted):
        width, height = self.texture.size
        if name == "aish-premium-symbol.png" and (width, height) == (268, 212):
            left, top, right, bottom = EMBLEM_CROP
        elif name == "aish-glass-reference.png" and (width, height) == (898, 607):
            # The asset contains only the artwork region of the approved mockup.
            left, top, right, bottom = (96, 11, 842, 607) if muted else (0, 0, 898, 607)
        elif name == "aish-welcome-art.png" and (width, height) == (1536, 1024):
            left, top, right, bottom = 4, 182, 508, 542
        else:
            left, top, right, bottom = 0, 0, width, height

        u0, v0, u1, _, _, v1, *_ = self.texture.tex_coords
        u_left = u0 + (u1 - u0) * left / width
        u_right = u0 + (u1 - u0) * right / width
        v_bottom = v1 + (v0 - v1) * bottom / height
        v_top = v1 + (v0 - v1) * top / height
        coords = (u_left, v_bottom, u_right, v_bottom, u_right, v_top, u_left, v_top)
        return (right - left, bottom - top), coords

    def layout_art(self, *_):
        source_width, source_height = self._art_size
        scale = min(self.width / source_width, self.height / source_height * self._zoom) * self._breath
        width, height = source_width * scale, source_height * scale
        pos = (self.x + (self.width - width) / 2, self.y + (self.height - height) / 2)
        self.picture.pos, self.picture.size = pos, (width, height)
        if self.edge is not None:
            self.edge.pos, self.edge.size = self.picture.pos, self.picture.size

    def _parent_changed(self, _widget, parent):
        if parent is None:
            self.set_motion(False)

    def set_motion(self, enabled):
        if enabled and self._tick is None:
            self._tick = Clock.schedule_interval(self._pulse, 1 / 24)
        elif not enabled and self._tick is not None:
            self._tick.cancel()
            self._tick = None
            self.ink.a = self._alpha
            self._breath = 1
            self.layout_art()

    def _pulse(self, dt):
        self._phase = (self._phase + dt * .85) % (2 * pi)
        self.ink.a = self._alpha * (.981 + .019 * cos(self._phase))
        if _effects_level == "full":
            self._breath = .994 + .006 * cos(self._phase)
            self.layout_art()


@lru_cache(maxsize=1)
def _cutout_texture(path):
    return CoreImage(str(path), mipmap=True).texture


class ComposerInput(TextInput):
    """Desktop Enter submits. Shift+Enter and mobile IMEs can insert new lines."""
    def __init__(self, on_send, **kwargs):
        super().__init__(multiline=True, write_tab=False, **kwargs)
        self.submit = on_send

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if platform != "android" and keycode[1] in ("enter", "numpadenter") and not modifiers:
            self.submit()
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)


class Glyph(Widget):
    def __init__(self, name, ink, icon_size=22, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.ink = ink
        self.icon_size = dp(icon_size)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        size = min(self.width, self.height, self.icon_size)
        if size <= 0:
            return
        unit = size / 24
        left = self.x + (self.width - size) / 2
        bottom = self.y + (self.height - size) / 2
        stroke = min(dp(1.02), max(dp(.75), unit * .89))

        def x(value):
            return left + value * unit

        def y(value):
            return bottom + value * unit

        def path(*points):
            vertices = [value for px, py in points for value in (x(px), y(py))]
            Line(points=vertices, width=stroke, joint="round", cap="round")

        def curve(start, *segments):
            points = [start]
            for first, second, end in segments:
                origin = points[-1]
                for step in range(1, 13):
                    t = step / 12
                    u = 1 - t
                    points.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d
                                        for a, b, c, d in zip(origin, first, second, end)))
            path(*points)

        def rect(px, py, width, height, radius=2):
            Line(rounded_rectangle=(x(px), y(py), width * unit, height * unit, radius * unit),
                 width=stroke)

        def circle(px, py, radius, filled=False):
            if filled:
                Ellipse(pos=(x(px - radius), y(py - radius)), size=(radius * 2 * unit,) * 2)
            else:
                Line(circle=(x(px), y(py), radius * unit), width=stroke)

        name = self.name
        with self.canvas:
            Color(*self.ink)
            if name in ("brand", "asterisk"):
                for axis in range(3):
                    angle = axis * pi / 3 + pi / 6
                    dx, dy = cos(angle) * 9.7, sin(angle) * 9.7
                    path((12 - dx, 12 - dy), (12 + dx, 12 + dy))
            elif name == "menu":
                for level in (6, 12, 18):
                    path((3, level), (21, level))
            elif name == "home":
                path((2.4, 11.3), (12, 20.7), (21.6, 11.3))
                path((5.3, 13.7), (5.3, 3.5), (9.7, 3.5), (9.7, 9.6),
                     (14.3, 9.6), (14.3, 3.5), (18.7, 3.5), (18.7, 13.7))
            elif name == "home_active":
                Triangle(points=(x(1.5), y(11), x(12), y(21.5), x(22.5), y(11)))
                Rectangle(pos=(x(5), y(9)), size=(14 * unit, 2.5 * unit))
                for px in (5, 14):
                    Rectangle(pos=(x(px), y(3)), size=(5 * unit, 6 * unit))
            elif name == "profile":
                circle(12, 16, 4)
                path((4, 3), (4, 6), (7, 9), (17, 9), (20, 6), (20, 3), (4, 3))
            elif name == "dot":
                circle(12, 12, 5, filled=True)
            elif name == "camera":
                curve((5, 17), ((2, 17), (2, 15.6), (2, 14)), ((2, 10), (2, 8), (2, 6.5)),
                      ((2, 4.6), (3, 3.6), (4.8, 3.6)), ((8, 3.6), (16, 3.6), (19.2, 3.6)),
                      ((21, 3.6), (22, 4.6), (22, 6.5)), ((22, 9.5), (22, 11), (22, 14)),
                      ((22, 16), (21, 17), (19.2, 17)))
                path((5, 17), (7.8, 17), (9.8, 20.1), (14.4, 20.1), (16.4, 17), (19.2, 17))
                circle(12, 10.4, 4.0)
                circle(18.7, 14.3, .55, True)
            elif name == "trash":
                path((3, 18), (21, 18))
                path((9, 18), (9, 21), (15, 21), (15, 18))
                path((6, 16), (7, 3), (17, 3), (18, 16))
                path((10, 14), (10, 7))
                path((14, 14), (14, 7))
            elif name == "volume":
                for bar, length in enumerate((5, 12, 18, 10, 5)):
                    path((4 + bar * 4, 12 - length / 2), (4 + bar * 4, 12 + length / 2))
            elif name == "share":
                path((6, 12), (17, 18))
                path((6, 12), (17, 6))
                circle(5, 12, 2.6)
                circle(19, 19, 2.6)
                circle(19, 5, 2.6)
            elif name == "paperclip":
                path((8, 13), (14, 19), (17, 20), (20, 18), (20, 15), (9, 4),
                     (6, 3), (3, 5), (3, 8), (14, 19))
                path((8, 13), (6, 9), (7, 7), (9, 7), (16, 14))
            elif name in ("chat", "message"):
                curve((5.2, 8.0), ((2.8, 8.5), (2.6, 10), (2.6, 12.5)),
                      ((2.6, 17.6), (3.1, 20.1), (6.5, 20.1)),
                      ((9.3, 20.3), (14.7, 20.3), (17.5, 20.1)),
                      ((21, 20.1), (21.4, 17.8), (21.4, 13.2)),
                      ((21.4, 9.7), (20.4, 7.3), (17, 7.3)))
                path((17, 7.3), (10, 7.3), (5.2, 3.8), (5.2, 8))
                for px in (7.3, 12, 16.7):
                    circle(px, 13.7, .82, True)
            elif name == "chat_active":
                RoundedRectangle(pos=(x(2), y(6)), size=(20 * unit, 15 * unit), radius=[4 * unit])
                Triangle(points=(x(6), y(7), x(11), y(7), x(6), y(2)))
                Color(*PALETTE["accent_text"])
                for px in (7, 12, 17):
                    circle(px, 13.5, 1.1, True)
            elif name in ("history", "layers"):
                path((3, 15), (12, 20), (21, 15), (12, 10), (3, 15))
                path((3, 11), (12, 6), (21, 11))
                path((3, 7), (12, 2), (21, 7))
            elif name == "studio":
                path((12, 22), (14.8, 14.8), (22, 12), (14.8, 9.2), (12, 2),
                     (9.2, 9.2), (2, 12), (9.2, 14.8), (12, 22))
            elif name in ("tools", "grid"):
                for px, py in ((3, 3), (14, 3), (3, 14), (14, 14)):
                    rect(px, py, 7, 7, 1.5)
            elif name == "more":
                for px in (5, 12, 19):
                    circle(px, 12, 1.35, True)
            elif name == "more_vertical":
                for py in (5, 12, 19):
                    circle(12, py, 1.6, True)
            elif name == "back":
                path((20, 12), (4, 12), (10, 18))
                path((4, 12), (10, 6))
            elif name == "chevron":
                path((9, 18), (15, 12), (9, 6))
            elif name == "down":
                path((6, 15), (12, 9), (18, 15))
            elif name == "download":
                path((12, 21), (12, 8), (7, 13))
                path((12, 8), (17, 13))
                path((6, 4), (18, 4))
            elif name == "expand":
                for px, py, dx, dy in ((3, 3, 1, 1), (21, 3, -1, 1),
                                      (3, 21, 1, -1), (21, 21, -1, -1)):
                    path((px + 5 * dx, py), (px, py), (px, py + 5 * dy))
            elif name == "plus":
                path((5, 12), (19, 12))
                path((12, 5), (12, 19))
            elif name == "close":
                path((6, 6), (18, 18))
                path((18, 6), (6, 18))
            elif name == "image":
                rect(3, 3, 18, 18, 3)
                circle(8.1, 15.8, 1.25)
                path((3.7, 7), (8.7, 11.6), (12.3, 8.5), (16.6, 13.2), (20.4, 9.4))
            elif name == "gear":
                points = []
                for index in range(8):
                    for offset, radius in ((-.43, 8.1), (-.27, 8.1), (-.21, 10), (.21, 10), (.27, 8.1), (.43, 8.1)):
                        angle = (index + offset) * pi / 4
                        points.append((12 + radius * cos(angle), 12 + radius * sin(angle)))
                path(*points, points[0])
                circle(12, 12, 3.5)
            elif name == "send_jade":
                Triangle(points=(x(4), y(5.5), x(19.6), y(12), x(6.3), y(10.3)))
                Triangle(points=(x(4), y(18.5), x(19.6), y(12), x(6.3), y(13.7)))
                path((4.5, 5.6), (19.6, 12), (4.5, 18.4))
            elif name == "send":
                path((3, 13), (21, 21), (15, 3), (11, 10), (3, 13))
                path((11, 10), (21, 21))
            elif name == "stop":
                RoundedRectangle(pos=(x(6), y(6)), size=(12 * unit, 12 * unit), radius=[1.8 * unit])
            elif name == "pen":
                path((5, 5), (9, 11), (13.2, 15.1))
                path((7, 8), (7, 13), (11, 18), (20, 21), (18, 14), (14, 10), (11, 10), (7, 8))
            elif name == "code":
                path((8, 7), (3, 12), (8, 17))
                path((16, 7), (21, 12), (16, 17))
                path((10, 4), (14, 20))
            elif name in ("plan", "check"):
                if name == "plan":
                    for level in (5, 12, 19):
                        path((3, level), (5, level - 2), (8, level + 2))
                        path((12, level), (21, level))
                else:
                    path((4, 12), (9, 7), (20, 18))
            elif name == "search":
                circle(10, 14, 6)
                path((14.4, 9.4), (20, 4))
            elif name == "copy":
                rect(8.5, 6.8, 12, 13.9, 2.3)
                curve((16.6, 3.6), ((12, 3.6), (8.7, 3.6), (6.2, 3.6)),
                      ((4.7, 3.6), (3.7, 4.7), (3.7, 6.2)),
                      ((3.7, 9.5), (3.7, 12.4), (3.7, 15.9)))
            elif name == "bookmark":
                path((6, 3), (6, 19), (8, 21), (16, 21), (18, 19), (18, 3),
                     (12, 7), (6, 3))
            elif name == "refresh":
                Line(circle=(x(12), y(12), 7.6 * unit, 40, 309), width=stroke, cap="round")
                path((19.5, 20), (19.5, 14.5), (14, 14.5))
            elif name == "folder":
                path((3, 16.1), (3, 19.5), (8.8, 19.5), (11, 16.9), (18, 16.9))
                curve((18, 16.9), ((20.2, 16.9), (21.1, 16.2), (21.1, 14.5)),
                      ((21.1, 12), (21.1, 9.8), (21.1, 7.3)),
                      ((21.1, 5.5), (20.3, 4.8), (18.5, 4.8)),
                      ((14, 4.8), (10, 4.8), (5.6, 4.8)),
                      ((4, 4.8), (3, 5.6), (3, 7.3)),
                      ((3, 10.1), (3, 13.2), (3, 16.1)))
            elif name == "book":
                path((12, 5), (8, 8), (3, 8), (3, 19), (8, 19), (12, 16),
                     (16, 19), (21, 19), (21, 8), (16, 8), (12, 5), (12, 16))
            elif name == "shield":
                path((12, 21), (20, 18), (19, 10), (16, 6), (12, 3), (8, 6),
                     (5, 10), (4, 18), (12, 21))
                path((8.5, 12), (11, 9), (16, 15))
            elif name == "sliders":
                path((3, 17), (8, 17))
                path((12, 17), (21, 17))
                circle(10, 17, 2)
                path((3, 7), (13, 7))
                path((17, 7), (21, 7))
                circle(15, 7, 2)
            elif name == "clock":
                circle(12, 12, 9)
                path((12, 18), (12, 12), (16, 10))
            elif name == "table":
                rect(3, 4, 18, 16, 2)
                path((3, 15), (21, 15))
                path((3, 10), (21, 10))
                path((10, 15), (10, 4))
            elif name == "calc":
                rect(5, 2, 14, 20, 3)
                path((8, 16), (16, 16))
                for px in (9, 15):
                    for py in (6, 11):
                        circle(px, py, 1.05, True)
            elif name == "file":
                path((5, 2), (5, 22), (15, 22), (20, 17), (20, 2), (5, 2))
                path((15, 22), (15, 17), (20, 17))
                for level in (7, 11, 15):
                    path((8, level), (13, level))
            elif name == "lock":
                rect(5, 2, 14, 11, 2)
                path((8, 13), (8, 18), (10, 20), (14, 20), (16, 18), (16, 13))
                circle(12, 8, 1.3)
            elif name == "cloud":
                path((7, 6), (4, 7), (3, 10), (4, 13), (7, 14), (9, 18),
                     (13, 19), (16, 17), (17, 14), (20, 13), (22, 10), (21, 7), (18, 6), (7, 6))
            elif name == "lightning":
                path((14, 22), (4, 10), (11, 10), (10, 2), (20, 14), (13, 14), (14, 22))
            elif name == "brain":
                path((12, 5), (9, 3), (5, 5), (5, 8), (2, 11), (3, 15), (6, 16),
                     (6, 19), (9, 21), (12, 19), (15, 21), (18, 19), (18, 16), (21, 15),
                     (22, 11), (19, 8), (19, 5), (15, 3), (12, 5), (12, 19))
                path((6, 16), (9, 14), (9, 11), (6, 10))
                path((18, 16), (15, 14), (15, 11), (18, 10))
            elif name == "cpu":
                rect(5, 5, 14, 14, 2)
                rect(9, 9, 6, 6, 1)
                for offset in (8, 12, 16):
                    path((offset, 2), (offset, 5))
                    path((offset, 19), (offset, 22))
                    path((2, offset), (5, offset))
                    path((19, offset), (22, offset))
            elif name == "palette":
                path((12, 3), (7, 4), (3, 8), (2, 13), (4, 18), (8, 21), (15, 22),
                     (19, 20), (22, 16), (22, 12), (20, 9), (16, 9), (13, 8), (13, 5), (12, 3))
                for px, py in ((6, 12), (9, 17), (15, 18), (18, 14)):
                    circle(px, py, 1.1, True)
            elif name == "keyboard":
                rect(2, 5, 20, 14, 2)
                for py in (10, 14):
                    for px in (6, 10, 14, 18):
                        circle(px, py, .8, True)
                path((9, 8), (15, 8))
            elif name == "bell":
                curve((3.5, 6), ((5.4, 8.3), (6.3, 9.8), (6.3, 13.9)),
                      ((6.3, 17.5), (8.5, 20.1), (12, 20.1)),
                      ((15.5, 20.1), (17.7, 17.5), (17.7, 13.9)),
                      ((17.7, 9.8), (18.6, 8.3), (20.5, 6)))
                path((3.5, 6), (20.5, 6))
                curve((9.2, 3.8), ((10, 1.7), (14, 1.7), (14.8, 3.8)))
            elif name == "type":
                path((2, 6), (6, 16), (10, 6))
                path((3.5, 10), (8.5, 10))
                path((11, 6), (16.5, 20), (22, 6))
                path((13, 11), (20, 11))
            elif name == "text":
                path((4, 18), (20, 18))
                path((4, 12), (17, 12))
                path((4, 6), (12, 6))
            elif name == "convert":
                path((4, 16), (20, 16), (16, 20))
                path((20, 8), (4, 8), (8, 4))
            elif name == "mic":
                rect(9, 8.5, 6, 12.9, 3)
                curve((5.7, 12), ((5.7, 7.4), (8, 5.8), (12, 5.8)),
                      ((16, 5.8), (18.3, 7.4), (18.3, 12)))
                path((12, 5.8), (12, 2.5))
                path((9, 2.5), (15, 2.5))


def _bevel_vertices(pos, size, corner, width, outside=False):
    x, y = pos
    w, h = size
    centers = ((w - corner, corner), (w - corner, h - corner),
               (corner, h - corner), (corner, corner))
    vertices = []
    for index, (cx, cy) in enumerate(centers):
        for sample in range(9):
            angle = (index - 1 + sample / 8) * pi / 2
            radii = (corner + width, corner) if outside else (corner, max(0, corner - width))
            for ring, radius in enumerate(radii):
                dx, dy = cx + cos(angle) * radius, cy + sin(angle) * radius
                u, v = (1. - ring, max(0, min(1, dy / h))) if outside else (dx / w, dy / h)
                vertices.extend((x + dx, y + dy, u, v))
    return vertices + vertices[:8]


def panel(widget, color, rim=None, radius=14, inset=0, luminous=False, glass=False, material=None):
    """Attach a rounded surface and return its mutable fill color and outline."""
    canvas = widget.canvas.before
    if isinstance(widget, TextInput):
        # Kivy's TextInput sets its text color in canvas.before. Draw behind that
        # rule so the glass outline cannot tint the search hint or entered text.
        background = Canvas()
        canvas.insert(0, background)
        canvas = background
    with canvas:
        diffusion = None
        if material in ("lit", "shortcut"):
            Color(1, 1, 1, 1)
            diffusion = Mesh(mode="triangle_strip", texture=halo_film(material == "shortcut"),
                             indices=list(range(74)))
        fill = Color(*color)
        body = RoundedRectangle(radius=[dp(radius)])
        glare = None
        aura = []
        bevel = None
        if material:
            Color(1, 1, 1, 1)
            glare = RoundedRectangle(texture=glass_film(material))
            if material == "profile":
                Color(1, 1, 1, .56)
                artwork = RoundedRectangle(texture=liquid_backdrop(True))
                Color(1, 1, 1, 1)
            else:
                artwork = None
            bevel = Mesh(mode="triangle_strip", texture=edge_film(material),
                         indices=list(range(74)))
        elif luminous:
            for width, alpha in ((6, .035), (4, .08), (2, .16)):
                Color(*MINT_LIGHT[:3], alpha)
                aura.append(Line(width=dp(width)))
        if not material and (glass or (color[3] and (rim or color in PALETTE.values()))):
            alpha = .30 if luminous else .13
            Color(*MINT_LIGHT[:3], alpha)
            glare = RoundedRectangle(texture=_glass_reflection())
        outline = Color(*rim) if rim else None
        border = Line(width=dp(.60)) if rim else None

    def place(*_):
        padding = dp(inset)
        pos = (widget.x + padding, widget.y + padding)
        size = (max(0, widget.width - padding * 2), max(0, widget.height - padding * 2))
        corner = min(dp(radius), min(size) / 2)
        body.pos, body.size = pos, size
        body.radius = [corner]
        if glare is not None:
            glare.pos, glare.size, glare.radius = pos, size, [corner]
        if material and artwork is not None:
            artwork.pos, artwork.size, artwork.radius = pos, size, [corner]
        if bevel is not None and min(size) > 0:
            bevel.vertices = _bevel_vertices(pos, size, corner, dp(1.35 if material == "lit" else 1.15))
        if diffusion is not None and min(size) > 0:
            diffusion.vertices = _bevel_vertices(pos, size, corner, dp(12 if material == "lit" else 7), outside=True)
        if border:
            border.rounded_rectangle = (*pos, *size, corner)
        for glow in aura:
            glow.rounded_rectangle = (*pos, *size, corner)

    widget.bind(pos=place, size=place)
    place()
    return fill, outline


def surface(widget, color, rim=None, radius=14, *, material=None):
    return panel(widget, color, rim, radius, material=material)


def hairline(widget, color, top=True, margin=0):
    with widget.canvas.before:
        Color(*color)
        line = Rectangle(size=(0, dp(1)))

    def place(*_):
        line.pos = (widget.x + dp(margin), widget.y + widget.height - dp(1) if top else widget.y)
        line.size = (max(0, widget.width - dp(margin * 2)), dp(1))

    widget.bind(pos=place, size=place)
    place()


class IconAction(PressFeedback, ButtonBehavior, BoxLayout):
    """Icon or icon-and-text action with a stable touch target."""
    text = StringProperty("")

    def __init__(self, text, icon, callback, tint, *, variant="quiet", button_width=44,
                 button_height=44, icon_size=21, icon_last=False, radius=None, material=None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("spacing", dp(4))
        kwargs.setdefault("width", dp(button_width))
        kwargs.setdefault("height", dp(button_height))
        super().__init__(**kwargs)
        self.text = text
        self.callback = callback
        self.tint = tint
        self.variant = variant
        self.glyph = Glyph(icon, tint("text"), icon_size)
        self.caption = Label(text=text, font_name=UI_FONT, font_size=sp(12.5), bold=True,
                             halign="center", valign="middle", shorten=True)
        self.caption.bind(size=self.caption.setter("text_size"))
        if text:
            self.glyph.size_hint_x = None
            self.glyph.width = dp(icon_size + 3)
            self.padding = (dp(10), 0, dp(8), 0)
            children = (self.caption, self.glyph) if icon_last else (self.glyph, self.caption)
            for child in children:
                self.add_widget(child)
        else:
            self.add_widget(self.glyph)
        if radius is None:
            radius = 24 if variant == "pill" else 12
        self._fill, self._rim = panel(self, (0, 0, 0, 0), (0, 0, 0, 0), radius,
                                      glass=variant in ("solid", "outline", "pill"), material=material)
        self.bind(state=self._style, disabled=self._style, text=self._update_caption)
        self._style()

    def _update_caption(self, _button, value):
        self.caption.text = value

    def on_touch_down(self, touch):
        # Hidden composer actions overlap the compact input field.
        if self.opacity == 0:
            return False
        return super().on_touch_down(touch)

    def _style(self, *_):
        tint = self.tint
        clear = (0, 0, 0, 0)
        bg, border, ink = {
            "quiet": (clear, clear, tint("text_dim")),
            "outline": (tint("panel"), tint("panel3"), tint("text")),
            "pill": (tint("chip"), tint("panel3"), tint("chip_text")),
            "solid": (tint("accent"), tint("accent"), tint("accent_text")),
            "danger": (tint("danger_bg"), tint("danger"), tint("danger")),
        }[self.variant]
        if self.disabled:
            bg, ink = tint("accent_soft"), tint("text_faint")
        elif self.state == "down":
            bg = tint("panel3") if bg == clear else (*[channel * .84 for channel in bg[:3]], bg[3])
        self._fill.rgba, self._rim.rgba = bg, border
        self.caption.color = self.glyph.ink = ink
        self.glyph.draw()

    def on_release(self):
        if self.callback is not None:
            self.callback()


class CardButton(PressFeedback, ButtonBehavior, BoxLayout):
    def __init__(self, callback, color, border, radius=17, luminous=False, material=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self._base = color
        self._fill, _ = panel(self, color, border, radius, luminous=luminous, material=material)
        self.bind(state=self._style)

    def _style(self, *_):
        factor = .86 if self.state == "down" else 1
        self._fill.rgba = (*(channel * factor for channel in self._base[:3]), self._base[3])

    def on_release(self):
        if self.callback is not None:
            self.callback()


class NavButton(PressFeedback, ButtonBehavior, BoxLayout):
    selected_opacity = NumericProperty(0)

    def __init__(self, title, icon, action, tint, *, glass=False, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(4), 0, dp(9)), **kwargs)
        self.tint = tint
        self.action = action
        self.active = False
        self.icon = icon
        self.glass = glass
        self.glyph = Glyph(icon, tint("text_dim"), icon_size=24 if glass else 22, size_hint_y=.60)
        self.caption = Label(text=title, font_name=UI_FONT, font_size=sp(10.5),
                             size_hint_y=.40, color=tint("text_dim"))
        self.add_widget(self.glyph)
        self.add_widget(self.caption)
        with self.canvas.before:
            self.selected_fill = Color(*tint("accent_soft")[:3], 0)
            self.selected_shape = RoundedRectangle(radius=[dp(15)])
            self.selected_light = Color(*(1, 1, 1) if glass else tint("accent")[:3], 0)
            self.selected_reflection = RoundedRectangle(texture=glass_film("nav-selected") if glass else _glass_reflection(),
                                                        radius=[dp(15)])
        self.bind(pos=self.place, size=self.place, state=self._style,
                  selected_opacity=self._paint_selection)
        self.place()

    def place(self, *_):
        width = min(dp(70), self.width - dp(2) if self.glass else self.width)
        position = (self.center_x - width / 2, self.y + (dp(4) if self.glass else 0))
        size = (width, max(0, self.height - (dp(3) if self.glass else 0)))
        self.selected_shape.pos = self.selected_reflection.pos = position
        self.selected_shape.size = self.selected_reflection.size = size

    def _style(self, *_):
        ink = self.tint("accent") if self.active or self.state == "down" else self.tint("text_dim")
        self.caption.color = self.glyph.ink = ink
        self.caption.bold = self.active
        self.glyph.name = self.icon + "_active" if self.active and self.icon in ("home", "chat") else self.icon
        self.glyph.draw()

    def _paint_selection(self, *_):
        self.selected_fill.a = self.selected_opacity
        self.selected_light.a = self.selected_opacity * 1.42 if self.glass else self.selected_opacity * .25

    def set_active(self, active):
        if self.active == active:
            return
        self.active = active
        alpha = .6 if active else 0
        Animation.cancel_all(self, "selected_opacity")
        if _effects_level == "off":
            self.selected_opacity = alpha
        else:
            Animation(selected_opacity=alpha, d=.18, t="out_quad").start(self)
        self._style()

    def on_release(self):
        self.action()


class ProgressDial(Widget):
    def __init__(self, tint, **kwargs):
        super().__init__(**kwargs)
        self.fraction = 1.0
        self.tint = tint
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.before.clear()
        radius = max(dp(8), min(self.size) / 2 - dp(14))
        center = (self.x + self.width / 2, self.y + self.height / 2)
        with self.canvas.before:
            Color(*self.tint("ring_bg"))
            Line(circle=(*center, radius), width=dp(4.5))
            fraction = min(1, max(0, self.fraction))
            if fraction:
                Color(*self.tint("accent"))
                Line(circle=(*center, radius, 0, 360 * fraction), width=dp(4.5), cap="round")
