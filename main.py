#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Чат — минималистичная версия."""
import os, sys, json, ssl, socket, threading, uuid
import urllib.request
from datetime import datetime as DT
import sqlite3

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

# ─── ЦВЕТА ───
BG      = (0.06, 0.07, 0.09, 1)
PANEL   = (0.10, 0.11, 0.14, 1)
PANEL2  = (0.15, 0.16, 0.20, 1)
ME_BG   = (0.18, 0.40, 0.85, 1)
AI_BG   = (0.14, 0.16, 0.19, 1)
TXT     = (0.93, 0.95, 0.97, 1)
TXT_D   = (0.55, 0.58, 0.64, 1)
ACCENT  = (0.23, 0.75, 0.51, 1)

# ─── ПРОВАЙДЕРЫ ───
PROVIDERS = [
    {"name": "KeylessAI",   "url": "https://keylessai.thryx.workers.dev/v1/chat/completions",
     "model": "auto",            "key": None,     "stream": True},
    {"name": "Kilo",        "url": "https://api.kilo.ai/api/gateway/chat/completions",
     "model": "kilo-auto/free",  "key": None,     "stream": True},
    {"name": "LLM7",        "url": "https://api.llm7.io/v1/chat/completions",
     "model": "default",         "key": "unused", "stream": False},
    {"name": "Pollinations","url": "https://text.pollinations.ai/openai",
     "model": "openai",          "key": None,     "stream": False},
]

ROOT = os.path.dirname(os.path.abspath(__file__)) or "."
DB_FILE = os.path.join(ROOT, "chat.db")

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Mobile"

# ─── БАЗА ───
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
except Exception as e:
    print("ОШИБКА БД:", e)
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

# ─── AI ───
def try_provider(prov, messages, on_chunk=None):
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
                    line = line.decode("utf-8", "ignore").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        j = json.loads(payload)
                    except Exception:
                        continue
                    try:
                        piece = j["choices"][0]["delta"].get("content", "")
                    except Exception:
                        piece = ""
                    if piece:
                        parts.append(piece)
                        if on_chunk:
                            try:
                                on_chunk(piece)
                            except Exception:
                                pass
                text = "".join(parts).strip()
                return (text, None) if text else (None, "пусто")
            else:
                raw = r.read().decode("utf-8", "ignore")
                j = json.loads(raw)
                if "choices" in j:
                    return j["choices"][0]["message"]["content"].strip(), None
                if "content" in j:
                    return str(j["content"]).strip(), None
                return raw.strip(), None
    except Exception as e:
        return None, str(e)[:60]

def ask_ai(messages, on_chunk=None):
    errs = []
    for prov in PROVIDERS:
        text, err = try_provider(prov, messages, on_chunk=on_chunk)
        if text:
            return text, None
        errs.append(prov["name"] + ":" + str(err))
    return None, " | ".join(errs[-2:])

# ═══════════════════════════════════════════════════════════
#  ПРОСТОЙ ПУЗЫРЬ
# ═══════════════════════════════════════════════════════════
class MsgBox(BoxLayout):
    """Пузырь сообщения. Простой прямоугольник."""
    def __init__(self, role, text, on_action=None, **kw):
        super(MsgBox, self).__init__(
            orientation="horizontal",
            size_hint=(1, None),
            padding=(dp(6), dp(3)),
            spacing=dp(6),
            **kw)

        self.role = role
        self._text = text
        self._on_action = on_action

        is_me = (role == "me")
        bg = ME_BG if is_me else AI_BG
        fg = (1, 1, 1, 1) if is_me else TXT

        # Аватар для AI
        if not is_me:
            av = Label(text="AI", color=ACCENT, bold=True,
                       size_hint=(None, 1), width=dp(26),
                       font_size=sp(10))
            self.add_widget(av)

        # Метка
        self.lbl = Label(
            text=text, markup=False, color=fg,
            size_hint=(0.72 if is_me else 0.85, None),
            halign="left", valign="top",
            padding=(dp(10), dp(8)),
            font_size=sp(15))

        # Фон (обычный прямоугольник)
        with self.lbl.canvas.before:
            Color(*bg)
            self._bgrect = Rectangle(pos=self.lbl.pos, size=self.lbl.size)
        self.lbl.bind(
            pos=lambda *a: setattr(self._bgrect, "pos", a[1]),
            size=lambda *a: setattr(self._bgrect, "size", a[1]))

        # Привязка высоты к тексту
        self.lbl.bind(texture_size=self._update_height)
        self.lbl.bind(width=self._update_textsize)

        # Раскладка
        if is_me:
            self.add_widget(BoxLayout(size_hint_x=0.15))  # spacer
            self.add_widget(self.lbl)
        else:
            self.add_widget(self.lbl)
            self.add_widget(BoxLayout(size_hint_x=0.10))  # spacer

        # Начальная высота
        self.height = dp(50)

        # Тап → меню
        self.lbl.bind(on_touch_down=self._touch)

    def _update_textsize(self, lbl, w):
        lbl.text_size = (w - dp(20), None)
        lbl.texture_update()

    def _update_height(self, lbl, ts):
        h = max(ts[1] + dp(16), dp(40))
        self.height = h + dp(6)
        lbl.height = h

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
        self.height = max(self.lbl.texture_size[1] + dp(16), dp(40)) + dp(6)

    def set_text(self, t):
        self._text = t
        self.lbl.text = t
        self.lbl.texture_update()
        self.height = max(self.lbl.texture_size[1] + dp(16), dp(40)) + dp(6)


# ═══════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ЭКРАН
# ═══════════════════════════════════════════════════════════
class ChatRoot(BoxLayout):
    def __init__(self, **kw):
        super(ChatRoot, self).__init__(orientation="vertical", **kw)
        self.busy = False
        self.sb = None
        self.sbuf = ""
        self.sev = None

        # Фон
        with self.canvas.before:
            Color(*BG)
            self._bgrect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bgrect, "pos", a[1]),
                  size=lambda *a: setattr(self._bgrect, "size", a[1]))

        # ─── Шапка ───
        head = BoxLayout(size_hint=(1, None), height=dp(54),
                         padding=(dp(8), dp(8)), spacing=dp(6))
        with head.canvas.before:
            Color(*PANEL)
            self._hbg = Rectangle(pos=head.pos, size=head.size)
        head.bind(pos=lambda *a: setattr(self._hbg, "pos", a[1]),
                  size=lambda *a: setattr(self._hbg, "size", a[1]))

        btn1 = Button(text="Меню", size_hint=(None, 1), width=dp(70),
                      background_normal="", background_down="",
                      background_color=PANEL2, color=TXT, font_size=sp(12))
        btn1.bind(on_release=lambda *a: self.open_menu())
        head.add_widget(btn1)

        self.title = Label(text="AI Чат", color=TXT, bold=True,
                           halign="center", valign="middle",
                           size_hint=(1, 1), font_size=sp(16))
        self.title.bind(size=lambda *a: setattr(self.title, "text_size", a[1]))
        head.add_widget(self.title)

        btn2 = Button(text="Новый", size_hint=(None, 1), width=dp(70),
                      background_normal="", background_down="",
                      background_color=PANEL2, color=TXT, font_size=sp(12))
        btn2.bind(on_release=lambda *a: self.new_chat())
        head.add_widget(btn2)

        self.add_widget(head)

        # ─── Скролл ───
        self.scroll = ScrollView(do_scroll_x=False)
        self.grid = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=dp(2), padding=(dp(4), dp(8)))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.add_widget(self.scroll)

        # ─── Низ ───
        foot = BoxLayout(size_hint=(1, None), height=dp(60),
                         padding=(dp(8), dp(8)), spacing=dp(6))
        with foot.canvas.before:
            Color(*PANEL)
            self._fbg = Rectangle(pos=foot.pos, size=foot.size)
        foot.bind(pos=lambda *a: setattr(self._fbg, "pos", a[1]),
                  size=lambda *a: setattr(self._fbg, "size", a[1]))

        self.inp = TextInput(hint_text="Сообщение...", multiline=False,
                             size_hint=(1, 1),
                             background_normal="", background_active="",
                             background_color=PANEL2,
                             foreground_color=TXT, cursor_color=ACCENT,
                             padding=(dp(12), dp(12)), font_size=sp(15))
        self.inp.bind(on_text_validate=self.send)
        foot.add_widget(self.inp)

        self.sbtn = Button(text=">", size_hint=(None, 1), width=dp(52),
                           background_normal="", background_down="",
                           background_color=ACCENT, color=(1, 1, 1, 1),
                           bold=True, font_size=sp(22))
        self.sbtn.bind(on_release=self.send)
        foot.add_widget(self.sbtn)

        self.add_widget(foot)

        Clock.schedule_once(lambda *a: self.load(), 0.2)

    def load(self):
        self.grid.clear_widgets()
        self.sb = None
        msgs = db_messages()
        if not msgs:
            self.add_msg("ai", "Привет! Напиши что угодно — отвечу.")
        else:
            for m in msgs:
                role = "me" if m["role"] == "user" else "ai"
                self.add_msg(role, m["content"])

    def add_msg(self, role, text):
        b = MsgBox(role, text, on_action=self.msg_menu)
        self.grid.add_widget(b)
        Clock.schedule_once(lambda *a: self.scroll_to_bottom(), 0.05)
        return b

    def scroll_to_bottom(self):
        try:
            self.scroll.scroll_y = 0
        except Exception:
            pass

    def send(self, *a):
        if self.busy:
            return
        text = self.inp.text.strip()
        if not text:
            return
        self.inp.text = ""
        db_add("user", text)
        self.add_msg("me", text)
        self.busy = True
        self.sbtn.disabled = True
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text):
        try:
            msgs = [{"role": "system", "content": "Ты дружелюбный ассистент. Отвечай по-русски."}]
            for m in db_recent(14):
                msgs.append({"role": m["role"], "content": m["content"]})

            first = [True]
            def on_chunk(p):
                if first[0]:
                    first[0] = False
                    Clock.schedule_once(lambda *a: self._start_stream(), 0)
                self.sbuf += p
                if self.sev is None:
                    self.sev = Clock.schedule_once(
                        lambda *a: self._flush_stream(), 0.08)

            reply, err = ask_ai(msgs, on_chunk=on_chunk)
        except Exception as e:
            reply, err = None, str(e)[:100]

        if reply:
            db_add("assistant", reply)

        def finish(*a):
            try:
                self._end_stream()
                if reply:
                    if self.sb is not None:
                        self.sb.set_text(reply)
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
            self.sbtn.disabled = False

        Clock.schedule_once(finish, 0)

    def _start_stream(self):
        self.sb = self.add_msg("ai", "")

    def _flush_stream(self):
        self.sev = None
        if self.sb and self.sbuf:
            self.sb.append(self.sbuf)
            self.sbuf = ""
            self.scroll_to_bottom()

    def _end_stream(self):
        if self.sev:
            try:
                self.sev.cancel()
            except Exception:
                pass
            self.sev = None
        if self.sb and self.sbuf:
            self.sb.append(self.sbuf)
            self.sbuf = ""
        self.sb = None

    def msg_menu(self, b):
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        content.add_widget(Label(text=b._text[:200], color=TXT,
                                 size_hint=(1, None), height=dp(80),
                                 halign="left", valign="top"))

        def mk(t, cb):
            btn = Button(text=t, size_hint=(1, None), height=dp(46),
                         background_normal="", background_down="",
                         background_color=PANEL2, color=TXT)
            btn.bind(on_release=lambda *a: cb())
            return btn

        p = Popup(title="", content=content, size_hint=(0.9, 0.5), title_size=0)

        def cp():
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(b._text)
            except Exception:
                pass
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
            content.add_widget(mk("Перегенерировать", rg))
        p.open()

    def new_chat(self):
        global SESSION_ID
        SESSION_ID = new_session()
        self.load()

    def open_menu(self):
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        p = Popup(title="Меню", title_color=TXT, separator_color=ACCENT,
                  background_color=PANEL, size_hint=(0.85, 0.55), title_size=sp(16))

        def mk(t, cb):
            b = Button(text=t, size_hint=(1, None), height=dp(48),
                       background_normal="", background_down="",
                       background_color=PANEL2, color=TXT)
            b.bind(on_release=lambda *a: cb())
            return b

        def clr():
            db_clear()
            p.dismiss()
            self.load()

        def new_chat_action():
            p.dismiss()
            self.new_chat()

        def help_action():
            p.dismiss()
            self.add_msg("ai",
                "Что умею:\n"
                "• Отвечаю на вопросы\n"
                "• Помню контекст\n"
                "• Тап по сообщению — меню\n\n"
                "Кнопки:\n"
                "• Новый — новый чат\n"
                "• Меню — эта панель")

        content.add_widget(mk("Новый чат", new_chat_action))
        content.add_widget(mk("Очистить", clr))
        content.add_widget(mk("Помощь", help_action))
        p.content = content
        p.open()


# ═══════════════════════════════════════════════════════════
#  ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════
class ChatApp(App):
    def build(self):
        self.title = "AI Чат"
        try:
            Window.clearcolor = BG
        except Exception:
            pass
        return ChatRoot()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    try:
        ChatApp().run()
    except Exception as e:
        import traceback
        print("КРИТИЧЕСКАЯ ОШИБКА:")
        traceback.print_exc()
        try:
            input("Enter...")
        except Exception:
            pass

