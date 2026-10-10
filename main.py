#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Чат Premium — rich-text Kivy assistant for Pydroid 3.

Core features: multiple chats, SQLite history, SSE responses, provider fallback,
notes, starred messages, safe calculator, image generation, voice I/O and themes.
"""
import os
import sys
import json
import base64
import hashlib
import platform
import mimetypes
import shutil
import webbrowser
import ssl
import socket
import threading
import uuid
import ast
import operator
import re
import math
import random
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime as DT

# App version used by the in-app GitHub Releases checker. Bump this per release.
APP_VERSION = "30"
UPDATE_API_URL = "https://api.github.com/repos/awayRu/Aish/releases/latest"


os.environ.setdefault("KIVY_NO_ARGS", "1")
# Keep Kivy console logging enabled: startup errors must remain visible in Pydroid.

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line, Triangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.uix.image import Image as KivyImage

# Android keyboard: disable automatic whole-window panning. ChatRoot adds a
# bottom inset when the IME appears, keeping the header stable and composer visible.
try:
    Window.softinput_mode = ""
except Exception:
    pass

# Keep softinput_mode empty. Android keyboard insets are handled by ChatRoot;
# using "below_target" pans the entire app and makes the chat jump upward.

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
THEMES = {
    "night": {
        "bg_top": (0.035, 0.043, 0.067, 1), "bg_bot": (0.075, 0.047, 0.125, 1),
        "panel": (0.075, 0.086, 0.118, 1), "panel2": (0.118, 0.133, 0.173, 1),
        "panel3": (0.157, 0.173, 0.220, 1), "bubble_me": (0.255, 0.435, 0.910, 1),
        "bubble_ai": (0.105, 0.122, 0.161, 1), "text": (0.945, 0.953, 0.973, 1),
        "text_dim": (0.610, 0.635, 0.690, 1), "text_faint": (0.400, 0.427, 0.486, 1),
        "accent": (0.365, 0.535, 1.000, 1), "accent_soft": (0.135, 0.190, 0.345, 1),
        "danger": (0.965, 0.365, 0.390, 1), "danger_bg": (0.255, 0.105, 0.145, 1),
        "success": (0.275, 0.855, 0.545, 1), "success_bg": (0.095, 0.215, 0.155, 1),
        "star": (1.0, 0.765, 0.245, 1), "star_bg": (0.285, 0.205, 0.065, 1),
        "avatar_me": (0.490, 0.310, 0.940, 1), "avatar_ai": (0.105, 0.735, 0.550, 1),
        "online": (0.275, 0.855, 0.545, 1), "chip": (0.125, 0.141, 0.184, 1),
        "chip_text": (0.780, 0.800, 0.850, 1), "shadow": (0, 0, 0, 0.24),
        "ring_bg": (0.035, 0.043, 0.067, 1),
    },
    "midnight": {
        "bg_top": (0.012, 0.016, 0.031, 1), "bg_bot": (0.035, 0.020, 0.075, 1),
        "panel": (0.047, 0.055, 0.082, 1), "panel2": (0.086, 0.094, 0.137, 1),
        "panel3": (0.125, 0.133, 0.180, 1), "bubble_me": (0.315, 0.205, 0.745, 1),
        "bubble_ai": (0.075, 0.082, 0.122, 1), "text": (0.920, 0.925, 0.960, 1),
        "text_dim": (0.600, 0.612, 0.680, 1), "text_faint": (0.365, 0.376, 0.435, 1),
        "accent": (0.625, 0.445, 1.000, 1), "accent_soft": (0.190, 0.125, 0.335, 1),
        "danger": (0.960, 0.365, 0.420, 1), "danger_bg": (0.225, 0.085, 0.135, 1),
        "success": (0.255, 0.800, 0.500, 1), "success_bg": (0.075, 0.190, 0.135, 1),
        "star": (1.0, 0.735, 0.220, 1), "star_bg": (0.235, 0.165, 0.055, 1),
        "avatar_me": (0.415, 0.225, 0.860, 1), "avatar_ai": (0.105, 0.655, 0.505, 1),
        "online": (0.255, 0.800, 0.500, 1), "chip": (0.095, 0.102, 0.149, 1),
        "chip_text": (0.765, 0.780, 0.835, 1), "shadow": (0, 0, 0, 0.34),
        "ring_bg": (0.012, 0.016, 0.031, 1),
    },
    "aurora": {
        "bg_top": (0.025, 0.031, 0.070, 1), "bg_bot": (0.043, 0.055, 0.114, 1),
        "panel": (0.055, 0.065, 0.125, 1), "panel2": (0.080, 0.092, 0.170, 1),
        "panel3": (0.120, 0.135, 0.235, 1), "bubble_me": (0.315, 0.285, 0.835, 1),
        "bubble_ai": (0.069, 0.080, 0.145, 1), "text": (0.957, 0.965, 0.995, 1),
        "text_dim": (0.625, 0.664, 0.765, 1), "text_faint": (0.397, 0.432, 0.555, 1),
        "accent": (0.475, 0.455, 1.000, 1), "accent_soft": (0.145, 0.140, 0.315, 1),
        "danger": (0.975, 0.390, 0.490, 1), "danger_bg": (0.245, 0.085, 0.155, 1),
        "success": (0.280, 0.890, 0.690, 1), "success_bg": (0.070, 0.205, 0.180, 1),
        "star": (1.000, 0.790, 0.310, 1), "star_bg": (0.270, 0.195, 0.065, 1),
        "avatar_me": (0.430, 0.330, 0.960, 1), "avatar_ai": (0.105, 0.735, 0.625, 1),
        "online": (0.300, 0.905, 0.700, 1), "chip": (0.078, 0.091, 0.166, 1),
        "chip_text": (0.815, 0.835, 0.905, 1), "shadow": (0.005, 0.008, 0.025, 0.28),
        "ring_bg": (0.025, 0.031, 0.070, 1),
    },
    "daylight": {
        "bg_top": (0.955, 0.965, 0.982, 1), "bg_bot": (0.910, 0.929, 0.965, 1),
        "panel": (0.977, 0.982, 0.992, 1), "panel2": (0.900, 0.916, 0.947, 1),
        "panel3": (0.835, 0.857, 0.900, 1), "bubble_me": (0.245, 0.455, 0.925, 1),
        "bubble_ai": (0.992, 0.994, 1.000, 1), "text": (0.090, 0.102, 0.145, 1),
        "text_dim": (0.365, 0.390, 0.455, 1), "text_faint": (0.565, 0.585, 0.645, 1),
        "accent": (0.165, 0.365, 0.875, 1), "accent_soft": (0.835, 0.885, 0.995, 1),
        "danger": (0.825, 0.180, 0.220, 1), "danger_bg": (0.985, 0.885, 0.900, 1),
        "success": (0.105, 0.590, 0.350, 1), "success_bg": (0.860, 0.950, 0.890, 1),
        "star": (0.780, 0.520, 0.055, 1), "star_bg": (0.985, 0.930, 0.795, 1),
        "avatar_me": (0.390, 0.265, 0.890, 1), "avatar_ai": (0.080, 0.555, 0.400, 1),
        "online": (0.105, 0.590, 0.350, 1), "chip": (0.865, 0.886, 0.925, 1),
        "chip_text": (0.235, 0.255, 0.315, 1), "shadow": (0, 0, 0, 0.10),
        "ring_bg": (0.955, 0.965, 0.982, 1),
    },
}
FONTS = {
    "small": {"body": sp(12), "title": sp(14), "ts": sp(8)},
    "medium": {"body": sp(14), "title": sp(17), "ts": sp(8)},
    "large": {"body": sp(17), "title": sp(20), "ts": sp(9)},
    "xlarge": {"body": sp(19), "title": sp(22), "ts": sp(9)},
}
SPACING = {"compact": dp(1), "normal": dp(5), "comfortable": dp(10)}

PROVIDERS = [
    {"name": "KeylessAI", "url": "https://keylessai.thryx.workers.dev/v1/chat/completions",
     "model": "auto", "key": None, "stream": True},
    {"name": "Kilo", "url": "https://api.kilo.ai/api/gateway/chat/completions",
     "model": "kilo-auto/free", "key": None, "stream": True},
    {"name": "LLM7", "url": "https://api.llm7.io/v1/chat/completions",
     "model": "default", "key": "unused", "stream": False},
]

ROOT = os.path.dirname(os.path.abspath(__file__)) or "."
DB_FILE = os.path.join(ROOT, "chat.db")
IMG_DIR = os.path.join(ROOT, "images")
os.makedirs(IMG_DIR, exist_ok=True)
UA = "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Mobile"


def make_ssl_context():
    """Use normal TLS certificate verification; certifi is optional."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()
SAFE_PROMPT = (
    "Ты дружелюбный ИИ-ассистент. Отвечай по-русски, ясно и по делу. "
    "Оформляй ответы в Markdown, который будет отображён красиво: выделяй **жирным** "
    "ключевые выводы, важные слова, числа и предупреждения; используй короткие заголовки "
    "для больших разделов, маркированные списки для перечислений и нумерованные шаги для инструкций. "
    "Используй *курсив* умеренно, цитаты для важных фрагментов и блоки ```язык ... ``` для кода. "
    "Не превращай короткий ответ в избыточно размеченный документ: выделяй только то, что помогает "
    "быстро понять главное. Если просят ответить в определённом количестве слов, строго соблюдай это. "
    "Для кода сохраняй отступы и добавляй короткие пояснения. "
    "Не выдумывай факты; если не уверен, честно скажи об этом. "
    "Не утверждай, что выполнял действия, которые не выполнял. "
    "Если спрашивают, кто ты или как тебя зовут, отвечай: «Я — AI Chat, ИИ-помощник этого приложения». "
    "Не называй случайный сторонний сервис или поставщика модели своей личностью; не выдумывай, какая именно модель отвечает."
)

IDENTITY_REPLY = (
    "Я — AI Chat, ИИ-помощник этого приложения. Я помогаю отвечать на вопросы, "
    "объяснять темы, писать тексты и разбираться с кодом. Моё имя в этом приложении — AI Chat."
)

def is_identity_question(text):
    """Recognize direct identity questions so providers cannot answer them inconsistently."""
    value = re.sub(r"[^\w]+", " ", str(text or "").lower(), flags=re.UNICODE).strip()
    patterns = (
        r"\bкто ты\b", r"\bты кто\b", r"\bкак тебя зовут\b",
        r"\bчто ты за (?:ии|нейросеть|модель|ассистент)\b",
        r"\bкакая у тебя модель\b", r"\bназови свою модель\b",
        r"\bкто ты такой\b", r"\bкакая у тебя нейросеть\b",
        r"\bна какой модели ты работаешь\b", r"\bты работаешь на какой модели\b",
        r"\bчто за нейросеть\b", r"\bwhat are you\b",
        r"\bwho are you\b", r"\bwhat model are you\b",
    )
    return any(re.search(pattern, value) for pattern in patterns)

STATE = {
    "theme": "aurora", "font_size": "medium", "font_weight": "normal", "font_family": "roboto",
    "msg_spacing": "normal", "show_time": True, "show_avatars": True,
    "voice_out": False, "last_provider": "-", "last_model": "-",
    # User-configurable behavior. Values are persisted in SQLite meta.
    "provider_preference": "auto", "fallback_enabled": True,
    "streaming": True, "creativity": "balanced", "response_length": "normal",
    "auto_scroll": True, "show_suggestions": True, "show_model_status": True,
    "message_animations": True, "performance_mode": True, "sparkle_background": True,
    "image_size": "512", "custom_prompt": "",
}


def T(key):
    return THEMES.get(STATE.get("theme"), THEMES["night"])[key]


def F(key):
    return FONTS.get(STATE.get("font_size"), FONTS["medium"])[key]


def msg_spacing():
    return SPACING.get(STATE.get("msg_spacing"), SPACING["normal"])


# Font files commonly available on Android. The bundled Roboto font is a safe fallback.
_FONT_CANDIDATES = {
    "roboto": ("/system/fonts/Roboto-Regular.ttf", "/system/fonts/RobotoStatic-Regular.ttf"),
    "serif": ("/system/fonts/NotoSerif-Regular.ttf",),
    "mono": ("/system/fonts/RobotoMono-Regular.ttf", "/system/fonts/NotoSansMono-Regular.ttf",
             "/system/fonts/DroidSansMono.ttf"),
    "noto": ("/system/fonts/NotoSans-Regular.ttf", "/system/fonts/Roboto-Regular.ttf"),
}
_FONT_CACHE = {}

def font_path(family=None):
    """Return an existing font path when available; never rely on optional font downloads."""
    family = family or STATE.get("font_family", "roboto")
    if family in _FONT_CACHE:
        return _FONT_CACHE[family]
    for candidate in _FONT_CANDIDATES.get(family, _FONT_CANDIDATES["roboto"]):
        if os.path.isfile(candidate):
            _FONT_CACHE[family] = candidate
            return candidate
    # Kivy ships its own Roboto face; it works on both Android and desktop.
    _FONT_CACHE[family] = "Roboto"
    return _FONT_CACHE[family]

def _kivy_escape(value):
    """Escape untrusted response text before adding Kivy markup tags."""
    return (str(value).replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;"))

def _color_hex(name="accent"):
    color = T(name)
    return "{:02X}{:02X}{:02X}".format(
        max(0, min(255, int(color[0] * 255))),
        max(0, min(255, int(color[1] * 255))),
        max(0, min(255, int(color[2] * 255))),
    )

# Compile Markdown expressions once: long replies are rendered repeatedly while streaming.
_MARKDOWN_INLINE_RE = re.compile(
    r"\[([^\]\n]+)\]\((https?://[^\s)]+|mailto:[^\s)]+)\)"
    r"|`([^`\n]+)`|\*\*(.+?)\*\*|__(.+?)__|~~(.+?)~~"
    r"|(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)"
    r"|(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)|\+\+(.+?)\+\+"
)
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_MARKDOWN_HR_RE = re.compile(r"^\s{0,3}([-*_]\s*){3,}$")
_MARKDOWN_QUOTE_RE = re.compile(r"^\s{0,3}>\s?(.*)$")
_MARKDOWN_BULLET_RE = re.compile(r"^(\s*)([-*+]\s+|\d+[.)]\s+)(.*)$")
_MARKDOWN_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_MARKDOWN_CALLOUT_RE = re.compile(r"^\s*(Важно|Внимание|Предупреждение|Осторожно|Примечание|Итог|Вывод|Ответ)\s*:\s*(.*)$", re.I)
_MARKDOWN_TITLE_LINE_RE = re.compile(r"^\s*(Главный вывод|Краткая аналогия|Коротко|Итог|Вывод|Пример|Пошагово|Что важно)\s*:?[\s.!]*$", re.I)


def _markdown_table_cells(line):
    """Parse a Markdown table row without treating escaped pipes as separators."""
    value = str(line).strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith(r"\|"):
        value = value[:-1]
    return [part.replace(r"\|", "|").strip() for part in re.split(r"(?<!\\)\|", value)]


def render_markdown(text, base_size=None):
    """Render a safe mobile-friendly Markdown subset as Kivy Label markup.

    Wide Markdown tables are converted to readable stacked rows on phones instead of
    showing raw pipes. Expensive regular expressions are compiled once, and this
    function deliberately avoids network calls or image processing.
    Returns (markup_text, link_map).
    """
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    accent = _color_hex("accent")
    muted = _color_hex("text_dim")
    danger = _color_hex("danger")
    mono = font_path("mono")
    size = float(base_size if base_size is not None else F("body"))
    links = {}
    next_link = [0]

    def inline(line):
        pieces = []
        pos = 0
        for match in _MARKDOWN_INLINE_RE.finditer(line):
            pieces.append(_kivy_escape(line[pos:match.start()]))
            groups = match.groups()
            if groups[0] is not None:
                title, url = groups[0], groups[1]
                # Only web URLs and mailto links are allowed; never create executable schemes.
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme not in ("http", "https", "mailto"):
                    pieces.append(_kivy_escape(title))
                else:
                    ref = "mdlink{}".format(next_link[0])
                    next_link[0] += 1
                    links[ref] = url
                    pieces.append("[ref={}][color={}][u]{}[/u][/color][/ref]".format(
                        ref, accent, _kivy_escape(title)))
            elif groups[2] is not None:
                pieces.append("[font={}][color={}][size={}]{}[/size][/color][/font]".format(
                    mono, accent, max(1, round(size * 0.92)), _kivy_escape(groups[2])))
            elif groups[3] is not None or groups[4] is not None:
                value = groups[3] if groups[3] is not None else groups[4]
                pieces.append("[b]{}[/b]".format(_kivy_escape(value)))
            elif groups[5] is not None:
                pieces.append("[s]{}[/s]".format(_kivy_escape(groups[5])))
            elif groups[6] is not None:
                pieces.append("[i]{}[/i]".format(_kivy_escape(groups[6])))
            elif groups[7] is not None:
                pieces.append("[i]{}[/i]".format(_kivy_escape(groups[7])))
            elif groups[8] is not None:
                pieces.append("[u]{}[/u]".format(_kivy_escape(groups[8])))
            pos = match.end()
        pieces.append(_kivy_escape(line[pos:]))
        return "".join(pieces)

    def append_spacer():
        if output and output[-1] != "":
            output.append("")

    lines = raw.split("\n")
    output = []
    in_code = False
    code_line_no = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            code_line_no = 0
            hint = stripped[3:].strip()
            if in_code:
                append_spacer()
                if hint:
                    output.append("[color={}][size={}][b]  {}[/b][/size][/color]".format(
                        muted, max(1, round(size * 0.78)), _kivy_escape(hint.upper())))
            else:
                output.append("")
            i += 1
            continue
        if in_code:
            code_line_no += 1
            # Line counters help with long code while keeping everything in one low-cost Label.
            output.append("[color={}][font={}][size={}] {:02d} [/size][/font][/color]"
                          "[color={}][font={}][size={}]{}[/size][/font][/color]".format(
                muted, mono, max(1, round(size * 0.72)), code_line_no,
                accent, mono, max(1, round(size * 0.90)), _kivy_escape(line) if line else " "))
            i += 1
            continue

        # Render Markdown tables as stacked mobile rows: readable even at 320 dp wide.
        # Some models omit the Markdown separator row, so detect repeated pipe rows too.
        next_line_is_separator = (i + 1 < len(lines)
            and bool(_MARKDOWN_TABLE_SEPARATOR_RE.fullmatch(lines[i + 1].strip())))
        repeated_pipe_rows = (i + 1 < len(lines) and line.count("|") >= 2
            and lines[i + 1].count("|") >= 2 and bool(lines[i + 1].strip()))
        if "|" in line and (next_line_is_separator or repeated_pipe_rows):
            if next_line_is_separator:
                headers = _markdown_table_cells(line)
                i += 2  # Skip the header separator row.
                rows = []
                while i < len(lines) and lines[i].count("|") >= 2 and lines[i].strip():
                    if _MARKDOWN_TABLE_SEPARATOR_RE.fullmatch(lines[i].strip()):
                        i += 1
                        continue
                    row = _markdown_table_cells(lines[i])
                    if any(cell for cell in row):
                        rows.append(row)
                    i += 1
            else:
                table_rows = []
                while i < len(lines) and lines[i].count("|") >= 2 and lines[i].strip():
                    row_line = lines[i]
                    if not _MARKDOWN_TABLE_SEPARATOR_RE.fullmatch(row_line.strip()):
                        row = _markdown_table_cells(row_line)
                        if any(cell for cell in row):
                            table_rows.append(row)
                    i += 1
                known_headers = {"понятие", "термин", "название", "описание", "определение",
                                 "пример", "свойство", "характеристика", "значение", "тип", "вид"}
                first = [cell.lower().rstrip(":") for cell in table_rows[0]] if table_rows else []
                is_header = sum(cell in known_headers for cell in first) >= 2
                if is_header:
                    headers, rows = table_rows[0], table_rows[1:]
                else:
                    max_cols = max((len(row) for row in table_rows), default=2)
                    inferred = ["Понятие", "Описание", "Пример", "Дополнение", "Дополнение 2"]
                    headers = [inferred[min(col, len(inferred)-1)] for col in range(max_cols)]
                    rows = table_rows
            append_spacer()
            title = " · ".join(headers[:3])
            output.append("[size={}][color={}][b]ТАБЛИЦА · {}[/b][/color][/size]".format(
                max(1, round(size * 0.90)), accent, inline(title)))
            for row in rows:
                if len(row) < len(headers):
                    row += [""] * (len(headers) - len(row))
                label = row[0] if row else ""
                if label:
                    output.append("[color={}][b]• {}[/b][/color]".format(accent, inline(label)))
                for col_index in range(1, min(len(headers), len(row))):
                    if row[col_index]:
                        output.append("[color={}][b]{}:[/b][/color] {}".format(
                            muted, inline(headers[col_index]), inline(row[col_index])))
                output.append("")
            continue

        if not stripped:
            output.append("")
            i += 1
            continue
        heading = _MARKDOWN_HEADING_RE.match(line)
        if heading:
            append_spacer()
            level = len(heading.group(1))
            scale = {1: 1.38, 2: 1.27, 3: 1.18, 4: 1.10, 5: 1.05, 6: 1.0}[level]
            output.append("[size={}][color={}][b]{}[/b][/color][/size]".format(
                max(1, round(size * scale)), accent if level <= 3 else muted,
                inline(heading.group(2))))
            i += 1
            continue
        if _MARKDOWN_HR_RE.match(line):
            output.append("[color={}]━━━━━━━━━━━━━━━━━━━━[/color]".format(muted))
            i += 1
            continue
        quote = _MARKDOWN_QUOTE_RE.match(line)
        if quote:
            output.append("[color={}][b]│[/b][/color] [i]{}[/i]".format(accent, inline(quote.group(1))))
            i += 1
            continue
        callout = _MARKDOWN_CALLOUT_RE.match(line)
        if callout:
            word, content = callout.group(1), callout.group(2)
            use_danger = word.lower() in ("важно", "внимание", "предупреждение", "осторожно")
            color = danger if use_danger else accent
            output.append("[color={}][b]{}:[/b][/color] {}".format(
                color, _kivy_escape(word), inline(content)))
            i += 1
            continue
        title_line = _MARKDOWN_TITLE_LINE_RE.match(line)
        if title_line:
            append_spacer()
            title = stripped.rstrip(":.! ")
            output.append("[size={}][color={}][b]◆ {}[/b][/color][/size]".format(
                max(1, round(size * 1.08)), accent, _kivy_escape(title)))
            i += 1
            continue
        bullet = _MARKDOWN_BULLET_RE.match(line)
        if bullet:
            marker, body = bullet.group(2), bullet.group(3)
            prefix = marker.strip() if marker[0].isdigit() else "•"
            indent = "  " if bullet.group(1) else ""
            output.append("{}[color={}][b]{}[/b][/color] {}".format(
                indent, accent, _kivy_escape(prefix), inline(body)))
            i += 1
            continue
        output.append(inline(line))
        i += 1
    return "\n".join(output), links

# ---------------------------------------------------------------------------
# Safe calculator: AST allow-list, size/complexity limits, no arbitrary eval.
# ---------------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_MATH = math
_ALLOWED_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "sin": math.sin,
    "cos": math.cos, "tan": math.tan, "log": math.log, "log10": math.log10,
    "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
}


def _safe_eval(node, depth=0):
    if depth > 30:
        raise ValueError("слишком сложное выражение")
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, depth + 1)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("разрешены только числа")
        if len(str(node.value)) > 80:
            raise ValueError("слишком большое число")
        return node.value
    if isinstance(node, ast.Num):  # compatibility with older Python ASTs
        return node.n
    if isinstance(node, ast.Name):
        constants = {"pi": math.pi, "e": math.e}
        if node.id in constants:
            return constants[node.id]
        raise ValueError("неизвестная константа")
    if isinstance(node, ast.UnaryOp):
        fn = _ALLOWED_OPS.get(type(node.op))
        if fn is None:
            raise ValueError("оператор не разрешён")
        return fn(_safe_eval(node.operand, depth + 1))
    if isinstance(node, ast.BinOp):
        fn = _ALLOWED_OPS.get(type(node.op))
        if fn is None:
            raise ValueError("оператор не разрешён")
        left = _safe_eval(node.left, depth + 1)
        right = _safe_eval(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
            raise ValueError("слишком большая степень")
        result = fn(left, right)
        if isinstance(result, (int, float)) and abs(result) > 1e100:
            raise ValueError("результат слишком большой")
        return result
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise ValueError("функция не разрешена")
        if node.keywords or len(node.args) > 2:
            raise ValueError("неподходящие аргументы функции")
        args = [_safe_eval(arg, depth + 1) for arg in node.args]
        return _ALLOWED_FUNCS[node.func.id](*args)
    raise ValueError("недопустимое выражение")


def calc_safe(text):
    """Return (result, error). The expression is never evaluated with eval()."""
    s = (text or "").lower().strip()
    for source, target in [
        ("умножить на", "*"), ("разделить на", "/"), ("делить на", "/"),
        ("плюс", "+"), ("минус", "-"), ("умножить", "*"),
        ("корень из", "sqrt("), ("корень", "sqrt("),
        ("^", "**"), ("π", "pi"), ("пи", "pi"), ("×", "*"), ("÷", "/"),
        (",", "."),
    ]:
        s = s.replace(source, target)
    s = s.strip()
    if len(s) > 160:
        return None, "Выражение слишком длинное (максимум 160 символов)."
    # Friendly explicit syntax: "квадратное a b c".
    q = re.fullmatch(r"квадратное\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", s)
    if q:
        a, b, c = map(float, q.groups())
        if a == 0:
            return None, "Коэффициент a не должен быть равен нулю."
        d = b * b - 4 * a * c
        if d < 0:
            return f"D = {d:.6g}; действительных корней нет.", None
        if d == 0:
            return f"x = {-b / (2*a):.8g}", None
        return f"x1 = {(-b + math.sqrt(d))/(2*a):.8g}; x2 = {(-b - math.sqrt(d))/(2*a):.8g}", None
    # Accept "sqrt(25)" and turn a spoken "корень из 25" into that form.
    if "sqrt(" in s and not s.endswith(")"):
        s += ")"
    try:
        tree = ast.parse(s, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 45:
            return None, "Слишком сложное выражение."
        result = _safe_eval(tree)
        if isinstance(result, complex) or not isinstance(result, (int, float)):
            return None, "Не удалось получить числовой результат."
        if not math.isfinite(float(result)):
            return None, "Результат не является конечным числом."
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 10)
        return result, None
    except ZeroDivisionError:
        return None, "Деление на ноль невозможно."
    except Exception as exc:
        return None, f"Не получилось вычислить выражение: {str(exc)[:100]}"

# ---------------------------------------------------------------------------
# Android voice adapters (optional in Pydroid)
# ---------------------------------------------------------------------------
ANDROID = None
try:
    import androidhelper
    ANDROID = androidhelper.Android()
except Exception:
    try:
        import android
        ANDROID = android.Android()
    except Exception:
        ANDROID = None


def voice_input():
    if not ANDROID:
        return None
    try:
        result = ANDROID.recognizeSpeech("Скажите запрос", "ru-RU", "free_form").result
        if isinstance(result, dict):
            return result.get("result") or result.get("text")
        return result or None
    except Exception:
        return None


def voice_output(text):
    if not ANDROID:
        return
    value = str(text)[:2500]
    try:
        ANDROID.speak(value)
    except Exception:
        try:
            ANDROID.ttsSpeak(value)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# SQLite persistence; all access to this shared connection is locked.
# ---------------------------------------------------------------------------
try:
    DB = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=20)
except Exception:
    DB = sqlite3.connect(":memory:", check_same_thread=False, timeout=20)
DB.row_factory = sqlite3.Row
DB_LOCK = threading.RLock()
with DB_LOCK:
    DB.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY, title TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL, ts TEXT NOT NULL,
            starred INTEGER NOT NULL DEFAULT 0,
            image_path TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, ts TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id);
    """)
    # Safe migration for databases created by earlier versions.
    try:
        DB.execute("ALTER TABLE messages ADD COLUMN starred INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        DB.execute("ALTER TABLE messages ADD COLUMN image_path TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    DB.execute("CREATE INDEX IF NOT EXISTS idx_messages_starred ON messages(starred, id)")
    DB.commit()


def _meta_get(key, default=""):
    with DB_LOCK:
        row = DB.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
        return row["v"] if row else default


def _meta_set(key, value):
    with DB_LOCK:
        DB.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (key, str(value)))
        DB.commit()


_SETTING_KEYS = (
    "theme", "font_size", "font_weight", "font_family", "msg_spacing", "show_time", "show_avatars",
    "voice_out", "provider_preference", "fallback_enabled", "streaming", "creativity",
    "response_length", "auto_scroll", "show_suggestions", "show_model_status",
    "message_animations", "performance_mode", "sparkle_background", "image_size", "custom_prompt",
)


def save_settings():
    """Persist app preferences in one place, retaining compatibility with older databases."""
    with DB_LOCK:
        for key in _SETTING_KEYS:
            value = STATE.get(key, "")
            if isinstance(value, bool):
                value = "1" if value else "0"
            DB.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (key, str(value)))
        DB.commit()


_SETTING_DEFAULTS = {
    "theme": "aurora", "font_size": "medium", "font_weight": "normal", "font_family": "roboto", "msg_spacing": "normal",
    "show_time": True, "show_avatars": True, "voice_out": False,
    "provider_preference": "auto", "fallback_enabled": True, "streaming": True,
    "creativity": "balanced", "response_length": "normal", "auto_scroll": True,
    "show_suggestions": True, "show_model_status": True, "message_animations": True,
    "performance_mode": True, "sparkle_background": True, "image_size": "512", "custom_prompt": "",
}
_SETTING_CHOICES = {
    "theme": set(THEMES), "font_size": set(FONTS), "font_weight": {"normal", "bold"},
    "font_family": {"roboto", "serif", "mono", "noto"},
    "msg_spacing": set(SPACING), "provider_preference": {"auto", "KeylessAI", "Kilo", "LLM7", "Pollinations"},
    "creativity": {"precise", "balanced", "creative"},
    "response_length": {"short", "normal", "long"},
    "image_size": {"512", "768"},
}
_BOOLEAN_SETTINGS = {"show_time", "show_avatars", "voice_out", "fallback_enabled", "streaming",
                     "auto_scroll", "show_suggestions", "show_model_status", "message_animations", "performance_mode", "sparkle_background"}
for _k, _default in _SETTING_DEFAULTS.items():
    _stored = _meta_get(_k, "1" if _default is True else "0" if _default is False else str(_default))
    if _k in _BOOLEAN_SETTINGS:
        STATE[_k] = str(_stored).strip().lower() in ("1", "true", "yes", "on")
    elif _k in _SETTING_CHOICES and _stored not in _SETTING_CHOICES[_k]:
        STATE[_k] = _default
    elif _k == "custom_prompt":
        STATE[_k] = str(_stored)[:5000]
    else:
        STATE[_k] = str(_stored)

# Current Pollinations API key; never hard-code personal credentials in source.
# One-time design refresh migration. Existing sessions/history remain untouched.
try:
    if _meta_get("ui_redesign_version", "0") != "28":
        if STATE.get("theme") == "night":
            STATE["theme"] = "aurora"
        # The new surface is intentionally calmer by default; particles remain optional.
        STATE["sparkle_background"] = False
        _meta_set("ui_redesign_version", "28")
        save_settings()
except Exception:
    pass

IMAGE_API_KEY = _meta_get("pollinations_api_key", "").strip()

def save_image_api_key(value):
    global IMAGE_API_KEY
    IMAGE_API_KEY = str(value or "").strip()[:300]
    _meta_set("pollinations_api_key", IMAGE_API_KEY)


def new_session():
    sid = uuid.uuid4().hex[:12]
    now = DT.now().strftime("%Y-%m-%d %H:%M:%S")
    with DB_LOCK:
        DB.execute("INSERT INTO sessions(id,title,created,updated) VALUES(?,?,?,?)", (sid, "Новый чат", now, now))
        DB.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('session_id',?)", (sid,))
        DB.commit()
    return sid


def get_session():
    sid = _meta_get("session_id", "")
    if sid:
        with DB_LOCK:
            row = DB.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone()
        if row:
            return sid
    return new_session()

SESSION_ID = get_session()


def db_add(role, content, sid=None, starred=False, image_path=""):
    sid = sid or SESSION_ID
    content = str(content)[:20000]
    now = DT.now().strftime("%Y-%m-%d %H:%M:%S")
    with DB_LOCK:
        cur = DB.execute("INSERT INTO messages(session_id,role,content,ts,starred,image_path) VALUES(?,?,?,?,?,?)",
                         (sid, role, content, now, 1 if starred else 0, str(image_path or "")[:1000]))
        msg_id = cur.lastrowid
        DB.execute("UPDATE sessions SET updated=? WHERE id=?", (now, sid))
        if role == "user":
            row = DB.execute("SELECT title FROM sessions WHERE id=?", (sid,)).fetchone()
            if row and row["title"] == "Новый чат":
                title = content.strip().splitlines()[0][:42] if content.strip() else "Новый чат"
                DB.execute("UPDATE sessions SET title=? WHERE id=?", (title, sid))
        DB.commit()
    return msg_id


def db_messages(limit=500, sid=None):
    sid = sid or SESSION_ID
    with DB_LOCK:
        rows = DB.execute(
            "SELECT * FROM (SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (sid, max(1, int(limit)))).fetchall()
        return [dict(row) for row in rows]


def db_recent(n=14, sid=None):
    sid = sid or SESSION_ID
    with DB_LOCK:
        rows = DB.execute("SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                          (sid, max(1, int(n)))).fetchall()
        return list(reversed([dict(row) for row in rows]))


def db_clear(sid=None):
    sid = sid or SESSION_ID
    now = DT.now().strftime("%Y-%m-%d %H:%M:%S")
    with DB_LOCK:
        DB.execute("DELETE FROM messages WHERE session_id=?", (sid,))
        DB.execute("UPDATE sessions SET title='Новый чат', updated=? WHERE id=?", (now, sid))
        DB.commit()


def db_sessions():
    with DB_LOCK:
        return [dict(row) for row in DB.execute("SELECT * FROM sessions ORDER BY updated DESC").fetchall()]


def db_delete_session(sid):
    with DB_LOCK:
        DB.execute("DELETE FROM messages WHERE session_id=?", (sid,))
        DB.execute("DELETE FROM sessions WHERE id=?", (sid,))
        DB.commit()


def db_session_title(sid=None):
    with DB_LOCK:
        row = DB.execute("SELECT title FROM sessions WHERE id=?", (sid or SESSION_ID,)).fetchone()
        return row["title"] if row else "AI Чат"


def db_search(query, limit=50):
    pattern = "%" + str(query).replace("%", "\\%").replace("_", "\\_") + "%"
    with DB_LOCK:
        rows = DB.execute("SELECT m.*, s.title AS session_title FROM messages m LEFT JOIN sessions s ON s.id=m.session_id "
                          "WHERE m.content LIKE ? ESCAPE '\\' ORDER BY m.id DESC LIMIT ?", (pattern, limit)).fetchall()
        return [dict(row) for row in rows]


def db_toggle_star(msg_id):
    with DB_LOCK:
        DB.execute("UPDATE messages SET starred=1-starred WHERE id=?", (msg_id,))
        DB.commit()
        row = DB.execute("SELECT starred FROM messages WHERE id=?", (msg_id,)).fetchone()
        return bool(row["starred"]) if row else False


def db_starred(limit=100):
    with DB_LOCK:
        rows = DB.execute("SELECT m.*, s.title AS session_title FROM messages m JOIN sessions s ON s.id=m.session_id "
                          "WHERE m.starred=1 ORDER BY m.id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


def db_trim_from(sid, msg_id):
    with DB_LOCK:
        DB.execute("DELETE FROM messages WHERE session_id=? AND id>=?", (sid, msg_id))
        DB.commit()


def db_note_add(text):
    with DB_LOCK:
        DB.execute("INSERT INTO notes(text,ts) VALUES(?,?)", (str(text)[:4000], DT.now().strftime("%Y-%m-%d %H:%M:%S")))
        DB.commit()


def db_notes():
    with DB_LOCK:
        return [dict(row) for row in DB.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()]


def db_note_delete(note_id):
    with DB_LOCK:
        DB.execute("DELETE FROM notes WHERE id=?", (note_id,))
        DB.commit()

# ---------------------------------------------------------------------------
# API clients: fallback only happens before any streamed text was received.
# This avoids joining partial answers from two different providers.
# ---------------------------------------------------------------------------


def _read_json_response(url, payload, headers, timeout=45):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
            raw = response.read().decode("utf-8", "replace")
        return raw, None
    except urllib.error.HTTPError as exc:
        try: detail = exc.read().decode("utf-8", "replace")[:180]
        except Exception: detail = ""
        return None, f"HTTP {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return None, "таймаут соединения"
        return None, f"сеть: {str(reason)[:100]}"
    except (socket.timeout, TimeoutError):
        return None, "таймаут соединения"
    except ssl.SSLError as exc:
        return None, f"ошибка TLS: {str(exc)[:100]}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:100]}"


def _stream_request(req, on_chunk=None, cancel_event=None):
    chunks = []
    try:
        with urllib.request.urlopen(req, timeout=45, context=SSL_CONTEXT) as response:
            while not (cancel_event and cancel_event.is_set()):
                line = response.readline()
                if not line:
                    break
                line = line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                piece = ""
                try:
                    choice = data["choices"][0]
                    piece = choice.get("delta", {}).get("content", "")
                    if not piece:
                        piece = choice.get("message", {}).get("content", "")
                    if isinstance(piece, list):
                        piece = "".join(str(x.get("text", "")) for x in piece if isinstance(x, dict))
                except Exception:
                    piece = ""
                if piece:
                    piece = str(piece)
                    chunks.append(piece)
                    if on_chunk:
                        try: on_chunk(piece)
                        except Exception: pass
    except urllib.error.HTTPError as exc:
        try: detail = exc.read().decode("utf-8", "replace")[:160]
        except Exception: detail = ""
        # Don't retry via another provider after partial text has been shown.
        if chunks:
            return "".join(chunks).strip(), None
        return None, f"HTTP {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        if chunks:
            return "".join(chunks).strip(), None
        return None, f"сеть: {str(getattr(exc, 'reason', exc))[:90]}"
    except (socket.timeout, TimeoutError):
        if chunks:
            return "".join(chunks).strip(), None
        return None, "таймаут потока"
    except ssl.SSLError as exc:
        if chunks:
            return "".join(chunks).strip(), None
        return None, f"ошибка TLS: {str(exc)[:90]}"
    except Exception as exc:
        if chunks:
            return "".join(chunks).strip(), None
        return None, f"{type(exc).__name__}: {str(exc)[:90]}"
    text = "".join(chunks).strip()
    if cancel_event and cancel_event.is_set():
        return text or None, None if text else "остановлено"
    return (text, None) if text else (None, "пустой потоковый ответ")


def try_provider(provider, messages, on_chunk=None, cancel_event=None):
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream, application/json", "User-Agent": UA}
    if provider.get("key"):
        headers["Authorization"] = "Bearer " + provider["key"]
    history = messages[-10:] if provider["name"] == "Pollinations" else messages
    temperature = {"precise": 0.25, "balanced": 0.7, "creative": 1.0}.get(
        STATE.get("creativity", "balanced"), 0.7)
    max_tokens = {"short": 800, "normal": 1800, "long": 3000}.get(
        STATE.get("response_length", "normal"), 1800)
    use_stream = bool(provider.get("stream") and STATE.get("streaming", True))
    payload = {"model": provider["model"], "messages": history, "temperature": temperature,
               "max_tokens": max_tokens, "stream": use_stream}
    if use_stream:
        req = urllib.request.Request(provider["url"], data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                     headers=headers, method="POST")
        text, error = _stream_request(req, on_chunk=on_chunk, cancel_event=cancel_event)
    else:
        raw, error = _read_json_response(provider["url"], payload, headers)
        if error:
            return None, error
        try:
            data = json.loads(raw)
        except Exception:
            data = None
        text = None
        if isinstance(data, dict):
            try:
                text = data["choices"][0]["message"].get("content")
            except Exception:
                pass
            if not text and isinstance(data.get("content"), str):
                text = data["content"]
            if not text and data.get("error"):
                return None, "API: " + str(data["error"])[:120]
        elif raw and raw.strip():
            # Some simple compatible APIs return plain text.
            text = raw.strip()
        text = text.strip() if isinstance(text, str) else None
        error = None if text else "пустой или неизвестный формат ответа"
    if text:
        STATE["last_provider"] = provider["name"]
        STATE["last_model"] = provider["model"]
        return text, None
    return None, error or "пустой ответ"


def friendly_api_error(error):
    """Turn provider-specific JSON/HTML errors into short actionable Russian text."""
    raw = str(error or "").strip()
    low = raw.lower()
    match = re.search(r"http\s*(\d{3})", low)
    code = int(match.group(1)) if match else None
    if code in (401, 403) or "unauthorized" in low or "invalid api key" in low:
        return "ключ API неверный или не имеет доступа"
    if code == 402 or "payment_required" in low or "insufficient_quota" in low or "quota_exceeded" in low:
        return "лимит или баланс API исчерпан"
    if code == 429 or "rate limit" in low or "too many requests" in low:
        return "слишком много запросов; попробуй позже"
    if code == 404:
        return "модель или endpoint не найден"
    if code and 500 <= code <= 599:
        return "временная ошибка сервера API"
    if "таймаут" in low or "timed out" in low or "timeout" in low:
        return "сервер не ответил вовремя"
    if "ssl" in low or "tls" in low:
        return "ошибка защищённого соединения"
    if "сеть" in low or "network" in low or "urlerror" in low:
        return "ошибка соединения; проверь интернет"
    # Avoid printing provider HTML/JSON payloads directly into the chat.
    if raw.startswith("HTTP "):
        return raw.split(":", 1)[0] + " — запрос отклонён"
    return raw[:110] if raw else "неизвестная ошибка"


def _provider_list():
    """Return the selected provider first, optionally retaining automatic fallbacks."""
    providers = list(PROVIDERS)
    pollinations = {
        "name": "Pollinations", "url": "https://gen.pollinations.ai/v1/chat/completions",
        "model": "openai/gpt-5.4-nano", "key": IMAGE_API_KEY, "stream": False,
    }
    if IMAGE_API_KEY:
        providers.append(pollinations)
    preferred = STATE.get("provider_preference", "auto")
    if preferred != "auto":
        picked = [p for p in providers if p.get("name") == preferred]
        others = [p for p in providers if p.get("name") != preferred]
        if picked:
            providers = picked + (others if STATE.get("fallback_enabled", True) else [])
        elif not STATE.get("fallback_enabled", True):
            return []
    elif not STATE.get("fallback_enabled", True):
        # With no preference, keep the default free provider as the single route.
        providers = providers[:1]
    return providers


def ask_ai(messages, on_chunk=None, cancel_event=None):
    errors = []
    available = _provider_list()
    if not available:
        return None, "Выбранный провайдер недоступен: проверь ключ API или включи автоматический резерв."
    for provider in available:
        if cancel_event and cancel_event.is_set():
            return None, "остановлено"
        text, error = try_provider(provider, messages, on_chunk=on_chunk, cancel_event=cancel_event)
        if text:
            return text, None
        errors.append(f"{provider['name']}: {friendly_api_error(error)}")
    return None, "\n".join(errors[-3:])

# ---------------------------------------------------------------------------
# Image generation helper. Callback is always sent back to the Kivy thread.
# ---------------------------------------------------------------------------


def generate_image(prompt, callback, cancel_event=None):
    """Generate an image through AI Horde using its public anonymous key.

    No personal API key is required. Anonymous jobs have low queue priority, so
    polling is bounded and the user receives a readable timeout/error message.
    Callback is always scheduled on the Kivy thread.
    """
    clean_prompt = str(prompt or "").strip()[:700]

    def worker():
        path = None
        error = None
        request_id = None
        try:
            if not clean_prompt:
                raise ValueError("Напиши, что нужно нарисовать.")
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Создание изображения отменено.")

            base = "https://aihorde.net/api/v2"
            # AI Horde requires the API key in the HTTP HEADER, not in the JSON body.
            # 0000000000 is the documented anonymous key; registered-user keys are optional.
            headers = {
                "User-Agent": UA,
                "Client-Agent": "AI-Chat:28:github.com/awayRu/Aish",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "apikey": "0000000000",
            }
            payload = {
                "prompt": clean_prompt,
                "params": {
                    "width": int(STATE.get("image_size", "512")) if str(STATE.get("image_size", "512")).isdigit() else 512,
                    "height": int(STATE.get("image_size", "512")) if str(STATE.get("image_size", "512")).isdigit() else 512,
                    "steps": 20,
                    "n": 1,
                    "cfg_scale": 7.0,
                    "karras": True,
                },
                "nsfw": False,
                "censor_nsfw": True,
                "r2": True,
                "shared": True,
            }
            payload["params"]["width"] = max(256, min(768, payload["params"]["width"]))
            payload["params"]["height"] = max(256, min(768, payload["params"]["height"]))

            req = urllib.request.Request(
                base + "/generate/async",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=35, context=SSL_CONTEXT) as response:
                    submitted = json.loads(response.read(1024 * 1024).decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read(800).decode("utf-8", "replace")
                raise RuntimeError(f"AI Horde не принял запрос (HTTP {exc.code}): {detail[:300]}")

            request_id = submitted.get("id")
            if not request_id:
                raise RuntimeError("AI Horde не вернул номер задания. Попробуй ещё раз.")

            # Anonymous queue may take several minutes. Poll no more often than every 3s.
            deadline = __import__("time").monotonic() + 300
            status = {}
            while __import__("time").monotonic() < deadline:
                if cancel_event and cancel_event.is_set():
                    try:
                        cancel_req = urllib.request.Request(
                            base + "/generate/status/" + urllib.parse.quote(str(request_id), safe=""),
                            headers=headers, method="DELETE")
                        urllib.request.urlopen(cancel_req, timeout=8, context=SSL_CONTEXT).close()
                    except Exception:
                        pass
                    raise InterruptedError("Создание изображения отменено.")
                check_req = urllib.request.Request(
                    base + "/generate/check/" + urllib.parse.quote(str(request_id), safe=""),
                    headers={"User-Agent": UA, "Client-Agent": "AI-Chat:28:github.com/awayRu/Aish", "Accept": "application/json", "apikey": "0000000000"})
                with urllib.request.urlopen(check_req, timeout=20, context=SSL_CONTEXT) as response:
                    status = json.loads(response.read(1024 * 1024).decode("utf-8"))
                if status.get("faulted"):
                    raise RuntimeError("AI Horde не смог выполнить генерацию. Попробуй другой запрос.")
                if status.get("done"):
                    break
                __import__("time").sleep(3)
            else:
                raise TimeoutError("AI Horde пока не нашёл свободного исполнителя. Очередь анонимных запросов может быть долгой; попробуй позже.")

            status_req = urllib.request.Request(
                base + "/generate/status/" + urllib.parse.quote(str(request_id), safe=""),
                headers={"User-Agent": UA, "Client-Agent": "AI-Chat:28:github.com/awayRu/Aish", "Accept": "application/json", "apikey": "0000000000"})
            with urllib.request.urlopen(status_req, timeout=30, context=SSL_CONTEXT) as response:
                result = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
            generations = result.get("generations") or []
            if not generations:
                raise RuntimeError("Задание завершено, но AI Horde не вернул изображение.")
            image_url = generations[0].get("img") or generations[0].get("url")
            if not image_url or not str(image_url).startswith(("https://", "http://")):
                raise RuntimeError("AI Horde вернул некорректную ссылку на изображение.")
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Создание изображения отменено.")

            image_req = urllib.request.Request(str(image_url), headers={"User-Agent": UA, "Accept": "image/*"})
            with urllib.request.urlopen(image_req, timeout=60, context=SSL_CONTEXT) as response:
                data = response.read(15 * 1024 * 1024 + 1)
                content_type = (response.headers.get("Content-Type") or "").lower()
            if not data:
                raise RuntimeError("AI Horde вернул пустой файл изображения.")
            if len(data) > 15 * 1024 * 1024:
                raise RuntimeError("Изображение превышает ограничение 15 МБ.")
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                ext = ".png"
            elif data.startswith(b"\xff\xd8\xff"):
                ext = ".jpg"
            elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                ext = ".webp"
            else:
                raise RuntimeError("Сервис вернул файл неизвестного формата (" + content_type[:50] + ").")
            filename = "horde_" + DT.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6] + ext
            path = os.path.join(IMG_DIR, filename)
            with open(path, "wb") as file:
                file.write(data)
        except urllib.error.URLError as exc:
            error = "Не удалось подключиться к AI Horde. Проверь интернет и попробуй снова. " + str(exc)[:180]
        except InterruptedError:
            error = "Создание изображения отменено."
        except Exception as exc:
            error = str(exc)[:500] or type(exc).__name__
        Clock.schedule_once(lambda _dt, pth=path, err=error: callback(pth, err), 0)

    threading.Thread(target=worker, daemon=True).start()

# ---------------------------------------------------------------------------
# Reusable visual widgets
# ---------------------------------------------------------------------------

def style_button(button, bg=None, fg=None, font=14, bold=False, radius=dp(14)):
    """Layered premium button style; safe to re-apply without duplicate event bindings."""
    base_bg = tuple(bg or T("panel3"))
    button._rounded_style = {"bg": base_bg, "radius": radius}
    button.background_normal = ""
    button.background_down = ""
    button.background_color = (0, 0, 0, 0)
    button.color = fg or T("text")
    button.font_size = sp(font)
    button.bold = bold
    button.padding = (dp(10), dp(7))

    def update(*_):
        style = button._rounded_style
        x, y = button.pos
        w, h = button.size
        r = min(style["radius"], max(dp(3), h / 2))
        pressed = getattr(button, "state", "normal") == "down"
        b = style["bg"]
        # Subtle movement/brightness feedback instead of changing layout geometry.
        if pressed:
            fill = tuple(max(0.0, c * 0.84) for c in b[:3]) + (b[3] if len(b) > 3 else 1,)
        else:
            fill = b
        rim_rgb = T("accent")
        button.canvas.before.clear()
        with button.canvas.before:
            Color(0, 0, 0, 0.14 if STATE.get("theme") != "daylight" else 0.045)
            RoundedRectangle(pos=(x, y - dp(1.4)), size=(w, h), radius=[r])
            Color(rim_rgb[0], rim_rgb[1], rim_rgb[2], 0.12 if not pressed else 0.38)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
            Color(*fill)
            RoundedRectangle(pos=(x + dp(1), y + dp(1)),
                             size=(max(0, w - dp(2)), max(0, h - dp(2))), radius=[max(dp(2), r - dp(1))])
            if not pressed and h > dp(10):
                Color(1, 1, 1, 0.055 if STATE.get("theme") != "daylight" else 0.18)
                Line(points=[x + r * 0.7, y + h - dp(1.6), x + w - r * 0.7, y + h - dp(1.6)],
                     width=dp(0.65))
    if not getattr(button, "_rounded_style_bound", False):
        button.bind(pos=update, size=update)
        try:
            button.bind(state=update)
        except Exception:
            pass
        def press(*_):
            if not STATE.get("performance_mode", True):
                Animation(opacity=0.90, d=0.06).start(button)
        def release(*_):
            if not STATE.get("performance_mode", True):
                Animation(opacity=1, d=0.10).start(button)
        button.bind(on_press=press, on_release=release)
        button._rounded_style_bound = True
    update()
    return button


class IconButton(ButtonBehavior, Widget):
    def __init__(self, icon="plus", callback=None, size_px=dp(42), bg_key="panel2", **kwargs):
        super().__init__(size_hint=(None, None), width=size_px, height=size_px, **kwargs)
        self.icon = icon
        self.callback = callback
        self.size_px = size_px
        self.bg_key = bg_key
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        pressed = getattr(self, "state", "normal") == "down"
        with self.canvas.before:
            # Shadow + luminous rim + inset surface make controls read as physical elements.
            Color(0, 0, 0, 0.20 if STATE.get("theme") != "daylight" else 0.055)
            RoundedRectangle(pos=(x, y-dp(1.8)), size=(w, h), radius=[self.size_px * 0.5])
            accent = T("accent")
            Color(accent[0], accent[1], accent[2], 0.30 if not pressed else 0.72)
            RoundedRectangle(pos=(x-dp(0.5), y-dp(0.2)), size=(w+dp(1), h+dp(1)), radius=[self.size_px * 0.5])
            bg = T(self.bg_key)
            if pressed:
                bg = tuple(c * 0.82 for c in bg[:3]) + (bg[3],)
            Color(*bg)
            RoundedRectangle(pos=(x+dp(1.1), y+dp(1.1)), size=(max(0,w-dp(2.2)), max(0,h-dp(2.2))),
                             radius=[max(dp(2), self.size_px * 0.5-dp(1.1))])
            if not pressed:
                Color(1, 1, 1, 0.055 if STATE.get("theme") != "daylight" else 0.20)
                Line(points=[x+w*0.31, y+h-dp(2.8), x+w*0.69, y+h-dp(2.8)], width=dp(0.7))
        with self.canvas:
            Color(*T("text"))
            cx, cy = self.center
            s = self.size_px * 0.22
            if self.icon == "plus":
                Line(points=[cx-s, cy, cx+s, cy], width=dp(2.2), cap="round")
                Line(points=[cx, cy-s, cx, cy+s], width=dp(2.2), cap="round")
            elif self.icon == "search":
                Line(circle=(cx-s*0.25, cy+s*0.2, s*0.75), width=dp(2))
                Line(points=[cx+s*0.25, cy-s*0.25, cx+s*0.85, cy-s*0.85], width=dp(2.2), cap="round")
            elif self.icon == "gear":
                Line(circle=(cx, cy, s*0.8), width=dp(2))
                Line(circle=(cx, cy, s*0.32), width=dp(2))
                for i in range(8):
                    angle = math.radians(i*45)
                    Line(points=[cx+math.cos(angle)*s*0.8, cy+math.sin(angle)*s*0.8,
                                 cx+math.cos(angle)*s*1.08, cy+math.sin(angle)*s*1.08], width=dp(2))
            elif self.icon == "menu":
                for off in (-s*0.65, 0, s*0.65):
                    Ellipse(pos=(cx-dp(2), cy+off-dp(2)), size=(dp(4), dp(4)))
            elif self.icon == "send":
                Color(1, 1, 1, 1)
                Triangle(points=[cx-s, cy+s*0.8, cx+s*1.1, cy, cx-s, cy-s*0.8])
                Line(points=[cx-s*0.2, cy, cx+s*0.35, cy], width=dp(1.5))
            elif self.icon == "stop":
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=(cx-s*0.55, cy-s*0.55), size=(s*1.1, s*1.1), radius=[dp(3)])
            elif self.icon == "mic":
                RoundedRectangle(pos=(cx-s*0.30, cy-s*0.15), size=(s*0.60, s*1.2), radius=[s*0.3])
                Line(points=[cx-s*0.55, cy-s*0.05, cx-s*0.55, cy-s*0.25, cx, cy-s*0.6,
                             cx+s*0.55, cy-s*0.25, cx+s*0.55, cy-s*0.05], width=dp(1.8))
                Line(points=[cx, cy-s*0.6, cx, cy-s*0.9], width=dp(1.8))
            elif self.icon == "down":
                Line(points=[cx-s*0.65, cy+s*0.25, cx, cy-s*0.4, cx+s*0.65, cy+s*0.25], width=dp(2.2), joint="round")
            elif self.icon == "smile":
                Line(circle=(cx, cy, s*0.95), width=dp(1.7))
                Ellipse(pos=(cx-s*0.43, cy+s*0.18), size=(dp(2.5), dp(2.5)))
                Ellipse(pos=(cx+s*0.25, cy+s*0.18), size=(dp(2.5), dp(2.5)))
                Line(points=[cx-s*0.42, cy-s*0.18, cx-s*0.20, cy-s*0.38,
                             cx+s*0.15, cy-s*0.42, cx+s*0.42, cy-s*0.16],
                     width=dp(1.7), joint="round")
            elif self.icon == "sparkle":
                Line(points=[cx, cy+s, cx, cy-s], width=dp(1.9), cap="round")
                Line(points=[cx-s, cy, cx+s, cy], width=dp(1.9), cap="round")
                Line(points=[cx-s*0.55, cy+s*0.55, cx+s*0.55, cy-s*0.55], width=dp(1.1), cap="round")
                Line(points=[cx-s*0.55, cy-s*0.55, cx+s*0.55, cy+s*0.55], width=dp(1.1), cap="round")

    def on_press(self):
        if not STATE.get("performance_mode", True):
            Animation(opacity=0.72, d=0.07).start(self)

    def on_release(self):
        if not STATE.get("performance_mode", True):
            Animation(opacity=1, d=0.12).start(self)
        if self.callback:
            self.callback()


class Avatar(Widget):
    def __init__(self, letter, color, size_px=dp(34), **kwargs):
        super().__init__(size_hint=(None, None), width=size_px, height=size_px, **kwargs)
        self.letter = letter
        self.avatar_color = color
        self.bind(pos=self.redraw, size=self.redraw)
        self.label = Label(text=letter, color=(1,1,1,1), bold=True, font_size=sp(10),
                           size_hint=(None, None), size=self.size, pos=self.pos,
                           halign="center", valign="middle")
        self.add_widget(self.label)
        self.redraw()

    def redraw(self, *_):
        self.label.pos = self.pos
        self.label.size = self.size
        self.label.text_size = self.size
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*T("shadow")); Ellipse(pos=(self.x+dp(1), self.y-dp(1)), size=self.size)
            Color(*self.avatar_color); Ellipse(pos=self.pos, size=self.size)


class ChatChip(ButtonBehavior, BoxLayout):
    def __init__(self, text, callback=None, **kwargs):
        super().__init__(orientation="horizontal", size_hint=(None, None), height=dp(38), padding=(dp(14), dp(5)), **kwargs)
        self.text_value = text
        self.callback = callback
        self.label = Label(text=text, color=T("chip_text"), font_size=sp(12), halign="center", valign="middle",
                           size_hint=(None, 1), width=dp(100), shorten=True, shorten_from="right")
        self.label.bind(size=lambda *_: setattr(self.label, "text_size", self.label.size))
        self.add_widget(self.label)
        self.width = max(dp(112), self.label.texture_size[0] + dp(34))
        with self.canvas.before:
            Color(*T("chip")); self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(19)])
        self.bind(pos=lambda *_: setattr(self.rect, "pos", self.pos), size=lambda *_: setattr(self.rect, "size", self.size))

    def on_release(self):
        if self.callback: self.callback(self.text_value)


class BrandMark(Widget):
    """Small, font-independent app mark built from Kivy canvas primitives."""
    def __init__(self, size_px=dp(36), **kwargs):
        super().__init__(size_hint=(None, None), size=(size_px, size_px), **kwargs)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        cx, cy = self.center
        r = min(w, h) * 0.47
        a = T("accent")
        with self.canvas:
            Color(a[0], a[1], a[2], 0.10)
            Ellipse(pos=(cx-r, cy-r), size=(2*r, 2*r))
            Color(a[0], a[1], a[2], 0.22)
            Line(circle=(cx, cy, r*0.83), width=dp(1.0))
            Color(*T("panel3"))
            Ellipse(pos=(cx-r*0.64, cy-r*0.64), size=(1.28*r, 1.28*r))
            Color(*T("accent"))
            # Minimal four-point star; no emoji font dependency.
            Line(points=[cx, cy+r*0.42, cx+r*0.10, cy+r*0.10,
                         cx+r*0.42, cy, cx+r*0.10, cy-r*0.10,
                         cx, cy-r*0.42, cx-r*0.10, cy-r*0.10,
                         cx-r*0.42, cy, cx-r*0.10, cy+r*0.10, cx, cy+r*0.42],
                 width=dp(1.55), close=True, joint="round")
            Color(1, 1, 1, 0.92)
            Ellipse(pos=(cx-dp(1.2), cy-dp(1.2)), size=(dp(2.4), dp(2.4)))


class PromptTile(ButtonBehavior, BoxLayout):
    """Premium quick-action card with numbered badge and tactile highlight."""
    def __init__(self, title, description, glyph, callback=None, **kwargs):
        super().__init__(orientation="vertical", size_hint=(1, None), height=dp(69),
                         padding=(dp(11), dp(7)), spacing=dp(2), **kwargs)
        self.callback = callback
        self.glyph = str(glyph)
        self.title_text = title
        self.description = description
        heading = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(27), spacing=dp(8))
        badge = BoxLayout(size_hint=(None, None), size=(dp(29), dp(25)), padding=(dp(2), dp(1)))
        with badge.canvas.before:
            ac = T("accent")
            Color(ac[0], ac[1], ac[2], 0.17)
            self._badge_bg = RoundedRectangle(pos=badge.pos, size=badge.size, radius=[dp(8)])
            Color(ac[0], ac[1], ac[2], 0.34)
            self._badge_rim = Line(rounded_rectangle=(badge.x, badge.y, badge.width, badge.height, dp(8)), width=dp(0.7))
        badge.bind(pos=lambda *_: self._sync_badge(badge), size=lambda *_: self._sync_badge(badge))
        badge.add_widget(make_label(self.glyph, 8.5, "accent", True, halign="center"))
        heading.add_widget(badge)
        heading.add_widget(make_label(title, 10.5, "text", True, size_hint=(1, 1)))
        self.add_widget(heading)
        self.add_widget(make_label(description, 9.1, "text_dim", False,
                                   size_hint=(1, None), height=dp(19)))
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw)
        self.redraw()

    def _sync_badge(self, badge):
        try:
            self._badge_bg.pos = badge.pos
            self._badge_bg.size = badge.size
            self._badge_rim.rounded_rectangle = (badge.x, badge.y, badge.width, badge.height, dp(8))
        except Exception:
            pass

    def redraw(self, *_):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        pressed = getattr(self, "state", "normal") == "down"
        accent = T("accent")
        with self.canvas.before:
            Color(0, 0, 0, 0.19 if STATE.get("theme") != "daylight" else 0.035)
            RoundedRectangle(pos=(x+dp(1), y-dp(1.4)), size=(w, h), radius=[dp(15)])
            Color(accent[0], accent[1], accent[2], 0.26 if not pressed else 0.66)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(15)])
            fill = T("accent_soft") if pressed else T("panel2")
            Color(*fill)
            RoundedRectangle(pos=(x+dp(1), y+dp(1)), size=(max(0, w-dp(2)), max(0, h-dp(2))), radius=[dp(14)])
            Color(1, 1, 1, 0.075 if not pressed else 0.12)
            Line(points=[x+dp(16), y+h-dp(1.8), x+w-dp(16), y+h-dp(1.8)], width=dp(0.6))
            Color(accent[0], accent[1], accent[2], 0.52 if not pressed else 0.92)
            Line(points=[x+dp(1.5), y+dp(13), x+dp(1.5), y+h-dp(13)], width=dp(1.0))

    def on_release(self):
        if self.callback:
            self.callback()


class WelcomePanel(BoxLayout):
    """Deliberate, polished empty state instead of a fake assistant chat bubble."""
    def __init__(self, callback, **kwargs):
        # Set defaults on kwargs before super().__init__. Passing size_hint/height both
        # explicitly and through **kwargs raises TypeError and aborts the first empty chat.
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", dp(402))
        super().__init__(orientation="vertical", padding=(dp(12), dp(11)),
                         spacing=dp(7), **kwargs)
        self.callback = callback
        self.bind(pos=self._sync_bg, size=self._sync_bg)
        with self.canvas.before:
            Color(0, 0, 0, 0.26 if STATE.get("theme") != "daylight" else 0.06)
            self._shadow = RoundedRectangle(pos=(self.x+dp(1), self.y-dp(4)), size=self.size, radius=[dp(25)])
            Color(*T("panel"))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(25)])
            a = T("accent")
            Color(a[0], a[1], a[2], 0.065 if STATE.get("theme") != "daylight" else 0.025)
            self._glow = Ellipse(pos=(self.x + self.width*0.34, self.top-dp(126)),
                                 size=(self.width*0.72, dp(190)))
            teal = T("avatar_ai")
            Color(teal[0], teal[1], teal[2], 0.028 if STATE.get("theme") != "daylight" else 0.015)
            self._glow2 = Ellipse(pos=(self.x-dp(75), self.y+dp(18)),
                                  size=(self.width*0.70, dp(120)))
            Color(a[0], a[1], a[2], 0.40)
            self._rim = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(25)),
                             width=dp(0.9))

        top = BoxLayout(size_hint=(1, None), height=dp(42), spacing=dp(9))
        top.add_widget(BrandMark(dp(36)))
        words = BoxLayout(orientation="vertical", spacing=0)
        words.add_widget(make_label("AI CHAT  /  AISH", 10, "accent", True,
                                    size_hint=(1, None), height=dp(17)))
        words.add_widget(make_label("ТВОЙ ЛИЧНЫЙ ПОМОЩНИК", 9, "text_dim", False,
                                    size_hint=(1, None), height=dp(17)))
        top.add_widget(words)
        status_pill = BoxLayout(size_hint=(None, None), size=(dp(70), dp(25)), padding=(dp(4), dp(2)))
        with status_pill.canvas.before:
            ok = T("success")
            Color(ok[0], ok[1], ok[2], 0.11)
            self._status_pill_bg = RoundedRectangle(pos=status_pill.pos, size=status_pill.size, radius=[dp(12)])
            Color(ok[0], ok[1], ok[2], 0.23)
            self._status_pill_rim = Line(rounded_rectangle=(status_pill.x, status_pill.y, status_pill.width, status_pill.height, dp(12)), width=dp(0.6))
        status_pill.bind(pos=lambda *_: self._sync_status_pill(status_pill), size=lambda *_: self._sync_status_pill(status_pill))
        status_pill.add_widget(make_label("● ГОТОВ", 7.5, "online", True, halign="center"))
        top.add_widget(status_pill)
        self.add_widget(top)
        self.add_widget(make_label("Твоя идея.\nНаш следующий шаг.", 23, "text", True,
                                   size_hint=(1, None), height=dp(61), valign="middle"))
        self.add_widget(make_label("Разберём сложное, напишем код или превратим мысль в готовый результат.",
                                   10.5, "text_dim", False, size_hint=(1, None), height=dp(35), valign="top"))
        self.add_widget(make_label("БЫСТРЫЙ СТАРТ  /  ВЫБЕРИ НАПРАВЛЕНИЕ", 8.5, "accent", True,
                                   size_hint=(1, None), height=dp(16)))
        grid = GridLayout(cols=2, spacing=dp(8), size_hint=(1, None), height=dp(151))
        prompts = [
            ("Объясни тему", "Просто и с примерами", "01", "Объясни просто"),
            ("Помоги с кодом", "Напиши и разберись", "02", "Помоги с кодом"),
            ("Создай текст", "Идея — готовый текст", "03", "Создай текст"),
            ("Нарисуй кота", "Генерация изображения", "04", "Нарисуй кота"),
        ]
        for title, desc, glyph, chip in prompts:
            grid.add_widget(PromptTile(title, desc, glyph,
                                       callback=lambda value=chip: self.callback(value)))
        self.add_widget(grid)
        self.add_widget(make_label("История хранится на устройстве · нажми на карточку или напиши запрос ниже",
                                   9, "text_faint", False, size_hint=(1, None), height=dp(22), valign="middle"))

    def _sync_bg(self, *_):
        self._shadow.pos = (self.x+dp(1), self.y-dp(4))
        self._shadow.size = self.size
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._rim.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(25))
        self._glow.pos = (self.x + self.width*0.34, self.top-dp(126))
        self._glow.size = (self.width*0.72, dp(190))
        self._glow2.pos = (self.x-dp(75), self.y+dp(18))
        self._glow2.size = (self.width*0.70, dp(120))

    def _sync_status_pill(self, pill):
        try:
            self._status_pill_bg.pos = pill.pos
            self._status_pill_bg.size = pill.size
            self._status_pill_rim.rounded_rectangle = (pill.x, pill.y, pill.width, pill.height, dp(12))
        except Exception:
            pass


class TypingDots(Widget):
    """Low-cost animated three-dot indicator for waiting and streaming states."""
    def __init__(self, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(28), dp(18)), **kwargs)
        self._phase = 0.0
        self._dot_colors = []
        self._dot_shapes = []
        with self.canvas:
            for _index in range(3):
                a = T("accent")
                color = Color(a[0], a[1], a[2], 0.45)
                shape = Ellipse(pos=self.pos, size=(dp(4.5), dp(4.5)))
                self._dot_colors.append(color)
                self._dot_shapes.append(shape)
        self.bind(pos=self._sync_dots, size=self._sync_dots)
        self._sync_dots()
        self._event = Clock.schedule_interval(self._tick, 1.0/18.0)

    def _sync_dots(self, *_):
        size = dp(4.5)
        for index, shape in enumerate(self._dot_shapes):
            shape.pos = (self.x + dp(3) + index*dp(9), self.center_y-size/2)
            shape.size = (size, size)

    def _tick(self, dt):
        self._phase = (self._phase + max(0.0, min(float(dt), 0.1))*5.2) % (math.pi*2)
        accent = T("accent")
        for index, color in enumerate(self._dot_colors):
            alpha = 0.20 + 0.72*(0.5+0.5*math.sin(self._phase-index*1.45))
            color.rgba = (accent[0], accent[1], accent[2], alpha)
        return True

    def stop(self):
        event = getattr(self, "_event", None)
        if event is not None:
            try:
                event.cancel()
            except Exception:
                pass
            self._event = None


class RoundedPopup(ModalView):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (0.92, 0.84))
        kwargs.setdefault("background_color", (0, 0, 0, 0.58))
        kwargs.setdefault("background", "")
        kwargs.setdefault("auto_dismiss", True)
        super().__init__(**kwargs)
        outer = BoxLayout(orientation="vertical", padding=dp(2))
        with outer.canvas.before:
            Color(*T("panel")); self.rect = RoundedRectangle(pos=outer.pos, size=outer.size, radius=[dp(24)])
        outer.bind(pos=lambda *_: setattr(self.rect, "pos", outer.pos), size=lambda *_: setattr(self.rect, "size", outer.size))
        self.container = BoxLayout(orientation="vertical", spacing=dp(7), padding=(dp(14), dp(13)))
        outer.add_widget(self.container)
        self.add_widget(outer)


def make_label(text, size=14, color_key="text", bold=False, halign="left", valign="middle", **kwargs):
    label = Label(text=text, color=T(color_key), bold=bold, font_size=sp(size), halign=halign, valign=valign, **kwargs)
    label.bind(size=lambda *_: setattr(label, "text_size", label.size))
    return label


def popup_button(text, callback, variant="default", height=dp(48)):
    palette = {"default": (T("panel3"), T("text")), "accent": (T("accent"), (1,1,1,1)),
               "danger": (T("danger_bg"), T("danger")), "success": (T("success_bg"), T("success"))}
    bg, fg = palette.get(variant, palette["default"])
    btn = Button(text=text, size_hint=(1, None), height=height)
    style_button(btn, bg, fg, 13, variant == "accent")
    btn.bind(on_release=lambda *_: callback())
    return btn


class PreviewImage(ButtonBehavior, KivyImage):
    """Clickable image thumbnail; full-size display is handled by ChatRoot."""
    def __init__(self, source, callback=None, **kwargs):
        self.callback = callback
        kwargs.setdefault("allow_stretch", True)
        kwargs.setdefault("keep_ratio", True)
        super().__init__(source=source, **kwargs)

    def on_release(self):
        if self.callback:
            self.callback()


class MessageBubble(BoxLayout):
    """Responsive chat row with contained metadata and no timestamp overlap."""
    LONG_PRESS = 0.48

    def __init__(self, role, text, ts="", msg_id=0, starred=False,
                 interrupted=False, image_path="", on_action=None,
                 on_long=None, on_image=None, **kwargs):
        super().__init__(orientation="horizontal", size_hint=(1, None),
                         padding=(dp(9), dp(4)), spacing=dp(7), **kwargs)
        self.role = role
        self.text = text or ""
        self.msg_id = int(msg_id or 0)
        self.starred = bool(starred)
        self.interrupted = bool(interrupted)
        self.image_path = str(image_path or "")
        self.on_action_cb = on_action
        self.on_long_cb = on_long
        self.on_image_cb = on_image
        self._press_event = None
        self._long_fired = False
        self._touch_origin = None
        self._touch_uid = None
        self._touch_moved = False
        self.ts = ts or DT.now().strftime("%H:%M")
        self._build()

    def _build(self):
        is_me = self.role == "me"
        show_avatars = STATE["show_avatars"]

        # Flexible space aligns assistant messages left and user messages right.
        if is_me:
            self.add_widget(Widget(size_hint_x=1))
        elif show_avatars:
            self.add_widget(Avatar("AI", T("avatar_ai"), size_px=dp(31)))
        else:
            self.add_widget(Widget(size_hint=(None, None), size=(dp(3), dp(1))))

        self.bubble = BoxLayout(orientation="vertical", size_hint=(None, None),
                                padding=(dp(13), dp(9)), spacing=dp(5))
        self.bubble.bind(minimum_height=self.bubble.setter("height"))
        bg = T("bubble_me") if is_me else T("bubble_ai")
        with self.bubble.canvas.before:
            Color(*T("shadow"))
            self._shadow_rect = RoundedRectangle(pos=self.bubble.pos,
                size=self.bubble.size, radius=[dp(22)])
            rim = T("accent") if is_me else T("panel3")
            Color(rim[0], rim[1], rim[2], 0.17 if is_me else 0.58)
            self._bubble_rim = RoundedRectangle(pos=self.bubble.pos,
                size=self.bubble.size,
                radius=[dp(22), dp(22), dp(7) if is_me else dp(22), dp(22)])
            Color(*bg)
            self._bubble_rect = RoundedRectangle(pos=(self.bubble.x + dp(0.8), self.bubble.y + dp(0.8)),
                size=(max(0, self.bubble.width - dp(1.6)), max(0, self.bubble.height - dp(1.6))),
                radius=[dp(21), dp(21), dp(6) if is_me else dp(21), dp(21)])
        self.bubble.bind(pos=self._sync_bubble, size=self._sync_bubble)

        fg = (1, 1, 1, 1) if is_me else T("text")
        formatted, self._markdown_links = render_markdown(self.text, F("body"))
        self.body = Label(text=formatted, color=fg,
                          font_name=font_path(), font_size=F("body"),
                          bold=STATE["font_weight"] == "bold",
                          size_hint=(1, None), halign="left", valign="top",
                          markup=True, shorten=False)
        self.body.bind(width=self._body_width, texture_size=self._body_texture)
        self.body.bind(on_ref_press=self._open_markdown_link)
        self.bubble.add_widget(self.body)

        if self.image_path and os.path.isfile(self.image_path):
            self.image_preview = PreviewImage(
                source=self.image_path,
                callback=lambda path=self.image_path: self.on_image_cb(path) if self.on_image_cb else None,
                size_hint=(1, None), height=dp(210))
            self.bubble.add_widget(self.image_preview)
        else:
            self.image_preview = None

        if self.interrupted:
            self.bubble.add_widget(make_label("Ответ прерван", 9, "danger",
                size_hint=(1, None), height=dp(14)))

        # Metadata is part of the bubble, so it cannot overlap the next row.
        show_star = self.starred
        if STATE["show_time"] or show_star:
            footer = BoxLayout(orientation="horizontal", size_hint=(1, None),
                               height=dp(14), spacing=dp(3))
            if show_star:
                star = Label(text="★ В избранном", color=T("star"),
                             font_size=sp(8), size_hint=(None, 1),
                             width=dp(72), halign="left", valign="middle")
                star.bind(size=lambda *_args, w=star: setattr(w, "text_size", w.size))
                footer.add_widget(star)
            footer.add_widget(Widget(size_hint_x=1))
            if STATE["show_time"]:
                time_label = Label(text=self.ts, color=T("text_faint"),
                                   font_size=F("ts"), size_hint=(None, 1),
                                   width=dp(42), halign="right", valign="middle")
                time_label.bind(size=lambda *_args, w=time_label: setattr(w, "text_size", w.size))
                footer.add_widget(time_label)
            self.bubble.add_widget(footer)

        self.add_widget(self.bubble)

        if is_me and show_avatars:
            self.add_widget(Avatar("Я", T("avatar_me"), size_px=dp(31)))
        elif is_me:
            self.add_widget(Widget(size_hint=(None, None), size=(dp(3), dp(1))))
        else:
            self.add_widget(Widget(size_hint_x=1))

        self.bind(width=self._layout_width)
        self.bubble.bind(height=self._update_height)
        Clock.schedule_once(self._layout_width, 0)
        Clock.schedule_once(lambda *_: self._update_height(), 0)

    def _sync_bubble(self, *_):
        self._bubble_rim.pos = self.bubble.pos
        self._bubble_rim.size = self.bubble.size
        self._bubble_rect.pos = (self.bubble.x + dp(0.8), self.bubble.y + dp(0.8))
        self._bubble_rect.size = (max(0, self.bubble.width - dp(1.6)), max(0, self.bubble.height - dp(1.6)))
        self._shadow_rect.pos = (self.bubble.x + dp(1), self.bubble.y - dp(2))
        self._shadow_rect.size = self.bubble.size

    def _layout_width(self, *_):
        if not hasattr(self, "bubble") or self.width <= dp(30):
            return
        # Keep comfortable margins on phones and prevent overly wide text bubbles on tablets.
        max_width = max(dp(130), self.width - dp(70))
        if Window.width > Window.height and Window.width > dp(900):
            max_width = min(max_width, dp(820))
        self.bubble.width = min(self.width * 0.84, max_width)
        if self.image_preview is not None:
            self.image_preview.height = min(dp(230), max(dp(150), self.bubble.width - dp(24)))
        self._body_width(self.body, self.body.width)
        Clock.schedule_once(lambda *_: self._update_height(), 0)

    def _body_width(self, widget, width):
        widget.text_size = (max(dp(40), width), None)

    def _body_texture(self, widget, texture_size):
        widget.height = max(dp(22), texture_size[1] + dp(3))
        Clock.schedule_once(lambda *_: self._update_height(), 0)

    def _update_height(self, *_):
        if hasattr(self, "bubble"):
            self.height = self.bubble.height + dp(8)

    def set_text(self, text, force_update=True):
        self.text = text or ""
        formatted, self._markdown_links = render_markdown(self.text, F("body"))
        self.body.font_name = font_path()
        self.body.font_size = F("body")
        self.body.bold = STATE.get("font_weight") == "bold"
        self.body.text = formatted
        # During streaming Kivy already coalesces Label texture updates on the next frame.
        # Avoid forcing a second texture render for every tiny network chunk.
        if force_update:
            self.body.texture_update()
            self.body.height = max(dp(22), self.body.texture_size[1] + dp(3))
        Clock.schedule_once(lambda *_: self._update_height(), 0)

    def _open_markdown_link(self, _label, ref):
        url = self._markdown_links.get(str(ref), "")
        if url:
            try:
                webbrowser.open(url)
            except Exception:
                pass

    def append(self, piece):
        """Append escaped plain text efficiently; apply rich Markdown once at completion."""
        if not piece:
            return
        self.text += str(piece)
        self.body.text = _kivy_escape(self.text)
        self.body.font_name = font_path()
        self.body.font_size = F("body")
        self.body.bold = STATE.get("font_weight") == "bold"
        Clock.schedule_once(lambda *_: self._update_height(), 0)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.on_long_cb:
            self._long_fired = False
            self._touch_moved = False
            self._touch_origin = (touch.x, touch.y)
            self._touch_uid = touch.uid
            # A press on the image is reserved for opening its full-size preview.
            on_image = bool(self.image_preview and self.image_preview.collide_point(*touch.pos))
            self._press_event = None if on_image else Clock.schedule_once(self._fire_long, self.LONG_PRESS)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._touch_uid == touch.uid and self._touch_origin:
            dx = touch.x - self._touch_origin[0]
            dy = touch.y - self._touch_origin[1]
            if dx * dx + dy * dy > dp(12) ** 2:
                self._touch_moved = True
                if self._press_event:
                    self._press_event.cancel()
                    self._press_event = None
        return super().on_touch_move(touch)

    def _fire_long(self, *_):
        self._press_event = None
        if not self._touch_moved:
            self._long_fired = True
            if self.on_long_cb:
                self.on_long_cb(self)

    def on_touch_up(self, touch):
        mine = self._touch_uid == touch.uid
        if mine and self._press_event:
            self._press_event.cancel()
            self._press_event = None
        inside = mine and self.collide_point(*touch.pos)
        moved = self._touch_moved
        on_image = bool(self.image_preview and self.image_preview.collide_point(*touch.pos))
        result = super().on_touch_up(touch)
        if inside and on_image:
            self._touch_uid = None
            self._touch_origin = None
            return result
        if inside and not moved and not self._long_fired and self.on_action_cb:
            self.on_action_cb(self)
            self._touch_uid = None
            self._touch_origin = None
            return True
        if mine:
            self._touch_uid = None
            self._touch_origin = None
        return result


# ---------------------------------------------------------------------------
# Main app UI
# ---------------------------------------------------------------------------
class ChatRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.busy = False
        self.cancel_event = None
        self.request_id = None
        self.request_kind = None
        self.stream_bubble = None
        self.typing = None
        self._stream_pending = []
        self._stream_flush_scheduled = False
        self._stream_queue_lock = threading.Lock()
        self._at_bottom = True
        self._chips_requested = True
        self._keyboard_visible = False
        self._keyboard_listener = None
        self._is_landscape = Window.width > Window.height
        self._welcome_panel = None
        self._build_ui()
        Clock.schedule_once(self._sync_background, 0)
        self.keyboard_spacer = Widget(size_hint=(1, None), height=0)
        self.add_widget(self.keyboard_spacer)
        Window.bind(size=self._adapt_orientation)
        Clock.schedule_once(lambda *_: self._install_android_keyboard_listener(), 0.7)
        Clock.schedule_once(self._safe_initial_load, 0.12)

    def _safe_initial_load(self, *_args):
        """Keep the UI alive if history/empty-state construction encounters a runtime error."""
        try:
            self.load_chat()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            detail = f"{type(exc).__name__}: {exc}"[:150]
            print("[Startup] Initial chat load failed:", detail)
            try:
                self.messages_box.clear_widgets()
                self.messages_box.add_widget(make_label(
                    "Не удалось загрузить чат\n" + detail + "\n\nПопробуй нажать «Новый чат».",
                    12, "danger", size_hint=(1, None), height=dp(100), valign="middle"))
                self.toast("Ошибка загрузки истории: " + detail[:80])
            except Exception:
                pass

    def dispose(self):
        """Detach listeners and background animation before root is destroyed or rebuilt."""
        event = getattr(self, "_spark_event", None)
        if event is not None:
            try:
                event.cancel()
            except Exception:
                pass
            self._spark_event = None
        try:
            Window.unbind(size=self._adapt_orientation)
        except Exception:
            pass
        listener = getattr(self, "_keyboard_listener", None)
        if listener is not None:
            try:
                from jnius import autoclass
                Activity = autoclass("org.renpy.android.PythonActivity")
                decor = Activity.mActivity.getWindow().getDecorView()
                decor.getViewTreeObserver().removeOnGlobalLayoutListener(listener)
            except Exception:
                pass
            self._keyboard_listener = None

    def _build_ui(self):
        # A single base surface avoids hard horizontal colour bands on tall phones.
        with self.canvas.before:
            # A subtle 30-band gradient replaces the flat purple field on tall screens.
            self._bg_bands = []
            bot = T("bg_bot")
            top = T("bg_top")
            for band_index in range(30):
                ratio = band_index / 29.0
                rgba = tuple(bot[channel]*(1.0-ratio)+top[channel]*ratio for channel in range(3)) + (1.0,)
                band_color = Color(*rgba)
                band_rect = Rectangle(pos=self.pos, size=self.size)
                self._bg_bands.append((ratio, band_color, band_rect))
            glow = T("accent")
            Color(glow[0], glow[1], glow[2], 0.062 if STATE.get("theme") != "daylight" else 0.02)
            self.bg_glow = Ellipse(pos=(self.x-dp(90), self.top-dp(300)), size=(self.width+dp(180), dp(470)))
            cool = T("avatar_ai")
            Color(cool[0], cool[1], cool[2], 0.030 if STATE.get("theme") != "daylight" else 0.012)
            self.bg_glow_2 = Ellipse(pos=(self.right-dp(220), self.y+dp(45)), size=(self.width*0.82, dp(310)))
            # Fine, low-alpha particle trails: decorative without overpowering chat content.
            self._spark_particles = []
            particle_count = 34 if not STATE.get("performance_mode", True) else 28
            for _spark_index in range(particle_count):
                sx, sy = random.random(), random.random()
                brightness = random.uniform(0.10, 0.34)
                spark_color = Color(*T("accent")[:3], brightness)
                spark_len = dp(random.uniform(3.0, 8.0))
                spark_line = Line(points=[0, 0, 0, 0], width=dp(random.choice([0.55, 0.75, 0.9])))
                spark_dot = Ellipse(pos=(0, 0), size=(dp(1.2), dp(1.2)))
                self._spark_particles.append({
                    "x": sx, "y": sy, "speed": random.uniform(0.038, 0.105),
                    "tilt": dp(random.uniform(-1.7, 1.7)), "length": spark_len,
                    "alpha": brightness, "color": spark_color, "line": spark_line, "dot": spark_dot,
                })
        self.bind(pos=self._sync_background, size=self._sync_background)
        self._spark_event = None
        if STATE.get("sparkle_background", True):
            self._spark_event = Clock.schedule_interval(self._animate_sparks, 1.0 / 30.0)

        header = BoxLayout(size_hint=(1, None), height=dp(70), padding=(dp(12), dp(8)), spacing=dp(7))
        self.header_widget = header
        with header.canvas.before:
            Color(*T("panel")); self.header_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda *_: setattr(self.header_rect, "pos", header.pos),
                    size=lambda *_: setattr(self.header_rect, "size", header.size))
        with header.canvas.after:
            accent = T("accent")
            Color(accent[0], accent[1], accent[2], 0.42)
            self.header_accent_line = Rectangle(pos=(header.x, header.y), size=(header.width, dp(0.8)))
        header.bind(pos=lambda *_: setattr(self.header_accent_line, "pos", (header.x, header.y)),
                    size=lambda *_: setattr(self.header_accent_line, "size", (header.width, dp(0.8))))
        header.add_widget(IconButton("plus", self.new_chat, dp(38), bg_key="panel2"))
        header.add_widget(IconButton("search", self.open_search, dp(38), bg_key="panel2"))
        center = BoxLayout(orientation="horizontal", spacing=dp(7), size_hint=(1, 1))
        center.add_widget(BrandMark(dp(33)))
        title_stack = BoxLayout(orientation="vertical", spacing=0)
        self.title_lbl = Label(text="AI Чат", color=T("text"), bold=True, font_size=F("title"),
                               halign="left", valign="bottom", shorten=True)
        self.title_lbl.bind(size=lambda *_: setattr(self.title_lbl, "text_size", self.title_lbl.size))
        self.status_lbl = Label(text="ГОТОВ К РАБОТЕ", color=T("online"), font_size=sp(8),
                                halign="left", valign="top", shorten=True)
        self.status_lbl.bind(size=lambda *_: setattr(self.status_lbl, "text_size", self.status_lbl.size))
        title_stack.add_widget(self.title_lbl)
        title_stack.add_widget(self.status_lbl)
        center.add_widget(title_stack)
        header.add_widget(center)
        header.add_widget(IconButton("gear", self.open_settings, dp(38), bg_key="panel2"))
        header.add_widget(IconButton("menu", self.open_menu, dp(38), bg_key="panel2"))
        self.add_widget(header)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), scroll_type=["bars", "content"])
        self.scroll.bind(scroll_y=self._scroll_changed)
        self.messages_box = BoxLayout(orientation="vertical", size_hint_y=None,
                                      spacing=msg_spacing(), padding=(dp(2), dp(12)))
        self.messages_box.bind(minimum_height=self.messages_box.setter("height"))
        self.scroll.add_widget(self.messages_box)
        self.add_widget(self.scroll)

        self.bottom_bar = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(128), spacing=dp(0))
        self.chips_scroll = ScrollView(size_hint=(1, None), height=dp(48), do_scroll_x=True, do_scroll_y=False, bar_width=0, scroll_type=["content"])
        self.chips = BoxLayout(size_hint=(None, None), height=dp(46), spacing=dp(8), padding=(dp(10), dp(4)))
        self.chips.bind(minimum_width=self.chips.setter("width"))
        self.chips_scroll.add_widget(self.chips)
        self.bottom_bar.add_widget(self.chips_scroll)

        composer = BoxLayout(size_hint=(1, None), height=dp(76), padding=(dp(13), dp(10)), spacing=dp(8))
        with composer.canvas.before:
            Color(0, 0, 0, 0.20 if STATE.get("theme") != "daylight" else 0.04)
            self.composer_shadow = RoundedRectangle(pos=(composer.x+dp(6), composer.y+dp(2)),
                size=(max(0,composer.width-dp(12)), max(0,composer.height-dp(8))), radius=[dp(27)])
            ac = T("accent")
            self.composer_frame_color = Color(ac[0], ac[1], ac[2], 0.16)
            self.composer_frame = Line(rounded_rectangle=(composer.x+dp(6), composer.y+dp(4),
                max(0,composer.width-dp(12)), max(0,composer.height-dp(8)), dp(26)), width=dp(0.8))
            Color(*T("panel"))
            self.composer_rect = RoundedRectangle(pos=(composer.x+dp(7), composer.y+dp(5)),
                size=(max(0,composer.width-dp(14)), max(0,composer.height-dp(10))), radius=[dp(25)])
        composer.bind(pos=self._sync_composer_skin, size=self._sync_composer_skin)
        # Text-first composer: no broken camera/photo controls. The smile icon is drawn with canvas primitives.
        emoji_button = IconButton("smile", self.open_emoji_picker, dp(39), bg_key="panel2")
        composer.add_widget(emoji_button)
        if ANDROID:
            composer.add_widget(IconButton("mic", self.voice_click, dp(40)))
        self.input_wrap = BoxLayout(padding=(dp(12), dp(8)))
        with self.input_wrap.canvas.before:
            Color(0, 0, 0, 0.10)
            self.input_shadow = RoundedRectangle(pos=self.input_wrap.pos, size=self.input_wrap.size, radius=[dp(23)])
            ac = T("accent")
            self.input_border_color = Color(ac[0], ac[1], ac[2], 0.16)
            self.input_border = Line(rounded_rectangle=(self.input_wrap.x, self.input_wrap.y,
                self.input_wrap.width, self.input_wrap.height, dp(22)), width=dp(0.75))
            Color(*T("panel2"))
            self.input_rect = RoundedRectangle(pos=(self.input_wrap.x+dp(1), self.input_wrap.y+dp(1)),
                size=(max(0,self.input_wrap.width-dp(2)), max(0,self.input_wrap.height-dp(2))), radius=[dp(21)])
        self.input_wrap.bind(pos=self._sync_input_skin, size=self._sync_input_skin)
        self.input = TextInput(hint_text="Напиши сообщение…", multiline=False, font_size=F("body"),
                               foreground_color=T("text"), cursor_color=T("accent"),
                               hint_text_color=T("text_dim"), background_normal="",
                               background_active="", background_color=(0, 0, 0, 0),
                               padding=(dp(3), dp(7)), write_tab=False,
                               input_type="text", keyboard_suggestions=True)
        self.input.bind(on_text_validate=self.send, focus=self._input_focus_changed)
        self.input_wrap.add_widget(self.input)
        composer.add_widget(self.input_wrap)
        self.action_slot = BoxLayout(size_hint=(None, 1), width=dp(47))
        self.send_button = IconButton("send", self.send, dp(45), bg_key="accent")
        self.stop_button = IconButton("stop", self.stop_generation, dp(45), bg_key="danger")
        self.action_slot.add_widget(self.send_button)
        composer.add_widget(self.action_slot)
        self.composer_widget = composer
        self.bottom_bar.add_widget(composer)
        self.add_widget(self.bottom_bar)
        self._build_chips()
        self._adapt_orientation()

    def _sync_composer_skin(self, *_):
        try:
            composer = self.composer_widget
            pos = (composer.x+dp(6), composer.y+dp(4))
            size = (max(0,composer.width-dp(12)), max(0,composer.height-dp(8)))
            self.composer_shadow.pos = (composer.x+dp(6), composer.y+dp(2))
            self.composer_shadow.size = size
            self.composer_frame.rounded_rectangle = (pos[0], pos[1], size[0], size[1], dp(26))
            self.composer_rect.pos = (composer.x+dp(7), composer.y+dp(5))
            self.composer_rect.size = (max(0,composer.width-dp(14)), max(0,composer.height-dp(10)))
        except Exception:
            pass

    def _sync_input_skin(self, *_):
        try:
            wrap = self.input_wrap
            self.input_shadow.pos = wrap.pos
            self.input_shadow.size = wrap.size
            self.input_border.rounded_rectangle = (wrap.x, wrap.y, wrap.width, wrap.height, dp(22))
            self.input_rect.pos = (wrap.x+dp(1), wrap.y+dp(1))
            self.input_rect.size = (max(0,wrap.width-dp(2)), max(0,wrap.height-dp(2)))
        except Exception:
            pass

    def _input_focus_changed(self, _widget, focused):
        try:
            ac = T("accent")
            current = self.input_border_color.rgba
            self.input_border_color.rgba = (ac[0], ac[1], ac[2], 0.62 if focused else 0.16)
            self.composer_frame_color.rgba = (ac[0], ac[1], ac[2], 0.28 if focused else 0.16)
        except Exception:
            pass

    def _adapt_orientation(self, *_):
        """Tighten vertical chrome in landscape; all Kivy children remain resize-aware."""
        landscape = Window.width > Window.height
        self._is_landscape = landscape
        try:
            self.header_widget.height = dp(58 if landscape else 66)
            self.chips_scroll.height = dp(38 if landscape else 48) if getattr(self, "_chips_requested", True) and not getattr(self, "_keyboard_visible", False) and STATE.get("show_suggestions", True) else 0
            self.chips.height = dp(38 if landscape else 46)
            self.chips.padding = (dp(10), dp(0) if landscape else dp(4))
            self.composer_widget.height = dp(66 if landscape else 76)
            self.composer_widget.padding = (dp(9), dp(7) if landscape else dp(10))
            chips_h = dp(38 if landscape else 48) if self.chips_scroll.height > 0 else 0
            self.bottom_bar.height = self.composer_widget.height + chips_h
        except Exception:
            pass

    def open_emoji_picker(self, *_):
        """Show a font-safe picker; ASCII faces/symbols avoid missing-glyph boxes on Android."""
        # Deliberately use ASCII characters only. Some bundled Kivy fonts do not contain
        # emoji glyphs, which Android/SDL then displays as crossed-out square placeholders.
        symbols = [
            # Emoticons
            ":)", ":-)", ":D", ":-D", ";)", ";-)", ":P", ":-P",
            ":(", ":-(", ":'(", ">:(", ":O", ":-O", ":|", ":-|",
            "xD", "XD", "^_^", "^-^", "o_O", "O_O", "T_T", "-_-",
            "<3", "</3", "<33", "(Y)", "(N)", r"\o/", "^^", "._.",
            # Punctuation and common symbols
            "!", "?", "...", "--", "->", "<-", "^", "v",
            "+", "-", "*", "/", "=", "#", "@", "$",
            "%", "&", "(", ")", "[", "]", "{", "}",
            "<", ">", "|", "\\", "~", "`", "'", '"',
            ":", ";", ",", ".", "!?!", "***", "###", "???",
            # Handy text-form math/format symbols
            "<=", ">=", "!=", "==", "+=", "%=", "x^2", "a/b",
            "1/2", "1/3", "1/4", "10^2", "( )", "[ ]", "{ }", "< >",
        ]
        popup = RoundedPopup(size_hint=(0.94, None),
                             height=min(dp(430), max(dp(300), Window.height - dp(30))))
        popup.container.add_widget(make_label(
            "Смайлики и символы", 18, bold=True,
            size_hint=(1, None), height=dp(38)))
        popup.container.add_widget(make_label(
            "Нажми на смайлик или символ — он вставится в поле сообщения.",
            10, "text_dim", size_hint=(1, None), height=dp(30)))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        grid = GridLayout(cols=4, spacing=dp(6), padding=(dp(2), dp(5)),
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for symbol in symbols:
            button = Button(text=symbol, font_size=sp(16),
                            size_hint=(1, None), height=dp(44),
                            background_normal="", background_down="")
            style_button(button, T("panel3"), T("text"), 16, False, dp(10))
            def insert_symbol(_button, value=symbol):
                try:
                    self.input.focus = True
                    self.input.insert_text(value)
                except Exception:
                    # Fallback for unusual keyboard/cursor states.
                    self.input.text = self.input.text + value
                popup.dismiss()
            button.bind(on_release=insert_symbol)
            grid.add_widget(button)
        scroll.add_widget(grid)
        popup.container.add_widget(scroll)
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss, "default"))
        popup.open()

    def _set_sparkles_enabled(self, enabled):
        """Start or stop the background animation immediately to respect battery preference."""
        event = getattr(self, "_spark_event", None)
        if enabled and event is None:
            self._spark_event = Clock.schedule_interval(self._animate_sparks, 1.0 / 30.0)
        elif not enabled and event is not None:
            try:
                event.cancel()
            except Exception:
                try:
                    Clock.unschedule(self._animate_sparks)
                except Exception:
                    pass
            self._spark_event = None
            for particle in getattr(self, "_spark_particles", []):
                try:
                    rgb = T("accent")
                    particle["color"].rgba = (rgb[0], rgb[1], rgb[2], 0)
                except Exception:
                    pass

    def _animate_sparks(self, dt):
        """Move small accent-colored streaks downward behind the conversation."""
        if not STATE.get("sparkle_background", True):
            return True
        width = max(1.0, float(self.width))
        height = max(1.0, float(self.height))
        accent = T("accent")
        for particle in getattr(self, "_spark_particles", []):
            particle["y"] -= particle["speed"] * max(0.0, min(float(dt), 0.08))
            if particle["y"] < -0.04:
                particle["y"] = random.uniform(1.00, 1.14)
                particle["x"] = random.random()
                particle["alpha"] = random.uniform(0.18, 0.62)
            x = self.x + particle["x"] * width
            y = self.y + particle["y"] * height
            length = particle["length"]
            tilt = particle["tilt"]
            try:
                particle["line"].points = [x, y + length, x + tilt, y]
                particle["dot"].pos = (x - dp(0.7), y - dp(0.7))
                particle["color"].rgba = (accent[0], accent[1], accent[2], particle["alpha"])
            except Exception:
                continue
        return True

    def _sync_background(self, *_):
        """Resize the gradient and atmospheric glows without allocating canvas objects."""
        width = max(0.0, float(self.width))
        height = max(0.0, float(self.height))
        bot, top = T("bg_bot"), T("bg_top")
        bands = getattr(self, "_bg_bands", [])
        count = max(1, len(bands))
        band_height = height/count + dp(0.8)
        for index, (_ratio, color_instruction, rect) in enumerate(bands):
            ratio = (index+0.5)/count
            color_instruction.rgba = tuple(bot[ch]*(1.0-ratio)+top[ch]*ratio for ch in range(3)) + (1.0,)
            rect.pos = (self.x, self.y + index*height/count)
            rect.size = (width, band_height)
        self.bg_glow.pos = (self.x-dp(90), self.top-dp(300))
        self.bg_glow.size = (width+dp(180), dp(470))
        self.bg_glow_2.pos = (self.right-dp(220), self.y+dp(45))
        self.bg_glow_2.size = (width*0.82, dp(310))

    def _build_chips(self):
        self.chips.clear_widgets()
        for text in ("Объясни просто", "Помоги с кодом", "Сократи текст", "Посчитай 15*7", "Нарисуй кота", "Перевод"):
            self.chips.add_widget(ChatChip(text, self.use_chip))

    def _set_chips_visible(self, visible):
        """Remember whether suggestions are allowed; hide them while keyboard is open."""
        self._chips_requested = bool(visible)
        self._refresh_bottom_layout()

    def _refresh_bottom_layout(self):
        visible = self._chips_requested and not self._keyboard_visible and STATE.get("show_suggestions", True)
        landscape = Window.width > Window.height
        chips_h = dp(38 if landscape else 48)
        composer_h = dp(66 if landscape else 76)
        self.chips_scroll.height = chips_h if visible else 0
        self.chips.height = dp(38 if landscape else 46)
        self.chips.padding = (dp(10), dp(0) if landscape else dp(4))
        self.composer_widget.height = composer_h
        self.composer_widget.padding = (dp(9), dp(7) if landscape else dp(10))
        self.bottom_bar.height = composer_h + (chips_h if visible else 0)

    def _keyboard_size_changed(self, pixel_height):
        """Move only the composer above the Android keyboard; don't pan the chat."""
        try:
            height = max(0, int(pixel_height))
            visible = height > 0
            if visible != self._keyboard_visible:
                self._keyboard_visible = visible
                self._refresh_bottom_layout()
            # Android's view frame reports physical pixels, matching Window coordinates.
            Animation.cancel_all(self.keyboard_spacer, "height")
            Animation(height=height, d=0.12, t="out_quad").start(self.keyboard_spacer)
        except Exception:
            self.keyboard_spacer.height = max(0, int(pixel_height))

    def _install_android_keyboard_listener(self):
        """Use Android's visible display frame because SDL2 Window.keyboard_height is 0 on Android."""
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            Activity = autoclass("org.renpy.android.PythonActivity")
            Rect = autoclass("android.graphics.Rect")
            activity = Activity.mActivity
            decor = activity.getWindow().getDecorView()
            root_view = decor.getRootView()
            chat = self

            class _KeyboardListener(PythonJavaClass):
                __javainterfaces__ = ["android/view/ViewTreeObserver$OnGlobalLayoutListener"]
                __javacontext__ = "app"

                @java_method("()V")
                def onGlobalLayout(self):
                    try:
                        frame = Rect()
                        decor.getWindowVisibleDisplayFrame(frame)
                        full_height = int(root_view.getHeight())
                        hidden_height = max(0, full_height - int(frame.bottom))
                        if full_height and hidden_height < int(full_height * 0.15):
                            hidden_height = 0
                        Clock.schedule_once(
                            lambda _dt, h=hidden_height: chat._keyboard_size_changed(h), 0)
                    except Exception:
                        pass

            self._keyboard_listener = _KeyboardListener()
            decor.getViewTreeObserver().addOnGlobalLayoutListener(self._keyboard_listener)
        except Exception:
            # Keep the window stationary if Android's native listener is unavailable.
            # This is preferable to below_target/pan, which shifts the whole chat.
            pass

    def _scroll_changed(self, *_):
        self._at_bottom = self.scroll.scroll_y <= 0.025

    def scroll_to_bottom(self, force=False):
        if not force and not STATE.get("auto_scroll", True):
            return
        try:
            Animation.cancel_all(self.scroll, "scroll_y")
            Animation(scroll_y=0, d=0.18).start(self.scroll)
        except Exception:
            self.scroll.scroll_y = 0

    def load_chat(self):
        self.messages_box.clear_widgets()
        self.messages_box.spacing = msg_spacing()
        self.stream_bubble = None
        self._remove_typing()
        records = db_messages(sid=SESSION_ID)
        self._welcome_panel = None
        if not records:
            self._set_chips_visible(False)
            self.title_lbl.text = "AI Чат"
            self._welcome_panel = WelcomePanel(self.use_chip)
            self.messages_box.add_widget(self._welcome_panel)
        else:
            self._set_chips_visible(False)
            for row in records:
                role = "me" if row["role"] == "user" else "ai"
                content = row["content"]
                interrupted = role == "ai" and content.startswith("[прервано] ")
                if interrupted:
                    content = content[len("[прервано] "):]
                image_path = row.get("image_path", "") or ""
                if not image_path:
                    old_path = re.search(r"Изображение готово и сохранено:\s*\n([^\n]+)", content)
                    if old_path:
                        candidate = old_path.group(1).strip()
                        if os.path.isfile(candidate):
                            image_path = candidate
                            content = "Изображение создано. Нажми на картинку, чтобы открыть её."
                self.add_message(role, content, ts=row["ts"][11:16], msg_id=row["id"],
                                 starred=bool(row.get("starred", 0)), interrupted=interrupted,
                                 image_path=image_path, animate=False)
            self.title_lbl.text = "AI Чат"
        self._update_status()
        Clock.schedule_once(lambda *_: self.scroll_to_bottom(force=True), 0.1)

    def add_message(self, role, text, ts="", msg_id=0, starred=False,
                    interrupted=False, image_path="", animate=True):
        welcome = getattr(self, "_welcome_panel", None)
        if welcome is not None:
            try:
                self.messages_box.remove_widget(welcome)
            except Exception:
                pass
            self._welcome_panel = None
        animate = bool(animate and STATE.get("message_animations", True)
                       and (not STATE.get("performance_mode", True) or role == "ai"))
        bubble = MessageBubble(role, text, ts=ts, msg_id=msg_id, starred=starred,
                               interrupted=interrupted, image_path=image_path,
                               on_action=self.open_message_actions,
                               on_long=self.open_quick_actions,
                               on_image=self.show_image)
        if animate:
            bubble.opacity = 0
        self.messages_box.add_widget(bubble)
        if animate:
            Animation(opacity=1, d=0.20).start(bubble)
        Clock.schedule_once(lambda *_: self.scroll_to_bottom(), 0.06)
        return bubble

    def _update_status(self):
        if not STATE.get("show_model_status", True):
            self.status_lbl.text = ""
            return
        provider = STATE.get("last_provider", "-")
        model = STATE.get("last_model", "-")
        if self.busy:
            return
        if provider != "-":
            info = provider + " · " + (model[:16] + ("…" if len(model) > 16 else ""))
        else:
            info = "готов к работе"
        self.status_lbl.text = info
        self.status_lbl.color = T("online")

    def _set_busy(self, value, status=None):
        self.busy = value
        self.action_slot.clear_widgets()
        self.action_slot.add_widget(self.stop_button if value else self.send_button)
        if status:
            self.status_lbl.text = status
            self.status_lbl.color = T("accent") if value else T("online")
        elif not value:
            self._update_status()

    def _show_typing(self):
        if self.typing is not None:
            return
        row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(43),
                        padding=(dp(14), dp(4)), spacing=dp(8))
        with row.canvas.before:
            Color(T("panel")[0], T("panel")[1], T("panel")[2], 0.72)
            row._typing_bg = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(18)])
            a = T("accent")
            Color(a[0], a[1], a[2], 0.24)
            row._typing_rim = Line(rounded_rectangle=(row.x, row.y, row.width, row.height, dp(18)), width=dp(0.7))
        row.bind(pos=lambda *_: self._sync_typing_row(row), size=lambda *_: self._sync_typing_row(row))
        row.add_widget(BrandMark(dp(25)))
        row.add_widget(make_label("Готовлю ответ", 10.5, "text_dim", False,
                                  size_hint=(None, 1), width=dp(100)))
        dots = TypingDots()
        row._typing_dots = dots
        row.add_widget(dots)
        row.add_widget(Widget(size_hint_x=1))
        self.typing = row
        self.messages_box.add_widget(row)
        self.scroll_to_bottom()

    @staticmethod
    def _sync_typing_row(row):
        try:
            row._typing_bg.pos = row.pos
            row._typing_bg.size = row.size
            row._typing_rim.rounded_rectangle = (row.x, row.y, row.width, row.height, dp(18))
        except Exception:
            pass

    def _remove_typing(self):
        if self.typing is not None:
            try:
                self.typing._typing_dots.stop()
            except Exception:
                pass
            try:
                self.messages_box.remove_widget(self.typing)
            except Exception:
                pass
            self.typing = None

    def _queue_stream_piece(self, request_id, piece):
        """Batch tiny network chunks so slow Android devices redraw at a steady rate."""
        with self._stream_queue_lock:
            self._stream_pending.append((request_id, piece))
            if self._stream_flush_scheduled:
                return
            self._stream_flush_scheduled = True
        interval = 0.038 if STATE.get("performance_mode", True) else 0.026
        Clock.schedule_once(self._flush_stream_pieces, interval)

    def _flush_stream_pieces(self, _dt=0):
        with self._stream_queue_lock:
            pending = self._stream_pending
            self._stream_pending = []
            self._stream_flush_scheduled = False
        if not pending:
            return
        merged = {}
        for request_id, piece in pending:
            merged[request_id] = merged.get(request_id, "") + piece
        for request_id, piece in merged.items():
            self._on_stream_piece(request_id, piece)

    def _on_stream_piece(self, request_id, piece):
        if request_id != self.request_id or not self.busy:
            return
        self._remove_typing()
        if self.stream_bubble is None:
            self.stream_bubble = self.add_message("ai", "", animate=True)
        self.stream_bubble.append(piece)
        # No repeated cancel/restart of a ScrollView animation while tokens arrive.
        # If the user has scrolled up to read earlier content, keep their position.
        if STATE.get("auto_scroll", True) and getattr(self, "_at_bottom", True):
            Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 0), 0)

    def send(self, *_):
        if self.busy:
            self.toast("Дождись завершения ответа или нажми Стоп")
            return
        text = self.input.text.strip()
        if not text:
            return
        self.input.text = ""
        low = text.lower().strip()
        sid = SESSION_ID

        if is_identity_question(text):
            try:
                user_id = db_add("user", text, sid)
                self.add_message("me", text, msg_id=user_id)
                answer_id = db_add("assistant", IDENTITY_REPLY, sid)
                self.add_message("ai", IDENTITY_REPLY, msg_id=answer_id)
                self._set_chips_visible(False)
                self.title_lbl.text = "AI Чат"
            except Exception as exc:
                self.toast("Не удалось сохранить ответ: " + str(exc)[:70])
            return

        # Local commands are saved to history like regular turns.
        note_match = re.match(r"^заметка\s*:?\s*(.+)$", text, re.I | re.S)
        if note_match:
            note_text = note_match.group(1).strip()
            if note_text:
                db_note_add(note_text)
                user_id = db_add("user", text, sid)
                self.add_message("me", text, msg_id=user_id)
                answer = "Заметка сохранена. Открыть её можно в меню «Заметки»."
                aid = db_add("assistant", answer, sid)
                self.add_message("ai", answer, msg_id=aid)
                self._set_chips_visible(False)
                self.title_lbl.text = "AI Чат"
            return

        calc_match = re.match(r"^(?:посчитай|вычисли|калькулятор|сколько будет)\s+(.+)$", text, re.I | re.S)
        quadratic_match = re.match(r"^квадратное\s+.+$", low)
        if calc_match or quadratic_match:
            expr = calc_match.group(1).strip() if calc_match else text
            result, error = calc_safe(expr)
            user_id = db_add("user", text, sid)
            self.add_message("me", text, msg_id=user_id)
            answer = error if error else (f"{expr} = {result}" if calc_match else str(result))
            aid = db_add("assistant", answer, sid)
            self.add_message("ai", answer, msg_id=aid)
            self._set_chips_visible(False)
            self.title_lbl.text = "AI Чат"
            return

        image_match = re.match(r"^(?:нарисуй|картинка|сгенерируй(?: изображение)?)\s+(.+)$", text, re.I | re.S)
        if image_match:
            prompt = image_match.group(1).strip()
            # Remove common Russian conversational filler so "нарисуй мне котика"
            # is sent to the image model as "котика", not literally "мне котика".
            prompt = re.sub(r"^(?:(?:мне|пожалуйста|картинку|изображение)\s+)+", "", prompt, flags=re.I).strip()
            if not prompt:
                prompt = "красивую иллюстрацию"
            user_id = db_add("user", text, sid)
            self.add_message("me", text, msg_id=user_id)
            self._set_chips_visible(False)
            self._set_busy(True, "создаю изображение…")
            self.request_id = uuid.uuid4().hex
            rid = self.request_id
            self.request_kind = "image"
            self._show_typing()
            self.cancel_event = threading.Event()
            image_cancel = self.cancel_event
            def done(path, error):
                if rid != self.request_id:
                    return
                self._remove_typing()
                if image_cancel.is_set():
                    answer = "Создание изображения отменено."
                elif path:
                    answer = "Изображение создано. Нажми на картинку, чтобы открыть её в полном размере.\nСохранено в локальную папку images."
                else:
                    answer = "Не удалось создать изображение.\n" + str(error or "Неизвестная ошибка")
                aid = db_add("assistant", answer, sid, image_path=path if path and not image_cancel.is_set() else "")
                self.add_message("ai", answer, msg_id=aid,
                                 image_path=path if path and not image_cancel.is_set() else "")
                self.cancel_event = None
                self.request_kind = None
                self._set_busy(False)
                self.title_lbl.text = "AI Чат"
            generate_image(prompt, done, image_cancel)
            return

        try:
            user_id = db_add("user", text, sid)
        except Exception as exc:
            self.add_message("ai", "Ошибка сохранения истории: " + str(exc)[:120])
            return
        self.add_message("me", text, msg_id=user_id)
        self._set_chips_visible(False)
        self.title_lbl.text = "AI Чат"
        self.request_id = uuid.uuid4().hex
        rid = self.request_id
        self.request_kind = "chat"
        self.cancel_event = threading.Event()
        self.stream_bubble = None
        self._set_busy(True, "думаю…")
        self._show_typing()
        threading.Thread(target=self._ai_worker, args=(rid, sid, self.cancel_event), daemon=True).start()

    def _ai_worker(self, rid, sid, cancel_event):
        reply = None
        error = None
        chunks_seen = []
        try:
            extra_prompt = (STATE.get("custom_prompt") or "").strip()
            active_prompt = SAFE_PROMPT
            if extra_prompt:
                active_prompt += "\n\nДополнительные пожелания пользователя:\n" + extra_prompt
            messages = [{"role": "system", "content": active_prompt[:9000]}]
            for row in db_recent(14, sid):
                role = row["role"]
                if role in ("user", "assistant", "system"):
                    messages.append({"role": role, "content": row["content"]})
            def on_chunk(piece):
                chunks_seen.append(piece)
                self._queue_stream_piece(rid, piece)
            if not cancel_event.is_set():
                reply, error = ask_ai(messages, on_chunk=on_chunk, cancel_event=cancel_event)
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc)[:140]}"
        interrupted = cancel_event.is_set()
        stored_text = None
        if reply:
            stored_text = ("[прервано] " if interrupted else "") + reply
        elif interrupted and chunks_seen:
            stored_text = "[прервано] " + "".join(chunks_seen)
            reply = "".join(chunks_seen)
        reply_id = 0
        if stored_text:
            try:
                reply_id = db_add("assistant", stored_text, sid)
            except Exception as exc:
                error = "Не удалось сохранить ответ: " + str(exc)[:100]
        Clock.schedule_once(lambda _dt: self._finish_ai(rid, reply, error, interrupted, reply_id), 0)

    def _finish_ai(self, rid, reply, error, interrupted, reply_id):
        if rid != self.request_id:
            return
        self._flush_stream_pieces(0)
        self._remove_typing()
        bubble = self.stream_bubble
        self.stream_bubble = None
        if interrupted:
            final_text = (reply or (bubble.text if bubble else "")).strip()
            if bubble is not None:
                bubble.set_text(final_text or "Генерация остановлена.")
                bubble.msg_id = reply_id
                self._replace_bubble(bubble, final_text or "Генерация остановлена.", reply_id, True)
            elif final_text:
                self.add_message("ai", final_text, msg_id=reply_id, interrupted=True)
            else:
                self.add_message("ai", "Генерация остановлена.")
        elif reply:
            if bubble is not None:
                bubble.set_text(reply)
                bubble.msg_id = reply_id
            else:
                self.add_message("ai", reply, msg_id=reply_id)
            if STATE["voice_out"]:
                threading.Thread(target=voice_output, args=(reply,), daemon=True).start()
        else:
            concise = error or "Неизвестная ошибка"
            if len(concise) > 360:
                concise = "\n".join(concise.splitlines()[-3:])[:360]
            message = "Не удалось получить ответ.\n\n" + concise + "\n\nПроверь настройки API и интернет."
            if bubble is not None:
                try:
                    self.messages_box.remove_widget(bubble)
                except Exception:
                    pass
            self.add_message("ai", message)
        self._set_busy(False)
        self.cancel_event = None
        self.request_kind = None
        self.scroll_to_bottom()

    def _replace_bubble(self, old, text, msg_id, interrupted):
        try:
            index = self.messages_box.children.index(old)
            old_ts = old.ts
            old_starred = old.starred
            self.messages_box.remove_widget(old)
            new = MessageBubble("ai", text, ts=old_ts, msg_id=msg_id, starred=old_starred,
                                interrupted=interrupted, image_path=getattr(old, "image_path", ""),
                                on_action=self.open_message_actions,
                                on_long=self.open_quick_actions, on_image=self.show_image)
            self.messages_box.add_widget(new, index=min(index, len(self.messages_box.children)))
        except Exception:
            pass

    def stop_generation(self):
        if not self.busy:
            return
        if self.cancel_event:
            self.cancel_event.set()
        if self.request_kind == "image":
            # Image downloads can block inside urlopen. Invalidate their callback
            # now so the UI unlocks immediately; the worker will discard the file.
            sid = SESSION_ID
            self.request_id = uuid.uuid4().hex
            self._remove_typing()
            self.cancel_event = None
            self.request_kind = None
            try:
                text = "Создание изображения отменено."
                msg_id = db_add("assistant", text, sid)
                self.add_message("ai", text, msg_id=msg_id)
            except Exception:
                pass
            self._set_busy(False)
            self.toast("Создание изображения отменено")
            return
        self.status_lbl.text = "останавливаю…"
        self.status_lbl.color = T("danger")

    def use_chip(self, text):
        prompts = {
            "Объясни просто": "Объясни простыми словами: ",
            "Помоги с кодом": "Помоги написать и проверить код на Python: ",
            "Краткое резюме": "Сделай краткое резюме: ",
            "Сократи текст": "Сократи текст, сохранив главные мысли: ",
            "Интересный факт": "Расскажи интересный научный факт и объясни его простыми словами.",
            "Нарисуй кота": "Нарисуй кота",
            "Переведи на английский": "Переведи на английский: ",
            "Перевод": "Переведи текст на нужный язык: ",
            "Создай текст": "Помоги написать хороший текст. Уточни цель, стиль и аудиторию: ",
        }
        self.input.text = text if text.startswith("Посчитай") else prompts.get(text, text)
        # For prompts needing user text, focus the input rather than sending an empty template.
        if self.input.text.endswith(": "):
            self.input.focus = True
            return
        self.send()

    def voice_click(self):
        if not ANDROID:
            self.toast("Голосовой ввод недоступен в этой среде")
            return
        self.status_lbl.text = "слушаю…"
        self.status_lbl.color = T("accent")
        def worker():
            value = voice_input()
            def done(*_):
                self._update_status()
                if value:
                    self.input.text = value
                    self.send()
            Clock.schedule_once(done, 0)
        threading.Thread(target=worker, daemon=True).start()

    def show_image(self, path):
        """Open an image viewer with a gallery-save action."""
        if not path or not os.path.isfile(path):
            self.toast("Файл изображения не найден")
            return
        popup = ModalView(size_hint=(0.98, 0.94), background_color=(0.015, 0.018, 0.030, 0.97),
                          auto_dismiss=True)
        outer = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        top = BoxLayout(size_hint=(1, None), height=dp(38), spacing=dp(8))
        top.add_widget(make_label("Просмотр изображения", 15, bold=True))
        top.add_widget(popup_button("×", popup.dismiss, "default", dp(36)))
        outer.add_widget(top)
        try:
            image_bytes = os.path.getsize(path)
            dimensions = ""
            try:
                from PIL import Image
                with Image.open(path) as image_file:
                    dimensions = f"{image_file.width} × {image_file.height} · "
            except Exception:
                pass
            image_size_label = dimensions + (f"{image_bytes / (1024 * 1024):.2f} МБ"
                               if image_bytes >= 1024 * 1024 else f"{max(1, image_bytes // 1024)} КБ")
        except OSError:
            image_size_label = os.path.basename(path)
        outer.add_widget(make_label(image_size_label, 10, "text_dim",
                                    size_hint=(1, None), height=dp(20)))
        preview = KivyImage(source=path, allow_stretch=True, keep_ratio=True, size_hint=(1, 1))
        outer.add_widget(preview)
        outer.add_widget(popup_button("Сохранить в галерею", lambda: self.save_image_to_gallery(path), "accent", dp(46)))
        outer.add_widget(popup_button("Закрыть", popup.dismiss, "default", dp(42)))
        popup.add_widget(outer)
        popup.open()

    def save_image_to_gallery(self, path):
        if not path or not os.path.isfile(path):
            self.toast("Файл изображения не найден")
            return
        candidates = [os.path.join("/storage/emulated/0/Pictures", "AI Chat"),
                      os.path.join(ROOT, "exported_images")]
        for folder in candidates:
            try:
                os.makedirs(folder, exist_ok=True)
                target = os.path.join(folder, os.path.basename(path))
                if os.path.abspath(path) != os.path.abspath(target):
                    shutil.copy2(path, target)
                self.toast("Сохранено: " + target)
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass("org.renpy.android.PythonActivity")
                    Intent = autoclass("android.content.Intent")
                    Uri = autoclass("android.net.Uri")
                    activity = PythonActivity.mActivity
                    intent = Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE)
                    intent.setData(Uri.fromFile(autoclass("java.io.File")(target)))
                    activity.sendBroadcast(intent)
                except Exception:
                    pass
                return
            except Exception:
                continue
        self.toast("Не удалось сохранить в галерею. Изображение осталось в папке images")

    # Message actions / favorites / regeneration
    def open_message_actions(self, bubble):
        popup = RoundedPopup(size_hint=(0.90, 0.70))
        popup.container.add_widget(make_label("Действия с сообщением", 19, bold=True,
                                              height=dp(38), size_hint=(1, None)))
        preview = Label(text=bubble.text[:220], color=T("text_dim"), font_size=sp(12),
                        halign="left", valign="middle", size_hint=(1, None),
                        height=dp(65), padding=(dp(10), dp(8)))
        preview.bind(size=lambda *_: setattr(preview, "text_size", preview.size))
        popup.container.add_widget(preview)
        popup.container.add_widget(popup_button("Копировать", lambda: (self.copy_text(bubble.text), popup.dismiss())))
        if ANDROID:
            popup.container.add_widget(popup_button("Озвучить", lambda: (threading.Thread(target=voice_output, args=(bubble.text,), daemon=True).start(), popup.dismiss())))
        popup.container.add_widget(popup_button("Сохранить в заметки", lambda: (db_note_add(bubble.text), popup.dismiss(), self.toast("Сохранено в заметки"))))
        label = "Убрать из избранного" if bubble.starred else "Добавить в избранное"
        popup.container.add_widget(popup_button(label, lambda: self._toggle_star(bubble, popup), "accent"))
        if bubble.role == "ai" and bubble.msg_id:
            popup.container.add_widget(popup_button("Перегенерировать ответ", lambda: self._regenerate(bubble, popup)))
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss))
        popup.open()

    def open_quick_actions(self, bubble):
        popup = RoundedPopup(size_hint=(0.90, 0.84))
        popup.container.add_widget(make_label("ДЕЙСТВИЯ С ОТВЕТОМ", 11, "accent", True,
                                              size_hint=(1, None), height=dp(20)))
        popup.container.add_widget(make_label(bubble.text[:180].replace("\n", " "), 11, "text_dim",
                                              size_hint=(1, None), height=dp(44), valign="top"))
        popup.container.add_widget(popup_button("Копировать текст", lambda: (self.copy_text(bubble.text), popup.dismiss()), "default", dp(42)))
        popup.container.add_widget(popup_button("Продолжить ответ", lambda: self._follow_up_from_bubble(bubble, "Продолжи этот ответ с того места, где остановился. Не повторяй уже сказанное.", popup), "accent", dp(42)))
        popup.container.add_widget(popup_button("Объяснить проще", lambda: self._follow_up_from_bubble(bubble, "Объясни этот ответ проще, понятным языком, сохранив важные детали.", popup), "default", dp(42)))
        popup.container.add_widget(popup_button("Сделать короче", lambda: self._follow_up_from_bubble(bubble, "Сократи этот ответ до самого важного, без потери смысла.", popup), "default", dp(42)))
        popup.container.add_widget(popup_button("Добавить подробности", lambda: self._follow_up_from_bubble(bubble, "Раскрой этот ответ подробнее, добавь шаги и практические примеры.", popup), "default", dp(42)))
        popup.container.add_widget(popup_button("Сохранить в заметки", lambda: (db_note_add(bubble.text), popup.dismiss(), self.toast("Сохранено в заметки")), "default", dp(42)))
        label = "Убрать из избранного" if bubble.starred else "Добавить в избранное"
        popup.container.add_widget(popup_button(label, lambda: self._toggle_star(bubble, popup), "accent", dp(42)))
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss, "default", dp(42)))
        popup.open()

    def _follow_up_from_bubble(self, bubble, instruction, popup=None):
        """Build a context-explicit follow-up prompt, so actions work on older messages too."""
        if self.busy:
            self.toast("Сначала дождись завершения текущего ответа")
            if popup:
                popup.dismiss()
            return
        if popup:
            popup.dismiss()
        quoted = (bubble.text or "").strip()[:5000]
        prompt = instruction + "\n\nТекст ответа для работы:\n" + quoted
        self.input.text = prompt
        self.input.focus = False
        self.send()

    def _toggle_star(self, bubble, popup=None):
        if bubble.msg_id:
            db_toggle_star(bubble.msg_id)
            self.load_chat()
        else:
            self.toast("Сообщение ещё не сохранено в историю")
        if popup:
            popup.dismiss()

    def _regenerate(self, bubble, popup=None):
        if self.busy:
            self.toast("Сначала дождись завершения текущего ответа")
            if popup:
                popup.dismiss()
            return
        rows = db_messages(limit=10000, sid=SESSION_ID)
        target_index = next((i for i, row in enumerate(rows) if row["id"] == bubble.msg_id), -1)
        user_row = None
        if target_index >= 0:
            for row in reversed(rows[:target_index]):
                if row["role"] == "user":
                    user_row = row
                    break
        if not user_row:
            self.toast("Не найден исходный запрос")
            if popup:
                popup.dismiss()
            return
        prompt = user_row["content"]
        db_trim_from(SESSION_ID, user_row["id"])
        if popup:
            popup.dismiss()
        self.load_chat()
        self.input.text = prompt
        self.send()

    def copy_text(self, text):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(str(text))
            self.toast("Скопировано")
        except Exception:
            self.toast("Не удалось открыть буфер обмена")

    # Notes screen
    def open_notes(self):
        popup = RoundedPopup()
        popup.container.add_widget(make_label("Мои заметки", 20, bold=True,
                                              size_hint=(1, None), height=dp(42)))
        row = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(6))
        inp = TextInput(hint_text="Новая заметка…", multiline=False, font_size=sp(13),
                        foreground_color=T("text"), hint_text_color=T("text_dim"),
                        background_normal="", background_active="", background_color=T("panel2"),
                        padding=(dp(10), dp(10)))
        add = Button(text="Добавить", size_hint=(None, 1), width=dp(88))
        style_button(add, T("accent"), (1, 1, 1, 1), 12, True)
        row.add_widget(inp); row.add_widget(add); popup.container.add_widget(row)
        scroll = ScrollView(do_scroll_x=False)
        listing = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6), padding=(0, dp(4)))
        listing.bind(minimum_height=listing.setter("height"))
        scroll.add_widget(listing); popup.container.add_widget(scroll)

        def refresh():
            listing.clear_widgets()
            notes = db_notes()
            if not notes:
                listing.add_widget(make_label("Пока нет заметок", 13, "text_dim",
                                              size_hint=(1, None), height=dp(42)))
            for note in notes:
                line = BoxLayout(size_hint=(1, None), height=dp(62), spacing=dp(6), padding=(dp(8), dp(4)))
                with line.canvas.before:
                    Color(*T("panel3")); rect = RoundedRectangle(pos=line.pos, size=line.size, radius=[dp(12)])
                line.bind(pos=lambda *_args, r=rect, w=line: setattr(r, "pos", w.pos),
                          size=lambda *_args, r=rect, w=line: setattr(r, "size", w.size))
                lbl = Label(text=note["text"], color=T("text"), font_size=sp(12), halign="left", valign="middle")
                lbl.bind(size=lambda *_args, w=lbl: setattr(w, "text_size", w.size))
                delete = Button(text="×", size_hint=(None, 1), width=dp(38))
                style_button(delete, T("danger_bg"), T("danger"), 18, True)
                delete.bind(on_release=lambda *_args, n=note["id"]: (db_note_delete(n), refresh()))
                line.add_widget(lbl); line.add_widget(delete); listing.add_widget(line)

        def add_note(*_):
            value = inp.text.strip()
            if value:
                db_note_add(value); inp.text = ""; refresh()
        add.bind(on_release=add_note); inp.bind(on_text_validate=add_note)
        refresh()
        popup.container.add_widget(popup_button("Готово", popup.dismiss))
        popup.open()

    def open_starred(self):
        popup = RoundedPopup()
        popup.container.add_widget(make_label("Избранное", 20, bold=True,
                                              size_hint=(1, None), height=dp(42)))
        scroll = ScrollView(do_scroll_x=False)
        listing = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7), padding=(0, dp(4)))
        listing.bind(minimum_height=listing.setter("height")); scroll.add_widget(listing)
        popup.container.add_widget(scroll)
        rows = db_starred()
        if not rows:
            listing.add_widget(make_label("Нет сохранённых сообщений", 13, "text_dim",
                                          size_hint=(1, None), height=dp(50)))
        for row in rows:
            item = Button(text=f"★ {row['session_title'][:28]}\n{row['content'][:170]}",
                          size_hint=(1, None), height=dp(82), halign="left", valign="middle")
            item.text_size = (Window.width * 0.72, None)
            style_button(item, T("panel3"), T("text"), 12)
            item.bind(on_release=lambda *_args, sid=row["session_id"]: self.open_chat_by_id(sid, popup))
            listing.add_widget(item)
        popup.container.add_widget(popup_button("Готово", popup.dismiss))
        popup.open()

    # Main menu / sessions / search / settings
    def open_prompt_studio(self, *_):
        """A local prompt composer: add intent/style instructions without another API call."""
        popup = RoundedPopup(size_hint=(0.94, 0.82))
        popup.container.add_widget(make_label("МАСТЕР ЗАПРОСА", 17, "text", True,
                                              size_hint=(1, None), height=dp(34)))
        popup.container.add_widget(make_label("Сформулируй задачу точнее. Подсказки добавляются в поле автоматически.",
                                              10, "text_dim", False, size_hint=(1, None), height=dp(36), valign="top"))
        editor = TextInput(text=self.input.text, hint_text="Напиши, чего хочешь добиться…", multiline=True,
                           size_hint=(1, 1), font_size=sp(13), foreground_color=T("text"),
                           hint_text_color=T("text_dim"), cursor_color=T("accent"),
                           background_normal="", background_active="", background_color=T("panel2"),
                           padding=(dp(10), dp(10)))
        popup.container.add_widget(editor)
        tool_rows = [
            ("Пошагово", "Объясни по шагам, от простого к сложному."),
            ("С примерами", "Добавь конкретные примеры и покажи результат."),
            ("Кратко", "Сначала дай короткий вывод, затем только самое важное."),
            ("Проверь", "Проверь логику и факты; не скрывай неопределённость."),
            ("Для новичка", "Объясни для новичка, избегай лишнего жаргона."),
        ]
        row = GridLayout(cols=2, size_hint=(1, None), height=dp(124), spacing=dp(5))
        for caption, instruction in tool_rows:
            button = popup_button(caption, lambda value=instruction: self._append_prompt_instruction(editor, value), "default", dp(38))
            row.add_widget(button)
        popup.container.add_widget(row)
        actions = BoxLayout(size_hint=(1, None), height=dp(46), spacing=dp(7))
        actions.add_widget(popup_button("Вставить", lambda: self._apply_prompt_studio(editor, popup, False), "default"))
        actions.add_widget(popup_button("Отправить", lambda: self._apply_prompt_studio(editor, popup, True), "accent"))
        popup.container.add_widget(actions)
        popup.open()

    @staticmethod
    def _append_prompt_instruction(editor, instruction):
        current = editor.text.strip()
        if instruction.lower() not in current.lower():
            editor.text = (current + "\n\n" + instruction).strip() if current else instruction + "\n\nМоя задача: "
        editor.focus = True

    def _apply_prompt_studio(self, editor, popup, submit):
        value = editor.text.strip()
        if not value:
            self.toast("Сначала напиши запрос")
            return
        self.input.text = value
        popup.dismiss()
        if submit:
            self.send()
        else:
            self.input.focus = True
            self.toast("Запрос добавлен в поле ввода")

    def open_menu(self):
        if self.busy:
            self.toast("Заверши генерацию или нажми Стоп перед открытием меню")
            return
        popup = RoundedPopup()
        popup.container.add_widget(make_label("Меню", 21, bold=True,
                                              size_hint=(1, None), height=dp(42)))
        actions = [
            ("Новый чат", self.new_chat, "default"),
            ("Мои чаты", self.open_sessions, "default"),
            ("Поиск по истории", self.open_search, "default"),
            ("Мастер запроса", self.open_prompt_studio, "accent"),
            ("Смайлики и символы", self.open_emoji_picker, "default"),
            ("Заметки", self.open_notes, "default"),
            ("Избранное", self.open_starred, "default"),
            ("Копировать текущий чат", self.copy_current_chat, "default"),
            ("Экспорт текущего чата", self.export_chat, "default"),
            ("Настройки", self.open_settings, "accent"),
            ("Очистить текущий чат", self.confirm_clear, "danger"),
        ]
        scroll = ScrollView(do_scroll_x=False)
        listing = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7), padding=(0, dp(3)))
        listing.bind(minimum_height=listing.setter("height")); scroll.add_widget(listing)
        for label, callback, variant in actions:
            listing.add_widget(popup_button(label, lambda cb=callback: (popup.dismiss(), cb()), variant))
        popup.container.add_widget(scroll)
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss))
        popup.open()

    def copy_current_chat(self):
        body = "\n\n".join(("Ты" if row["role"] == "user" else "AI") + ": " + row["content"]
                              for row in db_messages(limit=10000, sid=SESSION_ID))
        if body:
            self.copy_text(body)
        else:
            self.toast("Чат пуст")

    def open_settings(self):
        """Premium, scrollable settings center with live options and useful tools."""
        if self.busy:
            self.toast("Измени настройки после завершения ответа")
            return

        popup = RoundedPopup(size_hint=(0.95, 0.91))
        # Header / hero status
        head = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(76), spacing=dp(2))
        head.add_widget(make_label("Настройки", 22, bold=True,
                                   size_hint=(1, 0.62)))
        head.add_widget(make_label("Персонализация · производительность · генерация", 10, "text_dim",
                                    size_hint=(1, 0.38)))
        popup.container.add_widget(head)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), scroll_type=["bars", "content"])
        items = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=(dp(1), dp(4), dp(1), dp(10)))
        items.bind(minimum_height=items.setter("height"))
        scroll.add_widget(items)
        popup.container.add_widget(scroll)

        def section(title, subtitle=""):
            card = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=dp(3), padding=(dp(11), dp(8)))
            with card.canvas.before:
                Color(*T("panel2"))
                rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(15)])
            card.bind(pos=lambda *_a, w=card, r=rect: setattr(r, "pos", w.pos),
                      size=lambda *_a, w=card, r=rect: setattr(r, "size", w.size),
                      minimum_height=card.setter("height"))
            title_lbl = make_label(title, 12, "accent", True, size_hint=(1, None), height=dp(22))
            card.add_widget(title_lbl)
            if subtitle:
                card.add_widget(make_label(subtitle, 10, "text_dim", size_hint=(1, None), height=dp(28)))
            items.add_widget(card)
            return card

        def selector(parent, label, key, choices, height=dp(40)):
            parent.add_widget(make_label(label, 12, "text", size_hint=(1, None), height=dp(25)))
            row = BoxLayout(size_hint=(1, None), height=height, spacing=dp(5))
            buttons = []
            def repaint():
                current = STATE.get(key)
                for value, button in buttons:
                    active = current == value
                    style_button(button, T("accent") if active else T("panel3"),
                                 (1, 1, 1, 1) if active else T("text"), 10, active, dp(13))
            for value, caption in choices:
                button = Button(text=caption, size_hint=(1, 1))
                if key == "font_family":
                    button.font_name = font_path(value)
                buttons.append((value, button))
                def choose(_btn, selected=value):
                    STATE[key] = selected
                    save_settings()
                    repaint()
                    if key in ("theme", "font_size", "font_weight", "font_family", "msg_spacing"):
                        self.toast("Внешний вид сохранён")
                    elif key == "provider_preference":
                        self.toast("Предпочтительный API сохранён")
                    elif key == "image_size":
                        self.toast("Параметры изображения сохранены")
                button.bind(on_release=choose)
                row.add_widget(button)
            parent.add_widget(row)
            repaint()

        def toggle(parent, title, key, description=""):
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(48), spacing=dp(7))
            left = BoxLayout(orientation="vertical", spacing=dp(1))
            left.add_widget(make_label(title, 12, "text", size_hint=(1, 0.62)))
            if description:
                left.add_widget(make_label(description, 9, "text_dim", size_hint=(1, 0.38)))
            button = Button(size_hint=(None, None), size=(dp(82), dp(34)))
            def repaint():
                enabled = bool(STATE.get(key, False))
                button.text = "ВКЛ" if enabled else "ВЫКЛ"
                style_button(button, T("success_bg") if enabled else T("panel3"),
                             T("success") if enabled else T("text_dim"), 10, True, dp(17))
            def flip(*_):
                STATE[key] = not bool(STATE.get(key, False))
                save_settings(); repaint()
                if key == "show_suggestions":
                    self._refresh_bottom_layout()
                elif key == "sparkle_background":
                    self._set_sparkles_enabled(bool(STATE.get(key, True)))
                elif key == "show_model_status":
                    self._update_status()
                elif key in ("show_time", "show_avatars", "msg_spacing", "font_size", "font_weight", "font_family", "theme"):
                    # Rebuilding after the sheet closes applies layout-wide changes consistently.
                    if key in ("show_time", "show_avatars"):
                        self.toast("Применится к новым сообщениям; перезапусти чат для старых")
            button.bind(on_release=flip)
            row.add_widget(left); row.add_widget(button)
            parent.add_widget(row); repaint()

        # Appearance
        card = section("ВНЕШНИЙ ВИД", "Персонализируй цвета, текст и плотность интерфейса")
        selector(card, "Цветовая тема", "theme", [("aurora", "Aurora"), ("night", "Ночь"), ("midnight", "Полночь"), ("daylight", "День")])
        selector(card, "Размер текста", "font_size", [("small", "S"), ("medium", "M"), ("large", "L"), ("xlarge", "XL")])
        selector(card, "Начертание по умолчанию", "font_weight", [("normal", "Обычный"), ("bold", "Жирный")])
        selector(card, "Гарнитура сообщений", "font_family", [("roboto", "Roboto"), ("serif", "Serif"), ("mono", "Mono"), ("noto", "Noto")])
        card.add_widget(make_label("Форматирование Markdown автоматически оформляет заголовки, жирный текст, курсив, списки, цитаты, ссылки и код.", 10, "text_dim", size_hint=(1, None), height=dp(38)))
        selector(card, "Интервалы сообщений", "msg_spacing", [("compact", "Плотно"), ("normal", "Обычно"), ("comfortable", "Свободно")])

        # Chat behavior
        card = section("ПОВЕДЕНИЕ ЧАТА", "Настройки отображения и управления перепиской")
        toggle(card, "Аватары", "show_avatars", "Показывать значки у сообщений")
        toggle(card, "Время сообщений", "show_time", "Небольшая отметка времени внутри пузыря")
        toggle(card, "Быстрые подсказки", "show_suggestions", "Скрывать подсказки во время ввода")
        toggle(card, "Статус модели в шапке", "show_model_status", "Название выбранного API под заголовком")
        toggle(card, "Автопрокрутка", "auto_scroll", "Прокручивать чат к новым ответам")
        toggle(card, "Анимации сообщений", "message_animations", "Плавное появление новых сообщений")
        toggle(card, "Режим без лагов", "performance_mode", "Объединяет фрагменты ответа и уменьшает лишние перерисовки")
        toggle(card, "Падающие искорки", "sparkle_background", "Лёгкая анимация на фоне чата; отключи для экономии батареи")
        if ANDROID:
            toggle(card, "Озвучивать ответы", "voice_out", "Автоматически читать ответы ИИ вслух")

        # AI tuning
        card = section("ИНТЕЛЛЕКТ И ОТВЕТЫ", "Выбери предпочтительный маршрут; резервные сервисы могут помочь при сбоях")
        provider_choices = [("auto", "Авто"), ("KeylessAI", "Keyless"), ("Kilo", "Kilo"), ("LLM7", "LLM7")]
        if IMAGE_API_KEY:
            provider_choices.append(("Pollinations", "Pollin."))
        selector(card, "Предпочтительный провайдер", "provider_preference", provider_choices)
        toggle(card, "Автоматический резерв", "fallback_enabled", "Переходить к другому сервису при ошибке")
        toggle(card, "Потоковая выдача", "streaming", "Показывать ответ по мере генерации, если API поддерживает")
        selector(card, "Стиль ответа", "creativity", [("precise", "Точно"), ("balanced", "Баланс"), ("creative", "Креатив")])
        selector(card, "Длина ответа", "response_length", [("short", "Кратко"), ("normal", "Обычно"), ("long", "Подробно")])
        card.add_widget(popup_button("Проверить соединение с API", lambda: self.run_diagnostics(popup), "accent"))

        # System instruction editor
        card = section("ИНСТРУКЦИИ ДЛЯ ИИ", "Дополнительные пожелания будут передаваться как системная инструкция")
        prompt_input = TextInput(text=STATE.get("custom_prompt", ""),
                                 hint_text="Например: объясняй простыми словами, отвечай по-русски…",
                                 multiline=True, size_hint=(1, None), height=dp(94),
                                 font_size=sp(12), foreground_color=T("text"),
                                 hint_text_color=T("text_dim"), cursor_color=T("accent"),
                                 background_normal="", background_active="", background_color=T("panel3"),
                                 padding=(dp(10), dp(9)))
        card.add_widget(prompt_input)
        def save_prompt():
            STATE["custom_prompt"] = prompt_input.text.strip()[:5000]
            save_settings()
            self.toast("Инструкции для ИИ сохранены")
        card.add_widget(popup_button("Сохранить инструкции", save_prompt, "accent"))
        card.add_widget(popup_button("Вернуть стандартные инструкции", lambda: (setattr(prompt_input, "text", ""), STATE.update({"custom_prompt": ""}), save_settings(), self.toast("Возвращены стандартные инструкции"))))

        # Image generation only; photo-input controls have been removed.
        card = section("ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ", "Создавай картинки из сообщения. Личный API-ключ не требуется; анонимная очередь может ждать дольше.")
        card.add_widget(make_label("Напиши «Нарисуй …». Готовая картинка появится в переписке и сохранится в папке images.", 11, "text_dim", size_hint=(1, None), height=dp(40)))
        selector(card, "Размер изображения", "image_size", [("512", "512 px · быстрее"), ("768", "768 px · детальнее")])
        card.add_widget(popup_button("Проверить AI Horde", lambda: self.run_diagnostics(popup), "default"))

        # Storage / safety
        card = section("ДАННЫЕ И ПРИВАТНОСТЬ", "История хранится локально; резервная копия помогает перенести данные")
        stats = self.get_storage_summary()
        card.add_widget(make_label(stats, 11, "text_dim", size_hint=(1, None), height=dp(42)))
        card.add_widget(popup_button("Создать резервную копию JSON", lambda: self.export_backup_json(), "default"))
        card.add_widget(popup_button("Очистить временные изображения", lambda: self.cleanup_unused_images(), "default"))
        card.add_widget(popup_button("Сбросить настройки интерфейса", lambda: self.reset_preferences(popup), "danger"))

        # App information / current status
        card = section("СИСТЕМА", "Диагностика и текущая конфигурация")
        card.add_widget(make_label("Последний ответ: " + str(STATE.get("last_provider", "—")) + " · " + str(STATE.get("last_model", "—")), 10, "text_dim", size_hint=(1, None), height=dp(24)))
        card.add_widget(make_label("Kivy / Android · SQLite · локальная история", 10, "text_dim", size_hint=(1, None), height=dp(22)))

        popup.container.add_widget(popup_button("Готово", lambda: self._close_settings(popup), "accent", dp(48)))
        popup.open()


    def _close_settings(self, popup):
        try:
            popup.dismiss()
        except Exception:
            pass
        save_settings()
        # Rebuild so changed appearance options consistently apply to the whole chat.
        app = App.get_running_app()
        if app:
            app.rebuild_ui()

    def open_external(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            self.toast("Открой ссылку вручную: " + url)

    def get_storage_summary(self):
        try:
            with DB_LOCK:
                sessions = DB.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
                messages = DB.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                notes = DB.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            total = 0
            for name in os.listdir(IMG_DIR):
                try:
                    full = os.path.join(IMG_DIR, name)
                    if os.path.isfile(full): total += os.path.getsize(full)
                except Exception:
                    pass
            return f"Чатов: {sessions} · сообщений: {messages} · заметок: {notes}\nИзображения ИИ: {total / (1024 * 1024):.1f} МБ"
        except Exception:
            return "Не удалось получить статистику хранилища."

    def export_backup_json(self):
        try:
            with DB_LOCK:
                sessions = [dict(row) for row in DB.execute("SELECT * FROM sessions ORDER BY updated DESC")]
                messages = [dict(row) for row in DB.execute("SELECT * FROM messages ORDER BY id")]
                notes = [dict(row) for row in DB.execute("SELECT * FROM notes ORDER BY id DESC")]
                # Do not include API credentials in backups.
                meta = {row["k"]: row["v"] for row in DB.execute("SELECT k,v FROM meta")
                        if row["k"] != "pollinations_api_key" }
            payload = {"app": "AI Chat Aurora", "version": "v" + APP_VERSION, "exported_at": DT.now().isoformat(timespec="seconds"),
                       "sessions": sessions, "messages": messages, "notes": notes, "settings": meta}
            path = os.path.join(ROOT, "ai_chat_backup_" + DT.now().strftime("%Y%m%d_%H%M%S") + ".json")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
            self.toast("Резервная копия создана: " + os.path.basename(path))
            return path
        except Exception as exc:
            self.toast("Не удалось создать резервную копию: " + str(exc)[:90])
            return None

    def cleanup_unused_images(self):
        try:
            with DB_LOCK:
                referenced = {os.path.abspath(row[0]) for row in DB.execute("SELECT image_path FROM messages WHERE image_path != ''")}
            removed = 0
            for name in os.listdir(IMG_DIR):
                path = os.path.abspath(os.path.join(IMG_DIR, name))
                if os.path.isfile(path) and path not in referenced:
                    try:
                        os.remove(path); removed += 1
                    except Exception:
                        pass
            self.toast(f"Удалено временных файлов: {removed}")
            return removed
        except Exception as exc:
            self.toast("Ошибка очистки: " + str(exc)[:80])
            return 0

    def reset_preferences(self, popup=None):
        defaults = dict(_SETTING_DEFAULTS)
        # Keep custom system instructions only if explicitly configured? Reset means restore base.
        for key, value in defaults.items():
            STATE[key] = value
        save_settings()
        if popup:
            popup.dismiss()
        app = App.get_running_app()
        if app:
            app.rebuild_ui()
        self.toast("Настройки интерфейса сброшены.")

    def run_diagnostics(self, parent_popup=None):
        if parent_popup:
            parent_popup.dismiss()
        self.toast("Проверяю подключение к API…")
        def worker():
            results = []
            for label, url in (
                ("Kilo", "https://api.kilo.ai/api/gateway/models"),
                ("AI Horde", "https://aihorde.net/api/v2/status/status"),
            ):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
                    with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as response:
                        results.append(f"{label}: доступен (HTTP {response.getcode()})")
                except urllib.error.HTTPError as exc:
                    results.append(f"{label}: ответ HTTP {exc.code}")
                except Exception as exc:
                    results.append(f"{label}: нет соединения ({friendly_api_error(str(exc))})")
            results.append("Генерация изображений: AI Horde, анонимный режим; очередь зависит от доступных исполнителей")
            report = "\n".join(results)
            Clock.schedule_once(lambda *_: self.show_diagnostic_report(report), 0)
        threading.Thread(target=worker, daemon=True).start()

    def show_diagnostic_report(self, report):
        popup = RoundedPopup(size_hint=(0.90, 0.54))
        popup.container.add_widget(make_label("Диагностика API", 20, bold=True,
                                              size_hint=(1, None), height=dp(42)))
        label = make_label(report, 12, "text", size_hint=(1, 1), valign="top")
        label.bind(size=lambda *_: setattr(label, "text_size", label.size))
        popup.container.add_widget(label)
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss, "accent"))
        popup.open()

    def open_sessions(self):
        popup = RoundedPopup()
        popup.container.add_widget(make_label("Мои чаты", 21, bold=True,
                                              size_hint=(1, None), height=dp(42)))
        scroll = ScrollView(do_scroll_x=False)
        listing = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7), padding=(0, dp(4)))
        listing.bind(minimum_height=listing.setter("height")); scroll.add_widget(listing)
        for session in db_sessions():
            row = BoxLayout(size_hint=(1, None), height=dp(54), spacing=dp(5))
            title = session["title"][:32]
            open_btn = Button(text=title + "\n" + session["updated"][:16], halign="left", valign="middle")
            style_button(open_btn, T("accent") if session["id"] == SESSION_ID else T("panel3"),
                         (1, 1, 1, 1) if session["id"] == SESSION_ID else T("text"), 12)
            open_btn.bind(on_release=lambda *_args, sid=session["id"]: self.open_chat_by_id(sid, popup))
            delete = Button(text="×", size_hint=(None, 1), width=dp(43))
            style_button(delete, T("danger_bg"), T("danger"), 18, True)
            delete.bind(on_release=lambda *_args, sid=session["id"], t=title: self.ask_delete_session(sid, t, popup))
            row.add_widget(open_btn); row.add_widget(delete); listing.add_widget(row)
        popup.container.add_widget(scroll)
        popup.container.add_widget(popup_button("Новый чат", lambda: (popup.dismiss(), self.new_chat()), "accent"))
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss))
        popup.open()

    def ask_delete_session(self, sid, title, parent_popup):
        confirm = Popup(title="Удалить чат?", title_color=T("text"), separator_color=T("danger"),
                        background_color=T("panel"), size_hint=(0.82, 0.34))
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(9))
        box.add_widget(make_label("Чат «" + title[:35] + "» будет удалён без возможности восстановления.",
                                  13, "text_dim", halign="center"))
        row = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(8))
        yes = Button(text="Удалить"); style_button(yes, T("danger"), (1, 1, 1, 1), 13, True)
        no = Button(text="Отмена"); style_button(no, T("panel3"), T("text"), 13)

        def do_delete(*_):
            global SESSION_ID
            confirm.dismiss()
            was_current = sid == SESSION_ID
            db_delete_session(sid)
            remaining = db_sessions()
            if was_current:
                if remaining:
                    SESSION_ID = remaining[0]["id"]
                    _meta_set("session_id", SESSION_ID)
                else:
                    SESSION_ID = new_session()
            elif not remaining:
                SESSION_ID = new_session()
            try:
                parent_popup.dismiss()
            except Exception:
                pass
            self.load_chat()
        yes.bind(on_release=do_delete)
        no.bind(on_release=lambda *_: confirm.dismiss())
        row.add_widget(yes); row.add_widget(no); box.add_widget(row)
        confirm.content = box
        confirm.open()

    def open_chat_by_id(self, sid, popup=None):
        if self.busy:
            self.toast("Дождись окончания генерации")
            return
        global SESSION_ID
        SESSION_ID = sid
        _meta_set("session_id", sid)
        if popup:
            popup.dismiss()
        self.load_chat()

    def new_chat(self):
        if self.busy:
            self.toast("Останови генерацию перед созданием нового чата")
            return
        global SESSION_ID
        SESSION_ID = new_session()
        self.load_chat()
        self._build_chips()
        self._set_chips_visible(False)

    def confirm_clear(self):
        confirm = Popup(title="Очистить чат?", title_color=T("text"), separator_color=T("danger"),
                        background_color=T("panel"), size_hint=(0.82, 0.33))
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(make_label("Все сообщения текущего чата будут удалены.", 13, "text_dim", halign="center"))
        row = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(8))
        yes = Button(text="Очистить"); style_button(yes, T("danger"), (1, 1, 1, 1), 13, True)
        no = Button(text="Отмена"); style_button(no, T("panel3"), T("text"), 13)
        def clear(*_):
            db_clear()
            confirm.dismiss()
            self.load_chat()
            self._build_chips()
            self._set_chips_visible(False)
        yes.bind(on_release=clear)
        no.bind(on_release=lambda *_: confirm.dismiss())
        row.add_widget(yes); row.add_widget(no); box.add_widget(row)
        confirm.content = box
        confirm.open()

    def open_search(self):
        popup = RoundedPopup()
        popup.container.add_widget(make_label("Поиск по истории", 20, bold=True,
                                              size_hint=(1, None), height=dp(40)))
        inp = TextInput(hint_text="Введите слово или фразу…", multiline=False,
                        size_hint=(1, None), height=dp(46), font_size=sp(13),
                        foreground_color=T("text"), hint_text_color=T("text_dim"),
                        background_normal="", background_active="", background_color=T("panel2"),
                        padding=(dp(10), dp(10)))
        popup.container.add_widget(inp)
        scroll = ScrollView(do_scroll_x=False)
        listing = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6), padding=(0, dp(4)))
        listing.bind(minimum_height=listing.setter("height")); scroll.add_widget(listing)
        popup.container.add_widget(scroll)

        def search(*_):
            listing.clear_widgets()
            query = inp.text.strip()
            if not query:
                return
            results = db_search(query)
            if not results:
                listing.add_widget(make_label("Ничего не найдено", 13, "text_dim",
                                              size_hint=(1, None), height=dp(40)))
            for result in results:
                title = result.get("session_title") or "Чат"
                snippet = ("Ты" if result["role"] == "user" else "AI") + " · " + title[:20] + "\n" + result["content"][:180]
                btn = Button(text=snippet, size_hint=(1, None), height=dp(78), halign="left", valign="middle")
                style_button(btn, T("panel3"), T("text"), 12)
                btn.bind(on_release=lambda *_args, sid=result["session_id"]: self.open_chat_by_id(sid, popup))
                listing.add_widget(btn)
        inp.bind(on_text_validate=search)
        popup.container.add_widget(popup_button("Найти", search, "accent"))
        popup.container.add_widget(popup_button("Закрыть", popup.dismiss))
        popup.open()

    def export_chat(self):
        try:
            rows = db_messages(limit=10000, sid=SESSION_ID)
            if not rows:
                self.toast("В чате пока нет сообщений")
                return None
            path = os.path.join(ROOT, "chat_" + DT.now().strftime("%Y%m%d_%H%M%S") + ".txt")
            with open(path, "w", encoding="utf-8") as file:
                for row in rows:
                    who = "Ты" if row["role"] == "user" else "AI"
                    file.write(f"{who} [{row['ts']}]:\n{row['content']}\n\n")
            self.toast("Файл сохранён: " + os.path.basename(path))
            return path
        except Exception as exc:
            self.toast("Ошибка экспорта: " + str(exc)[:70])
            return None

    def toast(self, text):
        view = ModalView(size_hint=(0.78, None), height=dp(58), background_color=(0, 0, 0, 0), auto_dismiss=True)
        box = BoxLayout(padding=(dp(12), dp(6)))
        with box.canvas.before:
            Color(*T("panel3")); rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(18)])
        box.bind(pos=lambda *_: setattr(rect, "pos", box.pos), size=lambda *_: setattr(rect, "size", box.size))
        label = Label(text=str(text)[:150], color=T("text"), font_size=sp(12), halign="center", valign="middle")
        label.bind(size=lambda *_: setattr(label, "text_size", label.size))
        box.add_widget(label); view.add_widget(box); view.open()
        Clock.schedule_once(lambda *_: view.dismiss(), 1.8)


class ChatApp(App):
    def build(self):
        self.title = "AI Chat Aurora"
        Window.clearcolor = T("bg_top")
        self.root_widget = ChatRoot()
        return self.root_widget

    def on_start(self):
        """Enable tablet rotation where appropriate and check Releases off the UI thread."""
        self._enable_tablet_rotation()
        threading.Thread(
            target=self._check_for_updates_worker,
            daemon=True,
            name="github-update-check",
        ).start()

    @staticmethod
    def _enable_tablet_rotation():
        """Allow sensor rotation on Android tablets (smallest width >= 600 dp)."""
        try:
            from jnius import autoclass
            activity_class = autoclass("org.renpy.android.PythonActivity")
            activity = activity_class.mActivity
            configuration = activity.getResources().getConfiguration()
            smallest_width = int(getattr(configuration, "smallestScreenWidthDp", 0))
            if smallest_width >= 600:
                activity_info = autoclass("android.content.pm.ActivityInfo")
                activity.setRequestedOrientation(activity_info.SCREEN_ORIENTATION_SENSOR)
        except Exception as exc:
            print("[Orientation] Tablet sensor rotation unavailable:", repr(exc))

    @staticmethod
    def _version_tuple(value):
        parts = re.findall(r"\d+", str(value))
        return tuple(int(part) for part in parts) if parts else (0,)

    def _check_for_updates_worker(self, manual=False):
        try:
            request = urllib.request.Request(
                UPDATE_API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "AI-Chat-Premium-Updater",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(
                request, timeout=15, context=SSL_CONTEXT
            ) as response:
                release = json.loads(response.read().decode("utf-8"))

            latest_version = str(release.get("tag_name", "")).strip()
            if not latest_version:
                Clock.schedule_once(
                    lambda _dt: self.root_widget.toast("Обновление: GitHub не вернул номер версии."), 0
                )
                return
            latest_tuple = self._version_tuple(latest_version)
            installed_tuple = self._version_tuple(APP_VERSION)
            print(f"[Updater] installed={APP_VERSION}; latest={latest_version}")
            if latest_tuple <= installed_tuple:
                if manual:
                    Clock.schedule_once(lambda _dt: self.root_widget.toast(
                        "Установлена последняя версия " + latest_version), 0)
                return

            release_url = str(
                release.get("html_url", "https://github.com/awayRu/Aish/releases")
            ).strip()
            apk_asset = next(
                (
                    asset for asset in (release.get("assets") or [])
                    if str(asset.get("name", "")).lower().endswith(".apk")
                    and asset.get("browser_download_url")
                ),
                None,
            )
            download_url = (
                str(apk_asset["browser_download_url"])
                if apk_asset else release_url
            )
            release_notes = str(release.get("body", "")).strip()[:700]
            Clock.schedule_once(
                lambda _dt: self._show_update_dialog(
                    latest_version, download_url, release_url, release_notes
                ),
                0,
            )
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}".strip()[:120]
            print("[Updater] GitHub Releases check failed:", error_text)
            Clock.schedule_once(
                lambda _dt, msg=error_text: self.root_widget.toast(
                    "Ошибка проверки обновления: " + msg[:90]
                ),
                0,
            )

    def _show_update_dialog(self, version, download_url, release_url, release_notes=""):
        """A compact, scroll-safe update card that fits portrait phones and landscape tablets."""
        try:
            max_height = max(dp(300), Window.height - dp(28))
            popup_height = min(dp(520), max_height)
            popup = RoundedPopup(size_hint=(0.93, None), height=popup_height)
            popup.container.padding = (dp(16), dp(14))
            popup.container.spacing = dp(9)

            hero = BoxLayout(orientation="horizontal", size_hint=(1, None),
                             height=dp(62), spacing=dp(11))
            hero.add_widget(Avatar("↑", T("accent"), size_px=dp(48)))
            hero_text = BoxLayout(orientation="vertical", spacing=dp(1))
            hero_text.add_widget(make_label("Доступно обновление", 18, bold=True,
                                            size_hint=(1, 0.62)))
            hero_text.add_widget(make_label("AI CHAT · НОВАЯ ВЕРСИЯ", 9, "accent", True,
                                            size_hint=(1, 0.38)))
            hero.add_widget(hero_text)
            popup.container.add_widget(hero)

            version_card = BoxLayout(orientation="vertical", size_hint=(1, None),
                                      height=dp(65), padding=(dp(12), dp(8)), spacing=dp(2))
            with version_card.canvas.before:
                Color(*T("panel2"))
                card_rect = RoundedRectangle(pos=version_card.pos, size=version_card.size,
                                             radius=[dp(15)])
            version_card.bind(pos=lambda *_args: setattr(card_rect, "pos", version_card.pos),
                              size=lambda *_args: setattr(card_rect, "size", version_card.size))
            version_text = str(version).strip()
            if version_text and not version_text.lower().startswith("v"):
                version_text = "v" + version_text
            version_card.add_widget(make_label("Новая версия  " + (version_text or "доступна"),
                                               15, "success", True, size_hint=(1, 0.56)))
            version_card.add_widget(make_label("Установлена версия: v" + APP_VERSION,
                                               10, "text_dim", size_hint=(1, 0.44)))
            popup.container.add_widget(version_card)

            notes = str(release_notes or "").strip()
            notes = re.sub(r"(?m)^#{1,6}\s*", "", notes)
            notes = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", notes)
            notes = notes[:1800]
            if notes:
                popup.container.add_widget(make_label("ЧТО НОВОГО", 10, "text_dim", True,
                                                      size_hint=(1, None), height=dp(19)))
                notes_scroll = ScrollView(do_scroll_x=False, bar_width=dp(2),
                                          scroll_type=["bars", "content"])
                notes_label = Label(text=notes, color=T("text"), font_size=sp(11),
                                    halign="left", valign="top", size_hint=(1, None),
                                    markup=False)
                def fit_notes(widget, *_args):
                    widget.text_size = (max(dp(80), widget.width - dp(8)), None)
                    widget.height = max(dp(28), widget.texture_size[1] + dp(8))
                notes_label.bind(texture_size=fit_notes, width=fit_notes)
                notes_scroll.add_widget(notes_label)
                notes_scroll.height = dp(112 if Window.width > Window.height else 132)
                popup.container.add_widget(notes_scroll)
            else:
                popup.container.add_widget(make_label(
                    "Улучшения и исправления уже готовы. Обнови приложение, чтобы получить их.",
                    12, "text_dim", size_hint=(1, 1), valign="top"))

            footer = BoxLayout(orientation="horizontal", size_hint=(1, None),
                               height=dp(46), spacing=dp(8))
            later = popup_button("Позже", popup.dismiss, "default", dp(46))

            def open_download(*_args):
                popup.dismiss()
                url = download_url or release_url
                try:
                    opened = webbrowser.open(url)
                    if not opened and release_url and release_url != url:
                        webbrowser.open(release_url)
                except Exception as exc:
                    print("[Updater] Cannot open download URL:", repr(exc))
                    try:
                        webbrowser.open(release_url or "https://github.com/awayRu/Aish/releases")
                    except Exception:
                        pass
                    Clock.schedule_once(lambda _dt: self.root_widget.toast(
                        "Не удалось открыть загрузку. Открой релиз в браузере."), 0)

            download = popup_button("Скачать APK", open_download, "accent", dp(46))
            footer.add_widget(later)
            footer.add_widget(download)
            popup.container.add_widget(footer)
            popup.open()
        except Exception as exc:
            print("[Updater] Cannot show update dialog:", repr(exc))
            try:
                self.root_widget.toast("Есть обновление " + str(version) + ". Открой релизы GitHub.")
            except Exception:
                pass

    def rebuild_ui(self):
        old = self.root_widget
        if getattr(old, "busy", False):
            old.toast("Настройки нельзя менять во время генерации")
            return
        try:
            old.dispose()
        except Exception:
            pass
        self.root.clear_widgets()
        self.root_widget = ChatRoot()
        self.root.add_widget(self.root_widget)
        Window.clearcolor = T("bg_top")

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    try:
        ChatApp().run()
    except BaseException:
        # Persist startup failures because Pydroid may close/hide the console.
        import traceback
        report = traceback.format_exc()
        print(report)
        try:
            log_path = os.path.join(ROOT, "ai_chat_startup_error.log")
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write("\n" + "=" * 72 + "\n")
                log_file.write(DT.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                log_file.write(report + "\n")
        except Exception:
            pass
