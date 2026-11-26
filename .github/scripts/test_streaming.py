"""Regression checks for complete and interrupted OpenAI-compatible streams."""

from email.message import Message
import json
from pathlib import Path
import sys
from threading import Event
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
    def test_reads_utf8_chunks(self):
        pieces = []
        response = Response([fragment("Один"), fragment(" два"), b"data: [DONE]\n"])
        with patch.object(main, "_model_response", return_value=response):
            self.assertEqual(main._stream_request(None, pieces.append), ("Один два", None))
        self.assertEqual(pieces, ["Один", " два"])

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


if __name__ == "__main__":
    unittest.main()
