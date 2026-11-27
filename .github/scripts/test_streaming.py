"""Regression checks for complete and interrupted OpenAI-compatible streams."""

from email.message import Message
import json
from pathlib import Path
import sys
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import main


class Response:
    def __init__(self, lines):
        self.lines = iter(lines)
        self.headers = Message()
        self.headers["Content-Type"] = "text/event-stream"

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def readline(self):
        item = next(self.lines, b"")
        if isinstance(item, Exception):
            raise item
        return item


def fragment(text):
    return ("data: " + json.dumps({"choices": [{"delta": {"content": text}}]}) + "\n").encode()


class StreamingTests(unittest.TestCase):
    def test_copy_preserves_indentation_of_closed_code_fences(self):
        code = {}
        text = "Ссылка [документация](https://example.com)\n```python\r\nif ready:\r\n    start()\r\n```\n```text\nчасть"
        markup, links = main.render_markdown(text, code_blocks=code)
        self.assertIn("[ref=mdcode0]", markup)
        self.assertEqual(code, {"mdcode0": "if ready:\n    start()"})
        self.assertEqual(links, {"mdlink0": "https://example.com"})
        main.render_markdown("````md\n```python\nprint(42)\n```\n````\n", code_blocks=code)
        self.assertEqual(code, {"mdcode0": "```python\nprint(42)\n```"})
        main.render_markdown("Другой ответ", code_blocks=code)
        self.assertEqual(code, {})

    def test_reads_utf8_chunks(self):
        pieces = []
        response = Response([fragment("Один"), fragment(" два"), b"data: [DONE]\n"])
        with patch.object(main, "_model_response", return_value=response):
            self.assertEqual(main._stream_request(None, pieces.append), ("Один два", None))
        self.assertEqual(pieces, ["Один", " два"])

    def test_long_chat_draws_rows_in_the_scrolled_viewport(self):
        layout = main.BoxLayout(orientation="vertical", size_hint_y=None, height=2000)
        rows = []
        for index in range(100):
            widget = main.Widget(size_hint_y=None, height=20, y=index * 20)
            layout.add_widget(widget)
            rows.append(widget)
        root = SimpleNamespace(messages_box=layout, scroll=SimpleNamespace(height=200, scroll_y=0))

        main.ChatRoot._update_message_canvases(root)
        self.assertIn(rows[0].canvas, layout.canvas.children)
        self.assertNotIn(rows[-1].canvas, layout.canvas.children)
        root.scroll.scroll_y = 1
        main.ChatRoot._update_message_canvases(root)
        self.assertNotIn(rows[0].canvas, layout.canvas.children)
        self.assertIn(rows[-1].canvas, layout.canvas.children)
        self.assertIs(rows[0].parent, layout)

        layout.clear_widgets(rows[1:])
        main.ChatRoot._update_message_canvases(root)
        self.assertEqual(layout.children, rows[:1])
        self.assertIn(rows[0].canvas, layout.canvas.children)

    def test_transport_error_keeps_partial_reply(self):
        response = Response([fragment("Полученная часть"), TimeoutError()])
        with patch.object(main, "_model_response", return_value=response):
            text, error = main._stream_request(None)
        self.assertEqual(text, "Полученная часть")
        self.assertIn("таймаут", error)
        providers = [{"name": "first"}, {"name": "backup"}]
        with patch.object(main, "try_provider", return_value=(text, error)) as request:
            reply, error = main.ask_ai([], providers=providers)
        self.assertEqual(reply, text)
        self.assertTrue(error)
        self.assertEqual(request.call_count, 1)

    def test_stop_keeps_last_chunk(self):
        cancel = Event()
        with patch.object(main, "_model_response", return_value=Response([fragment("Часть"), fragment("лишнее")])):
            self.assertEqual(main._stream_request(None, lambda _text: cancel.set(), cancel), ("Часть", None))

    def test_stop_finalizes_once_while_provider_is_still_blocked(self):
        from unittest.mock import Mock

        root = SimpleNamespace(
            request_kind="chat", request_id="first", _request_session="original-chat",
            busy=True, cancel_event=Event(), stream_bubble=None, _at_bottom=False,
            _stream_display_buffer="partial reply", _pending_finish_payload=None,
            _stream_display_event=Mock(), _flush_stream_pieces=Mock(),
            _remove_typing=Mock(), add_message=Mock(),
        )
        root._set_busy = lambda value: setattr(root, "busy", value)
        root._complete_ai_finish = lambda *args: main.ChatRoot._complete_ai_finish(root, *args)
        cancel = root.cancel_event
        with patch.object(main, "db_add", return_value=7) as store:
            main.ChatRoot.stop_generation(root)
            main.ChatRoot._finish_ai(root, "first", "late result", None, True)
        self.assertTrue(cancel.is_set())
        self.assertFalse(root.busy)
        store.assert_called_once_with("assistant", "[прервано] partial reply", "original-chat")
        root.add_message.assert_called_once_with("ai", "partial reply", msg_id=7,
                                               interrupted=True, auto_scroll=False)


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        main.DB.close()
