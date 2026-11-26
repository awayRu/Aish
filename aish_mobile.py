"""Native controls and artwork rendering for the Aish interface."""
from functools import lru_cache
from math import cos, exp, pi, sin
from pathlib import Path
from weakref import WeakSet

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle, Scale
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex, platform


ASSETS = Path(__file__).resolve().parent / "assets"
WORDMARK = "Aish"
UI_FONT = "Roboto"
if (ASSETS / "Inter-Regular.ttf").is_file() and (ASSETS / "Inter-Bold.ttf").is_file():
    UI_FONT = "AishInter"
    LabelBase.register(UI_FONT, fn_regular=str(ASSETS / "Inter-Regular.ttf"),
                       fn_bold=str(ASSETS / "Inter-Bold.ttf"))

PALETTE = {key: tuple(get_color_from_hex(value)) for key, value in {
    "bg_top": "#071816", "bg_bot": "#041210",
    "panel": "#0a1c1a", "panel2": "#102725", "panel3": "#243f39",
    "text": "#f8f8f8", "text_dim": "#c3ccca", "text_faint": "#9eaeaa",
    "accent": "#63c69e", "accent_text": "#06251b", "accent_soft": "#133c31",
    "bubble_me": "#164837", "bubble_ai": "#0e201e", "bubble_text": "#f8f8f8",
    "chip": "#0e2420", "chip_text": "#c4e8dc", "avatar_me": "#215742", "avatar_ai": "#0e392c",
    "ring_bg": "#315a4c", "danger": "#ff9c9e", "danger_bg": "#392227",
    "success": "#9ceecf", "success_bg": "#1a4238", "star": "#ffd080", "star_bg": "#342b1c",
    "online": "#9ceecf", "shadow": "#0000004d",
}.items()}
MINT_LIGHT = tuple(get_color_from_hex("#a7f2d8"))


def _rgba_texture(width, height, pixels):
    texture = Texture.create(size=(width, height), colorfmt="rgba")
    texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
    return texture


@lru_cache(maxsize=1)
def jade_waves():
    """Two soft refracted ribbons with transparent edges for the jade screens."""
    width, height = 320, 150
    pixels = bytearray()
    for row in range(height):
        y = row / (height - 1)
        for column in range(width):
            x = column / (width - 1)
            ridge = .38 + .14 * sin(x * 7.8 - .45) + x * .31
            distance = y - ridge
            rim = exp(-((distance - .009) / .016) ** 2)
            halo = exp(-((distance + .035) / .091) ** 2)
            broad = exp(-((distance + .105) / .16) ** 2)
            reflection = exp(-((distance + .23 + .06 * sin(x * 11)) / .042) ** 2)
            focus = .32 + .68 * (.5 + .5 * sin(x * 10.5 + .7))
            edge = min(1, y * 8, (1 - y) * 8)
            alpha = (.30 * rim + .44 * halo + .18 * broad + .08 * reflection) * focus * edge
            pixels.extend((round(32 + 116 * rim), round(130 + 103 * rim),
                           round(100 + 110 * rim), round(min(1, alpha) * 255)))
    return _rgba_texture(width, height, pixels)


@lru_cache(maxsize=1)
def _glass_reflection():
    pixels = bytearray()
    for row in range(32):
        y = row / 31
        for column in range(32):
            x = column / 31
            light = .63 * exp(-((1 - y) / .16) ** 2) * (.45 + .55 * (1 - x))
            light += .49 * exp(-(y / .12) ** 2) * x
            pixels.extend((216, 255, 239, round(light * 255)))
    return _rgba_texture(32, 32, pixels)


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hovered = False
        with self.canvas.before:
            PushMatrix()
            self._press_scale = Scale(1, 1, 1, origin=self.center)
        with self.canvas.after:
            self._press_ink = Color(*MINT_LIGHT[:3], 0)
            self._press_reflection = RoundedRectangle(texture=_glass_reflection(), radius=[dp(12)])
            PopMatrix()
        self.bind(pos=self._place_feedback, size=self._place_feedback, state=self._press_effect,
                  parent=self._track_pointer, scale_feedback=self._paint_feedback,
                  glow_feedback=self._paint_feedback)
        if platform == "android":
            self.bind(on_press=self._touch_feedback)
        self._place_feedback()

    def _place_feedback(self, *_):
        self._press_scale.origin = self.center
        self._press_reflection.pos = self.pos
        self._press_reflection.size = self.size

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
        Animation.cancel_all(self, "scale_feedback", "glow_feedback")
        if _effects_level == "off":
            self.scale_feedback = 1
            self.glow_feedback = 0
            return
        duration = .12 if down else .18
        Animation(scale_feedback=target if _effects_level == "full" else 1,
                  glow_feedback=glow, d=duration, t="out_quad").start(self)


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
    for row in range(height):
        y = row / (height - 1)
        for col in range(width):
            x = col / (width - 1)
            edge = min(1, x / .18, (1 - x) / .18, y / .22, (1 - y) / .16)
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
        if name == "aish-glass-reference.png" and (width, height) == (898, 607):
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
        stroke = min(dp(1.15), max(dp(.82), unit * 1.02))

        def x(value):
            return left + value * unit

        def y(value):
            return bottom + value * unit

        def path(*points):
            vertices = [value for px, py in points for value in (x(px), y(py))]
            Line(points=vertices, width=stroke, joint="round", cap="round")

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
                path((2, 11), (12, 21), (22, 11))
                path((5, 13), (5, 3), (10, 3), (10, 9), (14, 9), (14, 3), (19, 3), (19, 13))
            elif name == "profile":
                circle(12, 16, 4)
                path((4, 3), (4, 6), (7, 9), (17, 9), (20, 6), (20, 3), (4, 3))
            elif name == "dot":
                circle(12, 12, 5, filled=True)
            elif name == "camera":
                path((5, 17), (8, 17), (10, 20), (15, 20), (17, 17), (20, 17),
                     (22, 15), (22, 5), (20, 3), (4, 3), (2, 5), (2, 15), (4, 17), (5, 17))
                circle(12, 10, 4)
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
                path((4, 8), (3, 9), (3, 18), (5, 20), (19, 20), (21, 18), (21, 9),
                     (19, 7), (10, 7), (5, 4), (5, 8), (4, 8))
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
            elif name == "back":
                path((20, 12), (4, 12), (10, 18))
                path((4, 12), (10, 6))
            elif name == "chevron":
                path((9, 18), (15, 12), (9, 6))
            elif name == "down":
                path((6, 15), (12, 9), (18, 15))
            elif name == "plus":
                path((5, 12), (19, 12))
                path((12, 5), (12, 19))
            elif name == "close":
                path((6, 6), (18, 18))
                path((18, 6), (6, 18))
            elif name == "image":
                rect(3, 3, 18, 18, 3)
                circle(9, 16, 1.5)
                path((4, 7), (8, 11), (12, 7), (17, 12), (20, 9))
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
                rect(8, 7, 12, 13, 2)
                path((15, 4), (5, 4), (4, 5), (4, 15))
            elif name == "bookmark":
                path((6, 3), (6, 19), (8, 21), (16, 21), (18, 19), (18, 3),
                     (12, 7), (6, 3))
            elif name == "refresh":
                Line(circle=(x(12), y(12), 7.6 * unit, 40, 309), width=stroke, cap="round")
                path((19.5, 20), (19.5, 14.5), (14, 14.5))
            elif name == "folder":
                path((3, 17), (9, 17), (11, 15), (19, 15), (21, 13), (21, 6),
                     (19, 4), (5, 4), (3, 6), (3, 17))
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
            elif name == "text":
                path((4, 18), (20, 18))
                path((4, 12), (17, 12))
                path((4, 6), (12, 6))
            elif name == "convert":
                path((4, 16), (20, 16), (16, 20))
                path((20, 8), (4, 8), (8, 4))
            elif name == "mic":
                rect(9, 9, 6, 12, 3)
                path((5, 12), (5, 9), (8, 6), (16, 6), (19, 9), (19, 12))
                path((12, 6), (12, 3))


def panel(widget, color, rim=None, radius=14, inset=0, luminous=False):
    """Attach a rounded surface and return its mutable fill color and outline."""
    with widget.canvas.before:
        fill = Color(*color)
        body = RoundedRectangle(radius=[dp(radius)])
        glare = None
        aura = []
        if luminous:
            for width, alpha in ((8, .06), (5, .12), (2, .24)):
                Color(*MINT_LIGHT[:3], alpha)
                aura.append(Line(width=dp(width)))
        if color[3] and (rim or color in PALETTE.values()):
            Color(*MINT_LIGHT[:3], .10 if color[0] < .2 else .19)
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
        if border:
            border.rounded_rectangle = (*pos, *size, corner)
        for glow in aura:
            glow.rounded_rectangle = (*pos, *size, corner)

    widget.bind(pos=place, size=place)
    place()
    return fill, outline


def surface(widget, color, rim=None, radius=14):
    return panel(widget, color, rim, radius)


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
                 button_height=44, icon_size=21, icon_last=False, **kwargs):
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
        self._fill, self._rim = panel(self, (0, 0, 0, 0), (0, 0, 0, 0),
                                      24 if variant == "pill" else 12)
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
    def __init__(self, callback, color, border, radius=17, luminous=False, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self._base = color
        self._fill, _ = panel(self, color, border, radius, luminous=luminous)
        self.bind(state=self._style)

    def _style(self, *_):
        factor = .86 if self.state == "down" else 1
        self._fill.rgba = (*(channel * factor for channel in self._base[:3]), self._base[3])

    def on_release(self):
        if self.callback is not None:
            self.callback()


class NavButton(PressFeedback, ButtonBehavior, BoxLayout):
    def __init__(self, title, icon, action, tint, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(4), 0, dp(9)), **kwargs)
        self.tint = tint
        self.action = action
        self.active = False
        self.glyph = Glyph(icon, tint("text_dim"), icon_size=22, size_hint_y=.60)
        self.caption = Label(text=title, font_name=UI_FONT, font_size=sp(10.5),
                             size_hint_y=.40, color=tint("text_dim"))
        self.add_widget(self.glyph)
        self.add_widget(self.caption)
        with self.canvas.after:
            self.marker = Color(*tint("accent")[:3], 0)
            self.line = RoundedRectangle(size=(dp(18), dp(2)), radius=[dp(1)])
        self.bind(pos=self.place, size=self.place, state=self._style)
        self.place()

    def place(self, *_):
        self.line.pos = (self.x + self.width / 2 - dp(9), self.y + dp(5))

    def _style(self, *_):
        ink = self.tint("accent") if self.active or self.state == "down" else self.tint("text_dim")
        self.marker.a = 1 if self.active else 0
        self.caption.color = self.glyph.ink = ink
        self.caption.bold = self.active
        self.glyph.draw()

    def set_active(self, active):
        self.active = active
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
