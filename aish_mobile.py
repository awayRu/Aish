"""Shared native layout primitives for Aish's mobile screens."""
from math import cos, pi, sin

from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

PALETTE = {
    "bg_top": (6/255, 26/255, 29/255, 1), "bg_bot": (6/255, 26/255, 29/255, 1),
    "panel": (0.049, 0.123, 0.138, 1), "panel2": (0.072, 0.169, 0.188, 1),
    "panel3": (0.089, 0.203, 0.225, 1), "bubble_me": (0.57, 0.95, 0.82, 1),
    "bubble_ai": (0.082, 0.189, 0.199, 1), "text": (0.95, 0.98, 0.97, 1),
    "text_dim": (0.72, 0.82, 0.80, 1), "text_faint": (0.61, 0.73, 0.70, 1),
    "accent": (0.57, 0.95, 0.81, 1), "accent_soft": (0.11, 0.24, 0.25, 1),
    "accent_text": (0.031, 0.115, 0.111, 1), "chip": (0.085, 0.192, 0.205, 1),
    "chip_text": (0.87, 0.96, 0.92, 1), "avatar_ai": (0.16, 0.41, 0.37, 1),
    "avatar_me": (0.14, 0.35, 0.33, 1), "ring_bg": (0.12, 0.29, 0.29, 1),
}


class Glyph(Widget):
    def __init__(self, name, ink, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.ink = ink
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        x, y = self.center
        r = min(self.width, self.height) * .33

        def path(points):
            scaled = [coordinate for px, py in points for coordinate in (x + px*r, y + py*r)]
            Line(points=scaled, width=dp(1.45), joint="round", cap="round")

        with self.canvas:
            Color(*self.ink)
            if self.name == "brand":
                for i in range(3):
                    angle = i*pi/3
                    dx, dy = cos(angle)*r, sin(angle)*r
                    Line(points=[x-dx, y-dy, x+dx, y+dy], width=dp(2.8), cap="round")
            elif self.name in ("chat", "history"):
                if self.name == "history":
                    Line(rounded_rectangle=(x-r*.65, y-r*.46, 1.67*r, 1.38*r, dp(4)), width=dp(1.3))
                path([(-1, .48), (-.8, .72), (.67, .72), (.84, .49), (.84, -.42),
                      (.66, -.61), (-.23, -.61), (-.81, -.96), (-.77, -.61),
                      (-1, -.42), (-1, .48)])
            elif self.name == "studio":
                path([(0, 1), (.29, .27), (1, 0), (.29, -.27), (0, -1), (-.29, -.27),
                      (-1, 0), (-.29, .27), (0, 1)])
            elif self.name == "tools":
                path([(-.94, -.85), (.11, .18), (.14, .57), (.41, .88), (.92, .94),
                      (.52, .56), (.56, .39), (.94, .45), (.73, .04), (.29, -.02),
                      (-.64, -.98), (-.94, -.85)])
            elif self.name == "more":
                for off in (-.66, 0, .66):
                    Ellipse(pos=(x + off*r - dp(1.8), y - dp(1.8)), size=(dp(3.6), dp(3.6)))
            elif self.name == "back":
                path([(.77, 0), (-.8, 0), (-.13, .61), (-.8, 0), (-.13, -.61)])


class NavButton(ButtonBehavior, BoxLayout):
    def __init__(self, title, icon, action, tint, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(4)), **kwargs)
        self.tint = tint
        self.action = action
        self.glyph = Glyph(icon, tint("text"), size_hint_y=.57)
        self.caption = Label(text=title, font_size=sp(9.5), size_hint_y=.43)
        self.add_widget(self.glyph)
        self.add_widget(self.caption)
        with self.canvas.before:
            self.fill = Color(0, 0, 0, 0)
            self.surface = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self.place, size=self.place)
        self.set_active(False)

    def place(self, *_):
        self.surface.pos = (self.x + dp(2), self.y)
        self.surface.size = (max(0, self.width - dp(4)), self.height)

    def set_active(self, active):
        ink = self.tint("accent_text") if active else self.tint("text")
        self.fill.rgba = self.tint("accent") if active else (0, 0, 0, 0)
        self.caption.color = ink
        self.caption.bold = active
        self.glyph.ink = ink
        self.glyph.draw()

    def on_release(self):
        self.action()


class GlassArtwork(Widget):
    """Display only the hero artwork from the approved mobile reference."""
    _texture = None

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1, 1, 1, 1)
            self.picture = Rectangle()
        if GlassArtwork._texture is None:
            texture = CoreImage(source).texture
            # Coordinates are defined on the full 1536×1024 approval reference.
            GlassArtwork._texture = texture.get_region(4, 482, 504, 360)
        self.picture.texture = GlassArtwork._texture
        self.bind(pos=self.place, size=self.place)
        self.place()

    def place(self, *_):
        width = min(self.width, self.height * 504 / 360)
        height = width * 360 / 504
        self.picture.pos = (self.x + (self.width - width)/2, self.y + (self.height - height)/2)
        self.picture.size = (width, height)


def surface(widget, color, rim=None, radius=14):
    """Add a flat rounded background that follows a widget's geometry."""
    with widget.canvas.before:
        Color(*color)
        body = RoundedRectangle(radius=[dp(radius)])
        if rim:
            Color(*rim)
            border = Line(width=dp(.8))

    def place(*_):
        body.pos, body.size = widget.pos, widget.size
        if rim:
            border.rounded_rectangle = (*widget.pos, *widget.size, dp(radius))

    widget.bind(pos=place, size=place)
    place()
    return body


class ProgressDial(Widget):
    def __init__(self, tint, **kwargs):
        super().__init__(**kwargs)
        self.fraction = 1
        self.tint = tint
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.before.clear()
        radius = max(dp(8), min(self.size)/2 - dp(14))
        center = (self.x + self.width/2, self.y + self.height/2)
        with self.canvas.before:
            Color(*self.tint("ring_bg"))
            Line(circle=(*center, radius), width=dp(4.5))
            if self.fraction > 0:
                Color(*self.tint("accent"))
                Line(circle=(*center, radius, 0, 360*self.fraction), width=dp(4.5), cap="round")
