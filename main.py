#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Чат — премиум v4."""
import os, sys, json, ssl, socket, threading, uuid, re
import urllib.request
from datetime import datetime as DT
import sqlite3

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.animation import Animation
from kivy.graphics import (Color, Rectangle, RoundedRectangle, Ellipse,
                            Line, Triangle, Mesh)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget

# ═══════════════ ПАЛИТРА ═══════════════
BG_TOP      = (0.039, 0.047, 0.071, 1)
BG_BOT      = (0.071, 0.051, 0.118, 1)
PANEL       = (0.086, 0.094, 0.125, 1)
PANEL2      = (0.129, 0.141, 0.180, 1)
PANEL3      = (0.169, 0.180, 0.224, 1)
BUBBLE_ME_A = (0.267, 0.502, 0.945, 1)
BUBBLE_ME_B = (0.404, 0.357, 0.918, 1)
BUBBLE_AI   = (0.129, 0.141, 0.176, 1)
TXT         = (0.945, 0.953, 0.965, 1)
TXT_DIM     = (0.522, 0.545, 0.596, 1)
TXT_FAINT   = (0.333, 0.353, 0.400, 1)
ACCENT      = (0.404, 0.510, 0.961, 1)
DANGER      = (0.941, 0.361, 0.361, 1)
AVATAR_ME   = (0.541, 0.325, 0.945, 1)
AVATAR_AI   = (0.180, 0.780, 0.600, 1)
ONLINE      = (0.290, 0.878, 0.549, 1)
CHIP_BG     = (0.157, 0.169, 0.208, 1)
CHIP_TEXT   = (0.702, 0.729, 0.784, 1)

# ═══════════════ ПРОВАЙДЕРЫ ═══════════════
PROVIDERS = [
    {"name": "KeylessAI",   "url": "https://keylessai.thryx.workers.dev/v1/chat/completions",
     "model": "auto", "key": None, "stream": True},
    {"name": "Kilo",        "url": "https://api.kilo.ai/api/gateway/chat/completions",
     "model": "kilo-auto/free", "key": None, "stream": True},
    {"name": "LLM7",        "url": "https://api.llm7.io/v1/chat/completions",
     "model": "default", "key": "unused", "stream": False},
    {"name": "Pollinations","url": "https://text.pollinations.ai/openai",
     "model": "openai", "key": None, "stream": False},
]

ROOT = os.path.dirname(os.path.abspath(__file__)) or "."
DB_FILE = os.path.join(ROOT, "chat.db")
EXPORT_DIR = ROOT

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Mobile"

# ═══════════════ ГОЛОС (Android) ═══════════════
_ANDROID = None
try:
    import androidhelper
    _ANDROID = androidhelper.Android()
except Exception:
    try:
        import android
        _ANDROID = android.Android()
    except Exception:
        _ANDROID = None

def voice_input():
    if not _ANDROID: return None
    try:
        r = _ANDROID.recognizeSpeech("ru").result
        if isinstance(r, dict):
            return r.get("result") or r.get("text") or None
        return r or None
    except Exception:
        return None

# ═══════════════ БАЗА ═══════════════
try:
    DB_CONN = sqlite3.connect(DB_FILE, check_same_thread=False)
    DB_CONN.row_factory = sqlite3.Row
    DB_CONN.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY, title TEXT, created TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,
            content TEXT, ts TEXT);
        CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
    """)
    DB_CONN.commit()
except Exception:
    DB_CONN = sqlite3.connect(":memory:")
    DB_CONN.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY, title TEXT, created TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,
            content TEXT, ts TEXT);
        CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
    """)
    DB_CONN.commit()

DB_LOCK = threading.Lock()

def get_session():
    r = DB_CONN.execute("SELECT v FROM meta WHERE k='session_id'").fetchone()
    return r["v"] if r else None

def new_session():
    sid = uuid.uuid4().hex[:12]
    now = str(DT.now())[:19]
    DB_CONN.execute("INSERT INTO sessions VALUES(?,?,?,?)",
                    (sid, "Новый чат", now, now))
    DB_CONN.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('session_id',?)", (sid,))
    DB_CONN.commit()
    return sid

SESSION_ID = get_session() or new_session()

def db_add(role, content):
    global SESSION_ID
    with DB_LOCK:
        DB_CONN.execute("INSERT INTO messages(session_id,role,content,ts) VALUES(?,?,?,?)",
                        (SESSION_ID, role, content[:8000], str(DT.now())[:19]))
        DB_CONN.execute("UPDATE sessions SET updated=? WHERE id=?",
                        (str(DT.now())[:19], SESSION_ID))
        DB_CONN.commit()
        if role == "user":
            r = DB_CONN.execute("SELECT title FROM sessions WHERE id=?",
                                (SESSION_ID,)).fetchone()
            if r and r["title"] == "Новый чат":
                t = content.strip().splitlines()[0][:36]
                if t:
                    DB_CONN.execute("UPDATE sessions SET title=? WHERE id=?",
                                    (t, SESSION_ID))
                    DB_CONN.commit()

def db_messages(limit=500):
    return [dict(r) for r in DB_CONN.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?",
        (SESSION_ID, limit))]

def db_recent(n=14):
    rows = DB_CONN.execute(
        "SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (SESSION_ID, n)).fetchall()
    return list(reversed([dict(r) for r in rows]))

def db_clear():
    DB_CONN.execute("DELETE FROM messages WHERE session_id=?", (SESSION_ID,))
    DB_CONN.commit()

def db_count():
    return DB_CONN.execute(
        "SELECT COUNT(*) c FROM messages WHERE session_id=?",
        (SESSION_ID,)).fetchone()["c"]

# ═══════════════ AI ═══════════════
_last_provider = {"name": "-"}

def try_provider(prov, messages, on_chunk=None, cancel_flag=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream, application/json",
        "User-Agent": UA,
    }
    if prov["key"]:
        headers["Authorization"] = "Bearer " + prov["key"]
    msgs = messages[-10:] if prov["name"] == "Pollinations" else messages
    body = json.dumps({
        "model": prov["model"],
        "messages": msgs,
        "temperature": 0.75,
        "max_tokens": 1500,
        "stream": prov["stream"],
    }).encode("utf-8")
    try:
        req = urllib.request.Request(prov["url"], data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45, context=_CTX) as r:
            if prov["stream"]:
                parts = []
                for line in r:
                    if cancel_flag and cancel_flag[0]:
                        break
                    line = line.decode("utf-8", "ignore").strip()
                    if not line.startswith("data:"): continue
                    payload = line[5:].strip()
                    if payload == "[DONE]": break
                    try: j = json.loads(payload)
                    except Exception: continue
                    try: piece = j["choices"][0]["delta"].get("content", "")
                    except Exception: piece = ""
                    if piece:
                        parts.append(piece)
                        if on_chunk:
                            try: on_chunk(piece)
                            except Exception: pass
                text = "".join(parts).strip()
                if text:
                    _last_provider["name"] = prov["name"]
                    return (text, None)
                return (None, "пусто")
            else:
                raw = r.read().decode("utf-8", "ignore")
                j = json.loads(raw)
                if "choices" in j:
                    _last_provider["name"] = prov["name"]
                    return j["choices"][0]["message"]["content"].strip(), None
                if "content" in j:
                    _last_provider["name"] = prov["name"]
                    return str(j["content"]).strip(), None
                _last_provider["name"] = prov["name"]
                return raw.strip(), None
    except Exception as e:
        return None, str(e)[:60]

def ask_ai(messages, on_chunk=None, cancel_flag=None):
    errs = []
    for prov in PROVIDERS:
        text, err = try_provider(prov, messages, on_chunk=on_chunk,
                                 cancel_flag=cancel_flag)
        if text:
            return text, None
        errs.append(prov["name"] + ":" + str(err))
    return None, " | ".join(errs[-2:])

# ═══════════════════════════════════════════════════════════
#  ИКОНКИ
# ═══════════════════════════════════════════════════════════
class IconBase(ButtonBehavior, Widget):
    def __init__(self, on_press=None, size_px=dp(44),
                 bg_color=PANEL2, circle=True, **kw):
        super().__init__(size_hint=(None, None),
                         width=size_px, height=size_px, **kw)
        self._cb = on_press
        self._bg = bg_color
        self._size_px = size_px
        self._circle = circle
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*self._bg)
            if self._circle:
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[self._size_px / 2])
            else:
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(14)])
            self._draw()
        self.canvas.ask_update()

    def _draw(self):
        pass

    def on_release(self):
        if self._cb:
            self._cb()

class IconPlus(IconBase):
    def _draw(self):
        Color(1, 1, 1, 1)
        cx, cy = self.center
        r = self._size_px * 0.19
        Line(points=[cx - r, cy, cx + r, cy], width=dp(2.4), cap="round")
        Line(points=[cx, cy - r, cx, cy + r], width=dp(2.4), cap="round")

class IconMenu(IconBase):
    def _draw(self):
        Color(1, 1, 1, 1)
        cx, cy = self.center
        d = self._size_px * 0.155
        for dy in (-d, 0, d):
            Ellipse(pos=(cx - dp(2), cy + dy - dp(2)),
                    size=(dp(4), dp(4)))

class IconSend(IconBase):
    """Правильный бумажный самолётик — залитый."""
    def _draw(self):
        Color(1, 1, 1, 1)
        cx, cy = self.center
        s = self._size_px * 0.30
        # 4 точки: top-left, right tip, bottom-left, notch
        p_top = (cx - s * 1.0, cy + s * 0.85)
        p_tip = (cx + s * 1.05, cy)
        p_bot = (cx - s * 1.0, cy - s * 0.85)
        p_notch = (cx - s * 0.30, cy)
        # 2 треугольника = залитая форма
        Triangle(points=[p_top[0], p_top[1],
                         p_tip[0], p_tip[1],
                         p_notch[0], p_notch[1]])
        Triangle(points=[p_top[0], p_top[1],
                         p_notch[0], p_notch[1],
                         p_bot[0], p_bot[1]])
        # Линия складки (для реалистичности)
        Color(0.86, 0.88, 0.94, 0.9)
        Line(points=[p_top[0], p_top[1], p_notch[0], p_notch[1],
                     p_bot[0], p_bot[1]],
             width=dp(0.6))

class IconStop(IconBase):
    """Квадрат — кнопка остановки."""
    def _draw(self):
        Color(1, 1, 1, 1)
        cx, cy = self.center
        s = self._size_px * 0.18
        RoundedRectangle(pos=(cx - s, cy - s), size=(s * 2, s * 2),
                         radius=[dp(4)])

class IconMic(IconBase):
    """Микрофон."""
    def _draw(self):
        Color(1, 1, 1, 1)
        cx, cy = self.center
        s = self._size_px * 0.16
        # Капсула микрофона
        RoundedRectangle(pos=(cx - s * 0.55, cy - s * 0.3),
                         size=(s * 1.1, s * 2.1),
                         radius=[s * 0.55])
        # Дуга-держатель
        Line(circle=(cx, cy - s * 0.2, s * 0.85, 200, 340),
             width=dp(2.2))
        # Ножка
        Line(points=[cx, cy - s * 1.05, cx, cy - s * 1.7],
             width=dp(2.2), cap="round")
        Line(points=[cx - s * 0.7, cy - s * 1.7,
                     cx + s * 0.7, cy - s * 1.7],
             width=dp(2.2), cap="round")

class IconClose(IconBase):
    def _draw(self):
        Color(1, 1, 1, 1)
        cx, cy = self.center
        s = self._size_px * 0.20
        Line(points=[cx - s, cy - s, cx + s, cy + s], width=dp(2.2), cap="round")
        Line(points=[cx - s, cy + s, cx + s, cy - s], width=dp(2.2), cap="round")

# ═══════════════════════════════════════════════════════════
#  АВАТАР
# ═══════════════════════════════════════════════════════════
class Avatar(Widget):
    def __init__(self, letter, color, size_px=dp(36), font_px=None,
                 online=False, **kw):
        super().__init__(size_hint=(None, None),
                         width=size_px, height=size_px, **kw)
        self._letter = letter
        self._color = color
        self._size_px = size_px
        self._font = font_px or sp(12)
        self._online = online
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            # Тень
            Color(0, 0, 0, 0.20)
            Ellipse(pos=(self.x + dp(1.5), self.y - dp(1.5)),
                    size=self.size)
            # Круг
            Color(*self._color)
            Ellipse(pos=self.pos, size=self.size)
            # Буква
            Color(1, 1, 1, 1)
        # Текст как child
        for c in self.children[:]:
            self.remove_widget(c)
        lbl = Label(text=self._letter, color=(1, 1, 1, 1), bold=True,
                    font_size=self._font,
                    size_hint=(None, None), size=self.size,
                    pos=self.pos,
                    halign="center", valign="middle")
        self.add_widget(lbl)
        # Онлайн-точка
        if self._online:
            with self.canvas:
                # Ободок под точку (фон)
                Color(0.039, 0.047, 0.071, 1)
                r = self._size_px * 0.30
                x = self.x + self.width - r - dp(1)
                y = self.y + dp(1)
                Ellipse(pos=(x - dp(2), y - dp(2)),
                        size=(r + dp(4), r + dp(4)))
                # Сама точка
                Color(*ONLINE)
                Ellipse(pos=(x, y), size=(r, r))
        self.canvas.ask_update()

# ═══════════════════════════════════════════════════════════
#  ПУЗЫРЬ СООБЩЕНИЯ
# ═══════════════════════════════════════════════════════════
class MsgBox(BoxLayout):
    def __init__(self, role, text, ts="", on_action=None, **kw):
        super().__init__(orientation="horizontal",
                         size_hint=(1, None),
                         padding=(dp(10), dp(4)),
                         spacing=dp(8), **kw)
        self.role = role
        self._text = text
        self._on_action = on_action
        self.ts = ts or DT.now().strftime("%H:%M")

        is_me = (role == "me")
        bubble_bg = BUBBLE_ME_A if is_me else BUBBLE_AI
        fg = (1, 1, 1, 1) if is_me else TXT

        if is_me:
            self.add_widget(BoxLayout(size_hint_x=0.08))
            self._build_bubble(text, fg, bubble_bg, is_me)
            self.add_widget(Avatar("Я", AVATAR_ME, size_px=dp(36)))
        else:
            self.add_widget(Avatar("AI", AVATAR_AI, size_px=dp(36),
                                   font_px=sp(11), online=True))
            self._build_bubble(text, fg, bubble_bg, is_me)
            self.add_widget(BoxLayout(size_hint_x=0.08))

        self.height = dp(60)

    def _build_bubble(self, text, fg, bg, is_me):
        wrapper = BoxLayout(orientation="vertical",
                            size_hint=(0.82, None),
                            spacing=dp(2))
        wrapper.bind(minimum_height=wrapper.setter("height"))

        self.lbl = Label(
            text=text, markup=False, color=fg,
            size_hint=(1, None),
            halign="left", valign="top",
            padding=(dp(14), dp(10)),
            font_size=sp(15))
        self.lbl.bind(width=lambda *a: setattr(
            self.lbl, "text_size", (a[1] - dp(28), None)))
        self.lbl.bind(texture_size=lambda *a: self._on_text_size(a[1][1]))

        with self.lbl.canvas.before:
            # Тень
            Color(0, 0, 0, 0.22)
            self._shadow = RoundedRectangle(
                pos=(self.lbl.x + dp(1), self.lbl.y - dp(2)),
                size=self.lbl.size,
                radius=[dp(20), dp(20), dp(20), dp(20)])
            # Пузырь
            Color(*bg)
            if is_me:
                # Правый нижний угол — плоский
                self._rect = RoundedRectangle(
                    pos=self.lbl.pos, size=self.lbl.size,
                    radius=[dp(20), dp(20), dp(4), dp(20)])
            else:
                # Левый нижний угол — плоский
                self._rect = RoundedRectangle(
                    pos=self.lbl.pos, size=self.lbl.size,
                    radius=[dp(20), dp(20), dp(20), dp(4)])

        def _sync(*a):
            self._rect.pos = self.lbl.pos
            self._rect.size = self.lbl.size
            self._shadow.pos = (self.lbl.x + dp(1), self.lbl.y - dp(2))
            self._shadow.size = self.lbl.size
        self.lbl.bind(pos=_sync, size=_sync)

        wrapper.add_widget(self.lbl)

        time_lbl = Label(
            text=self.ts, color=TXT_FAINT,
            size_hint=(1, None), height=dp(16),
            font_size=sp(10),
            halign="right" if is_me else "left",
            padding=(dp(8), 0))
        time_lbl.bind(size=lambda *a: setattr(time_lbl, "text_size", a[1]))
        wrapper.add_widget(time_lbl)

        self.lbl.bind(on_touch_down=self._touch)
        self.add_widget(wrapper)

    def _on_text_size(self, h):
        self.lbl.height = h
        self.height = max(h + dp(30), dp(60))

    def _touch(self, lbl, touch):
        if lbl.collide_point(*touch.pos):
            if self._on_action:
                self._on_action(self)
            return True
        return False

    def append(self, piece):
        self._text += piece
        self.lbl.text = self._text
        self.lbl.texture_update()
        self.lbl.height = self.lbl.texture_size[1]
        self.height = max(self.lbl.height + dp(30), dp(60))

    def set_text(self, t):
        self._text = t
        self.lbl.text = t
        self.lbl.texture_update()
        self.lbl.height = self.lbl.texture_size[1]
        self.height = max(self.lbl.height + dp(30), dp(60))

# ═══════════════════════════════════════════════════════════
#  ИНДИКАТОР «ПЕЧАТАЕТ»
# ═══════════════════════════════════════════════════════════
class TypingBubble(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="horizontal",
                         size_hint=(1, None),
                         height=dp(56),
                         padding=(dp(10), dp(4)),
                         spacing=dp(8))
        self.add_widget(Avatar("AI", AVATAR_AI, size_px=dp(36),
                               font_px=sp(11), online=True))

        box = BoxLayout(size_hint=(None, None),
                        width=dp(96), height=dp(42),
                        padding=(dp(14), dp(12)))
        with box.canvas.before:
            Color(0, 0, 0, 0.22)
            self._shadow = RoundedRectangle(
                pos=(box.x + dp(1), box.y - dp(2)),
                size=box.size,
                radius=[dp(20), dp(20), dp(20), dp(4)])
            Color(*BUBBLE_AI)
            self._rect = RoundedRectangle(pos=box.pos, size=box.size,
                                          radius=[dp(20), dp(20), dp(20), dp(4)])
        def _sync(*a):
            self._rect.pos = box.pos
            self._rect.size = box.size
            self._shadow.pos = (box.x + dp(1), box.y - dp(2))
            self._shadow.size = box.size
        box.bind(pos=_sync, size=_sync)

        self.dots = Label(text="●", color=TXT_DIM, font_size=sp(11),
                          halign="center", valign="middle")
        box.add_widget(self.dots)
        self.add_widget(box)
        self.add_widget(BoxLayout(size_hint_x=1))

        self._n = 1
        self._ev = Clock.schedule_interval(self._tick, 0.35)

    def _tick(self, *a):
        self._n = (self._n % 3) + 1
        self.dots.text = "● " * self._n
        self.dots.opacity = 0.4
        Animation(opacity=1, d=0.25).start(self.dots)

    def stop(self):
        try: Clock.unschedule(self._ev)
        except Exception: pass

# ═══════════════════════════════════════════════════════════
#  КНОПКА-ЧИП (быстрая подсказка)
# ═══════════════════════════════════════════════════════════
class Chip(ButtonBehavior, BoxLayout):
    def __init__(self, text, on_press=None, **kw):
        super().__init__(size_hint=(None, None),
                         height=dp(40), **kw)
        self._cb = on_press
        self._text = text
        self._lbl = Label(text=text, color=CHIP_TEXT,
                          font_size=sp(12),
                          halign="center", valign="middle",
                          padding=(dp(16), 0))
        self._lbl.bind(texture_size=lambda *a: self._size(a[1][0]))
        self.add_widget(self._lbl)
        with self.canvas.before:
            Color(*CHIP_BG)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[dp(20)])
        self.bind(pos=lambda *a: setattr(self._rect, "pos", a[1]))
        self.bind(size=lambda *a: setattr(self._rect, "size", a[1]))

    def _size(self, w):
        self.width = w + dp(32)

    def on_release(self):
        if self._cb:
            self._cb(self._text)

# ═══════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ЭКРАН
# ═══════════════════════════════════════════════════════════
class ChatRoot(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.busy = False
        self.sb = None
        self.sbuf = ""
        self.sev = None
        self.cancel_flag = [False]
        self.typing = None

        # Фон-градиент
        with self.canvas.before:
            Color(*BG_TOP)
            self._bg1 = Rectangle(pos=self.pos, size=self.size)
            Color(*BG_BOT)
            self._bg2 = Rectangle(pos=self.pos, size=(self.width, self.height))
        self.bind(pos=self._update_bg, size=self._update_bg)

        # ─── Шапка ───
        head = BoxLayout(size_hint=(1, None), height=dp(64),
                         padding=(dp(12), dp(10)), spacing=dp(8))
        with head.canvas.before:
            Color(*PANEL)
            self._hbg = Rectangle(pos=head.pos, size=head.size)
        head.bind(pos=lambda *a: setattr(self._hbg, "pos", a[1]))
        head.bind(size=lambda *a: setattr(self._hbg, "size", a[1]))

        head.add_widget(IconPlus(on_press=self.new_chat, size_px=dp(44),
                                 bg_color=PANEL2))

        title_box = BoxLayout(orientation="vertical", size_hint=(1, 1),
                              padding=(dp(4), 0))
        self.title = Label(text="AI Чат", color=TXT, bold=True,
                           halign="center", valign="bottom",
                           size_hint=(1, 0.6), font_size=sp(17))
        self.title.bind(size=lambda *a: setattr(self.title, "text_size", a[1]))
        self.sub = Label(text="онлайн", color=ONLINE,
                         halign="center", valign="top",
                         size_hint=(1, 0.4), font_size=sp(10))
        self.sub.bind(size=lambda *a: setattr(self.sub, "text_size", a[1]))
        title_box.add_widget(self.title)
        title_box.add_widget(self.sub)
        head.add_widget(title_box)

        head.add_widget(IconMenu(on_press=self.open_menu, size_px=dp(44),
                                 bg_color=PANEL2))
        self.add_widget(head)

        # ─── Скролл ───
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        self.grid = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=dp(2), padding=(dp(4), dp(12)))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.add_widget(self.scroll)

        # ─── Быстрые подсказки (видны если чат пуст) ───
        self.chips_row = BoxLayout(size_hint=(1, None), height=dp(52),
                                   spacing=dp(8), padding=(dp(12), dp(6)))
        self.chips_row.opacity = 1
        self.add_widget(self.chips_row)
        self._build_chips()

        # ─── Панель ввода ───
        foot = BoxLayout(size_hint=(1, None), height=dp(72),
                         padding=(dp(10), dp(10)), spacing=dp(8))
        with foot.canvas.before:
            Color(*PANEL)
            self._fbg = Rectangle(pos=foot.pos, size=foot.size)
        foot.bind(pos=lambda *a: setattr(self._fbg, "pos", a[1]))
        foot.bind(size=lambda *a: setattr(self._fbg, "size", a[1]))

        # Кнопка голосового ввода (слева)
        if _ANDROID:
            self.mic_btn = IconMic(on_press=self.voice_click,
                                   size_px=dp(46), bg_color=PANEL2)
            foot.add_widget(self.mic_btn)

        # Поле ввода
        input_wrap = BoxLayout(size_hint=(1, 1), padding=(dp(16), dp(10)))
        with input_wrap.canvas.before:
            Color(0, 0, 0, 0.20)
            self._inp_sh = RoundedRectangle(
                pos=(input_wrap.x + dp(1), input_wrap.y - dp(1)),
                size=input_wrap.size, radius=[dp(24)])
            Color(*PANEL2)
            self._inp_rect = RoundedRectangle(
                pos=input_wrap.pos, size=input_wrap.size,
                radius=[dp(24)])
        def _sync_inp(*a):
            self._inp_rect.pos = input_wrap.pos
            self._inp_rect.size = input_wrap.size
            self._inp_sh.pos = (input_wrap.x + dp(1), input_wrap.y - dp(1))
            self._inp_sh.size = input_wrap.size
        input_wrap.bind(pos=_sync_inp, size=_sync_inp)

        self.inp = TextInput(hint_text="Напиши сообщение...",
                             multiline=False,
                             background_normal="", background_active="",
                             background_color=(0, 0, 0, 0),
                             foreground_color=TXT,
                             cursor_color=ACCENT,
                             hint_text_color=TXT_DIM,
                             padding=(dp(6), dp(4)),
                             font_size=sp(15))
        self.inp.bind(on_text_validate=self.send)
        self.inp.bind(text=self._on_input)
        input_wrap.add_widget(self.inp)
        foot.add_widget(input_wrap)

        # Слот для кнопки действия (send / stop)
        self.action_slot = BoxLayout(size_hint=(None, 1), width=dp(52))
        self.send_btn = IconSend(on_press=self.send, size_px=dp(52),
                                 bg_color=ACCENT)
        self.stop_btn = IconStop(on_press=self.stop_generation,
                                 size_px=dp(52), bg_color=DANGER)
        self.action_slot.add_widget(self.send_btn)
        foot.add_widget(self.action_slot)

        self.add_widget(foot)

        Clock.schedule_once(lambda *a: self.load(), 0.2)

    def _build_chips(self):
        self.chips_row.clear_widgets()
        prompts = [
            "Расскажи интересный факт",
            "Помоги с кодом",
            "Что приготовить?",
            "Переведи на английский",
        ]
        for p in prompts:
            self.chips_row.add_widget(Chip(p, on_press=self.use_chip))
        self.chips_row.add_widget(BoxLayout(size_hint_x=1))

    def use_chip(self, text):
        self.inp.text = text
        self.send()

    def _on_input(self, *a):
        # Кнопка clear при вводе
        if self.inp.text.strip():
            self.sub.text = "готов"
            self.sub.color = ACCENT
        else:
            self.sub.text = "онлайн"
            self.sub.color = ONLINE

    def _update_bg(self, *a):
        self._bg1.pos = self.pos
        self._bg1.size = self.size
        self._bg2.pos = self.pos
        self._bg2.size = self.size

    def load(self):
        self.grid.clear_widgets()
        self.sb = None
        msgs = db_messages()
        if not msgs:
            self.add_msg("ai", "Привет! Я твой AI-ассистент.\n"
                               "Спроси что угодно или используй подсказки ниже.")
            self.chips_row.opacity = 1
            self.chips_row.height = dp(52)
        else:
            for m in msgs:
                role = "me" if m["role"] == "user" else "ai"
                ts = ""
                try: ts = m["ts"][11:16]
                except Exception: pass
                self.add_msg(role, m["content"], ts=ts)
            self.chips_row.opacity = 0
            self.chips_row.height = 0

    def add_msg(self, role, text, ts=""):
        b = MsgBox(role, text, ts=ts, on_action=self.msg_menu)
        b.opacity = 0
        self.grid.add_widget(b)
        Animation(opacity=1, d=0.22).start(b)
        Clock.schedule_once(lambda *a: self.scroll_to_bottom(), 0.05)
        return b

    def scroll_to_bottom(self):
        try:
            Animation.cancel_all(self.scroll, "scroll_y")
            Animation(scroll_y=0, d=0.2).start(self.scroll)
        except Exception:
            pass

    def voice_click(self):
        if not _ANDROID:
            return
        self.sub.text = "слушаю..."
        self.sub.color = ACCENT
        def worker():
            txt = voice_input()
            def done(*a):
                self.sub.text = "онлайн"
                self.sub.color = ONLINE
                if txt:
                    self.inp.text = txt
                    self.send()
            Clock.schedule_once(done, 0)
        threading.Thread(target=worker, daemon=True).start()

    def send(self, *a):
        if self.busy: return
        text = self.inp.text.strip()
        if not text: return
        self.inp.text = ""
        db_add("user", text)
        self.add_msg("me", text)
        # Скрыть чипы
        self.chips_row.opacity = 0
        self.chips_row.height = 0
        self.busy = True
        self.cancel_flag[0] = False
        # Показать стоп
        self.action_slot.clear_widgets()
        self.action_slot.add_widget(self.stop_btn)
        self.show_typing()
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def stop_generation(self):
        self.cancel_flag[0] = True
        self.sub.text = "остановлено"
        self.sub.color = DANGER

    def show_typing(self):
        if self.typing is None:
            self.typing = TypingBubble()
            self.grid.add_widget(self.typing)
            self.scroll_to_bottom()

    def hide_typing(self):
        if self.typing is not None:
            self.typing.stop()
            try: self.grid.remove_widget(self.typing)
            except Exception: pass
            self.typing = None

    def _worker(self, text):
        try:
            msgs = [{"role": "system",
                     "content": "Ты дружелюбный ассистент. Отвечай по-русски "
                                "ясно и по делу. Без эмодзи — только текст."}]
            for m in db_recent(14):
                msgs.append({"role": m["role"], "content": m["content"]})

            first = [True]
            def on_chunk(p):
                if self.cancel_flag[0]: return
                if first[0]:
                    first[0] = False
                    Clock.schedule_once(lambda *a: self._start_stream(), 0)
                self.sbuf += p
                if self.sev is None:
                    self.sev = Clock.schedule_once(
                        lambda *a: self._flush_stream(), 0.07)

            reply, err = ask_ai(msgs, on_chunk=on_chunk,
                                cancel_flag=self.cancel_flag)
        except Exception as e:
            reply, err = None, str(e)[:100]

        if reply:
            db_add("assistant", reply)

        def finish(*a):
            sb_ref = self.sb
            try:
                self._end_stream()
                self.hide_typing()
                if self.cancel_flag[0]:
                    if sb_ref is not None:
                        sb_ref.set_text((sb_ref._text or "") + " [остановлено]")
                elif reply:
                    if sb_ref is not None:
                        sb_ref.set_text(reply)
                    else:
                        self.add_msg("ai", reply)
                else:
                    self.add_msg("ai", "Ошибка: " + str(err))
                self.scroll_to_bottom()
            except Exception as e:
                try:
                    self.add_msg("ai", "UI: " + str(e)[:80])
                except Exception:
                    pass
            self.busy = False
            self.cancel_flag[0] = False
            # Вернуть send
            self.action_slot.clear_widgets()
            self.action_slot.add_widget(self.send_btn)
            self.sub.text = "онлайн"
            self.sub.color = ONLINE

        Clock.schedule_once(finish, 0)

    def _start_stream(self):
        self.hide_typing()
        self.sb = self.add_msg("ai", "")

    def _flush_stream(self):
        self.sev = None
        if self.sb and self.sbuf:
            self.sb.append(self.sbuf)
            self.sbuf = ""
            self.scroll_to_bottom()

    def _end_stream(self):
        if self.sev:
            try: self.sev.cancel()
            except Exception: pass
            self.sev = None
        if self.sb and self.sbuf:
            self.sb.append(self.sbuf)
            self.sbuf = ""
        self.sb = None

    def msg_menu(self, b):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14))
        preview = Label(text=b._text[:180],
                        color=TXT_DIM, size_hint=(1, None), height=dp(70),
                        halign="left", valign="top", font_size=sp(12))
        preview.bind(size=lambda *a: setattr(preview, "text_size", a[1]))
        content.add_widget(preview)

        def mk(t, cb, color=TXT):
            btn = Button(text=t, size_hint=(1, None), height=dp(48),
                         background_normal="", background_down="",
                         background_color=PANEL3, color=color,
                         font_size=sp(14))
            btn.bind(on_release=lambda *a: cb())
            return btn

        p = Popup(title="", content=content, size_hint=(0.85, 0.55),
                  title_size=0, background_color=PANEL,
                  separator_color=ACCENT)

        def cp():
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(b._text)
            except Exception: pass
            p.dismiss()

        def rg():
            p.dismiss()
            for m in reversed(db_messages()):
                if m["role"] == "user":
                    self.inp.text = m["content"]
                    self.send()
                    break

        content.add_widget(mk("Копировать", cp))
        if b.role == "ai":
            content.add_widget(mk("Сгенерировать заново", rg))
        p.open()

    def new_chat(self):
        global SESSION_ID
        SESSION_ID = new_session()
        self.load()
        self._build_chips()

    def export_chat(self):
        try:
            msgs = db_messages()
            if not msgs: return None
            fname = f"chat_{DT.now().strftime('%Y%m%d_%H%M%S')}.txt"
            path = os.path.join(EXPORT_DIR, fname)
            with open(path, "w", encoding="utf-8") as f:
                for m in msgs:
                    who = "Ты" if m["role"] == "user" else "AI"
                    f.write(f"{who} [{m['ts']}]: {m['content']}\n\n")
            return path
        except Exception:
            return None

    def copy_all_chat(self):
        try:
            from kivy.core.clipboard import Clipboard
            msgs = db_messages()
            text = "\n\n".join(
                f"{'Ты' if m['role']=='user' else 'AI'}: {m['content']}"
                for m in msgs)
            Clipboard.copy(text)
            return True
        except Exception:
            return False

    def open_menu(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14))
        p = Popup(title="Меню", title_color=TXT, separator_color=ACCENT,
                  background_color=PANEL, size_hint=(0.88, 0.72),
                  title_size=sp(16))

        def mk(t, cb, color=TXT):
            b = Button(text=t, size_hint=(1, None), height=dp(48),
                       background_normal="", background_down="",
                       background_color=PANEL3, color=color,
                       font_size=sp(14))
            b.bind(on_release=lambda *a: cb())
            return b

        def clr():
            db_clear(); p.dismiss(); self.load(); self._build_chips()

        def nc():
            p.dismiss(); self.new_chat()

        def export_action():
            path = self.export_chat()
            p.dismiss()
            if path:
                self.add_msg("ai", f"Сохранено в:\n{path}")
            else:
                self.add_msg("ai", "Не удалось сохранить файл")

        def copy_all():
            ok = self.copy_all_chat()
            p.dismiss()
            self.add_msg("ai", "Скопировано в буфер" if ok
                               else "Не удалось скопировать")

        def hp():
            p.dismiss()
            self.add_msg("ai",
                "Что умею:\n\n"
                "• Отвечаю на любые вопросы\n"
                "• Помню контекст диалога\n"
                "• Голосовой ввод (Android)\n"
                "• Кнопка Стоп — прервать ответ\n\n"
                "Действия:\n"
                "• + в шапке — новый чат\n"
                "• Три точки — это меню\n"
                "• Тап по сообщению — копировать/регенерировать")

        content.add_widget(mk("Новый чат", nc))
        content.add_widget(mk("Копировать весь чат", copy_all))
        content.add_widget(mk("Сохранить в файл", export_action))
        content.add_widget(mk("Очистить историю", clr, color=DANGER))
        content.add_widget(mk("Помощь", hp))
        p.content = content
        p.open()

# ═══════════════════════════════════════════════════════════
#  ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════
class ChatApp(App):
    def build(self):
        self.title = "AI Чат"
        try:
            Window.clearcolor = BG_TOP
        except Exception:
            pass
        return ChatRoot()
    def on_pause(self): return True
    def on_resume(self): pass

if __name__ == "__main__":
    try:
        ChatApp().run()
    except Exception:
        import traceback
        print("КРИТИЧЕСКАЯ ОШИБКА:")
        traceback.print_exc()
        try: input("Enter...")
        except Exception: pass
