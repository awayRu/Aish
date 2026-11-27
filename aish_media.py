"""Prepare local photos and request images from Aish's public providers."""

import base64
import binascii
from dataclasses import dataclass
from http.client import HTTPException, HTTPSConnection
from io import BytesIO
import json
import mimetypes
import os
from pathlib import Path
from shutil import copyfileobj
import time
from urllib.parse import urlsplit
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

OVH_API = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
HORDE_API = "https://aihorde.net/api/v2"
PHOTO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_VISION_BYTES = 3 * 1024 * 1024
MAX_GENERATION_RESPONSE = 18 * 1024 * 1024
MAX_QUEUE_RESPONSE = 128 * 1024
POLL_SECONDS = 3
HORDE_TIMEOUT = 120
_FORMATS = {"JPEG", "PNG", "WEBP"}
_ASPECTS = {"1:1": (1, 1), "4:5": (4, 5), "16:9": (16, 9)}


class ImageServiceUnavailable(RuntimeError):
    """A connection, capacity, or rate-limit failure that permits fallback."""


@dataclass(frozen=True)
class Photo:
    name: str
    jpeg: bytes


def _check_image(opened, allowed, too_large):
    if opened.format not in allowed:
        raise ValueError("Используй JPG, PNG или WebP.")
    if opened.width * opened.height > MAX_PIXELS:
        raise ValueError(too_large)


def _rgb(image):
    if "A" in image.getbands() or "transparency" in image.info:
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (248, 249, 247))
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        return canvas
    return image.convert("RGB")


def prepare_photo(source, name):
    raw = source.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Фото превышает ограничение 16 МБ.")
    try:
        with Image.open(BytesIO(raw)) as opened:
            _check_image(opened, _FORMATS, "Фото больше 24 мегапикселей. Уменьши его и попробуй снова.")
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((1344, 1344), LANCZOS)
            out = BytesIO()
            _rgb(image).save(out, format="JPEG", quality=88, optimize=True)
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError("Не удалось прочитать изображение.") from error
    filename = str(name or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return Photo(filename[:100] or "Фото", out.getvalue())


def _write_image(directory, prefix, suffix, data):
    path = Path(directory) / (prefix + uuid.uuid4().hex + suffix)
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("xb") as target:
            target.write(data)
        temporary.replace(path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise OSError("Не удалось сохранить изображение. Проверь свободное место.") from error
    return path


def store_photo(photo, directory):
    return str(_write_image(directory, "aish_photo_", ".jpg", photo.jpeg))


def export_android_picture(path):
    """Publish a complete copy in the Android system gallery on Android 10+."""
    from jnius import autoclass

    path = Path(path)
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    resolver = activity.getContentResolver()
    media = autoclass("android.provider.MediaStore$Images$Media")
    values = autoclass("android.content.ContentValues")()
    values.put("_display_name", path.name)
    values.put("mime_type", mimetypes.guess_type(path.name)[0] or "image/jpeg")
    values.put("relative_path", "Pictures/Aish")
    values.put("is_pending", "1")
    uri = resolver.insert(media.EXTERNAL_CONTENT_URI, values)
    if uri is None:
        raise OSError("Галерея не приняла изображение.")
    try:
        with path.open("rb") as source:
            descriptor = resolver.openFileDescriptor(uri, "w")
            if descriptor is None:
                raise OSError("Не удалось открыть файл галереи.")
            with os.fdopen(descriptor.detachFd(), "wb") as target:
                copyfileobj(source, target)
        values.clear()
        values.put("is_pending", "0")
        if resolver.update(uri, values, None, None) != 1:
            raise OSError("Галерея не завершила сохранение.")
    except Exception:
        try:
            resolver.delete(uri, None, None)
        except Exception:
            pass
        raise


def vision_content(text, path):
    message = "Прикрепи фото заново. Сохранённый файл недоступен или повреждён."
    try:
        with Path(path).open("rb") as source:
            raw = source.read(MAX_VISION_BYTES + 1)
        if len(raw) > MAX_VISION_BYTES:
            raise ValueError(message)
        with Image.open(BytesIO(raw)) as opened:
            if opened.format != "JPEG" or max(opened.size) > 1344:
                raise ValueError(message)
            opened.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError(message) from error
    data_url = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    return [{"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": data_url}}]


def _cancelled(cancel):
    if cancel is not None and cancel.is_set():
        raise InterruptedError("Создание изображения отменено.")


def _time_left(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ImageServiceUnavailable("Генератор не ответил вовремя. Попробуй снова чуть позже.")
    return remaining


def _json_request(url, *, ssl_context, cancel, deadline, limit,
                  timeout=20, headers=None, body=None, method=None):
    _cancelled(cancel)
    endpoint = urlsplit(url)
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"User-Agent": "Aish", "Accept": "application/json",
                       "Content-Type": "application/json", **(headers or {})}
    # urllib sends Connection: close. AI Horde's gateway can hang on that header.
    # A fixed HTTPS connection also leaves redirects unhandled.
    connection = HTTPSConnection(endpoint.hostname, timeout=min(timeout, _time_left(deadline)),
                                 context=ssl_context)
    try:
        connection.request(method or ("POST" if body is not None else "GET"), endpoint.path,
                           body=payload, headers=request_headers)
        with connection.getresponse() as response:
            if response.status in {408, 429, 502, 503, 504}:
                raise ImageServiceUnavailable("Генератор сейчас недоступен или перегружен.")
            if not 200 <= response.status < 300:
                raise RuntimeError("Сервис отклонил запрос (HTTP " + str(response.status) + ").")
            raw = bytearray()
            while True:
                _cancelled(cancel)
                _time_left(deadline)
                part = response.read1(min(65536, limit + 1 - len(raw)))
                if not part:
                    break
                raw.extend(part)
                if len(raw) > limit:
                    raise ValueError("Сервис вернул слишком большой ответ.")
    except InterruptedError:
        raise
    except (HTTPException, OSError) as error:
        raise ImageServiceUnavailable("Не удалось подключиться к генератору.") from error
    finally:
        connection.close()
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Сервис вернул некорректный ответ.") from error
    if not isinstance(result, dict):
        raise ValueError("Сервис вернул некорректный ответ.")
    return result


def _prompt_text(prompt):
    cleaned = str(prompt or "").strip()
    if not cleaned:
        raise ValueError("Напиши, что нарисовать.")
    if len(cleaned) > 700:
        raise ValueError("Описание должно содержать не больше 700 символов.")
    return cleaned


def _target(size, ratio):
    if ratio not in _ASPECTS:
        raise ValueError("Выбери формат 1:1, 4:5 или 16:9.")
    width, height = _ASPECTS[ratio]
    side = max(width, height)
    longest = int(size) if str(size) in {"512", "768", "1024"} else 1024
    step = longest // side
    return width * step, height * step


def _result_entry(body, key):
    entries = body.get(key)
    if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
        raise ValueError("Сервис не вернул готовое изображение.")
    entry = entries[0]
    state = entry.get("state")
    if entry.get("censored") or state in ("censored", "csam"):
        raise RuntimeError("Сервис заблокировал результат по правилам обработки изображений.")
    if state in ("faulted", "failed"):
        raise RuntimeError("Сервис не смог создать изображение.")
    return entry


def _save_picture(encoded, target, directory, cancel):
    _cancelled(cancel)
    if not isinstance(encoded, str):
        raise ValueError("Сервис не вернул данные изображения.")
    try:
        raw = base64.b64decode(encoded, validate=True)
        with Image.open(BytesIO(raw)) as opened:
            if opened.format not in _FORMATS or opened.width * opened.height > MAX_PIXELS:
                raise ValueError("Сервис вернул неподдерживаемый формат или размер изображения.")
            image = _rgb(ImageOps.exif_transpose(opened))
            image = ImageOps.fit(image, target, method=LANCZOS)
            out = BytesIO()
            image.save(out, format="PNG")
    except (binascii.Error, UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError("Сервис не вернул пригодное изображение.") from error
    _cancelled(cancel)
    path = _write_image(directory, "aish_image_", ".png", out.getvalue())
    if cancel is not None and cancel.is_set():
        path.unlink(missing_ok=True)
        _cancelled(cancel)
    return str(path)


def create_picture(prompt, size, directory, ssl_context, cancel, *, ratio="1:1"):
    """Generate with OVH and deliver the requested aspect ratio by center cropping."""
    target = _target(size, ratio)
    body = _json_request(
        OVH_API + "/images/generations", ssl_context=ssl_context, cancel=cancel,
        deadline=time.monotonic() + 55, limit=MAX_GENERATION_RESPONSE, timeout=48,
        body={"model": "stable-diffusion-xl-base-v10", "prompt": _prompt_text(prompt),
              "size": "1024x1024"})
    return _save_picture(_result_entry(body, "data").get("b64_json"), target, directory, cancel)


def _parse_job(value):
    try:
        return str(uuid.UUID(value))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("AI Horde не вернул номер задания.") from error


def _wait_for_job(cancel, deadline):
    seconds = min(POLL_SECONDS, _time_left(deadline))
    if cancel is None:
        time.sleep(seconds)
    elif cancel.wait(seconds):
        _cancelled(cancel)


def create_horde_picture(prompt, size, directory, ssl_context, cancel, *, ratio="1:1", on_wait=None):
    """Use the opt-in AI Horde fallback. on_wait receives a queue estimate in seconds or None."""
    target = _target(size, ratio)
    deadline = time.monotonic() + HORDE_TIMEOUT
    headers = {"apikey": "0000000000", "Client-Agent": "Aish:46:github.com/awayRu/Aish"}
    width, height = (max(64, round(value / 64) * 64) for value in target)
    # Anonymous workers may limit jobs by resolution, steps, and current queue capacity.
    payload = {
        "prompt": _prompt_text(prompt),
        "params": {"width": width, "height": height, "steps": 16, "n": 1,
                   "cfg_scale": 7.0, "karras": True},
        "nsfw": False, "censor_nsfw": True, "allow_downgrade": True,
        "r2": False, "shared": False,
    }
    submitted = _json_request(
        HORDE_API + "/generate/async", ssl_context=ssl_context, cancel=cancel, deadline=deadline,
        limit=MAX_QUEUE_RESPONSE, headers=headers, body=payload)
    job_id = _parse_job(submitted.get("id"))
    status_url = HORDE_API + "/generate/status/" + job_id
    finished = False
    try:
        while True:
            status = _json_request(
                HORDE_API + "/generate/check/" + job_id, ssl_context=ssl_context, cancel=cancel,
                deadline=deadline, limit=MAX_QUEUE_RESPONSE, headers=headers)
            if status.get("faulted"):
                finished = True
                raise RuntimeError("AI Horde не смог создать изображение.")
            if status.get("done"):
                finished = True
                break
            if on_wait is not None:
                estimate = status.get("wait_time")
                on_wait(estimate if type(estimate) is int and estimate > 0 else None)
            _wait_for_job(cancel, deadline)
        result = _json_request(status_url, ssl_context=ssl_context, cancel=cancel, deadline=deadline,
                               limit=MAX_GENERATION_RESPONSE, headers=headers)
        return _save_picture(_result_entry(result, "generations").get("img"), target, directory, cancel)
    finally:
        if not finished:
            try:
                _json_request(status_url, ssl_context=ssl_context, cancel=None,
                              deadline=time.monotonic() + 5, limit=MAX_QUEUE_RESPONSE,
                              headers=headers, method="DELETE")
            except (RuntimeError, ValueError, OSError):
                pass
