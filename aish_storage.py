"""Resolve chat storage and migrate older Android installs without replacing their data."""

from contextlib import closing, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import filecmp
import logging
import os
import re
import shutil
import sqlite3
import sys


_LOG = logging.getLogger(__name__)
_LEGACY_IMAGE_MESSAGE = re.compile(r"(Изображение готово и сохранено:\s*\n)([^\n]+)")


def data_directory(root, override=None):
    if override:
        return Path(override)
    root = Path(root)
    if sys.platform != "android" and not (os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_PRIVATE")):
        return root

    from android.storage import app_storage_path

    destination = Path(app_storage_path()) / "aish-data"
    if not (root / "chat.db").is_file() or (destination / "chat.db").exists():
        return destination
    try:
        _migrate_legacy_storage(root, destination)
    except (OSError, sqlite3.Error):
        if (destination / "chat.db").exists():
            return destination
        # The build hook keeps the old data available, so failed migrations can be retried.
        _LOG.exception("Could not migrate Android chat history. Keeping the original storage.")
        return root
    return destination


@contextmanager
def _migration_lock(path):
    # Lock a stable file across processes. The OS releases the lock on process exit.
    with path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX)
            yield


def _migrate_legacy_storage(root, destination):
    original = root / "chat.db"
    migrated = destination / "chat.db"
    destination.mkdir(parents=True, exist_ok=True)
    with _migration_lock(destination / ".migration.lock"):
        if migrated.exists() or not original.is_file():
            return
        with TemporaryDirectory(prefix=".migration-", dir=destination) as temporary:
            stage = Path(temporary)
            staged_db = stage / "chat.db"
            with closing(sqlite3.connect(original.resolve().as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(staged_db)) as target:
                    source.backup(target)
                    target.execute("PRAGMA journal_mode=DELETE")
                    paths = _copy_legacy_images(root / "images", destination / "images", stage)
                    with target:
                        _rewrite_image_paths(target, root, paths)
            # Publish chat.db last. Partial copies are reusable on the next launch.
            if not migrated.exists():
                os.replace(staged_db, migrated)


def _copy_legacy_images(source, destination, stage):
    if not source.is_dir() or source.is_symlink():
        return {}
    relocated = {}
    staged_image = stage / "image"
    for file in source.rglob("*"):
        if not file.is_file() or file.is_symlink():
            continue
        target = destination / file.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = _available_image_path(file, target)
        if not target.exists():
            shutil.copy2(file, staged_image)
            os.replace(staged_image, target)
        relocated[file.resolve()] = str(target)
    return relocated


def _available_image_path(source, target):
    name = target
    suffix = 0
    while name.exists() or name.is_symlink():
        if name.is_file() and not name.is_symlink() and filecmp.cmp(source, name, shallow=False):
            return name
        suffix += 1
        name = target.with_name(f"{target.stem}-legacy-{suffix}{target.suffix}")
    return name


def _rewrite_image_paths(database, root, relocated):
    if not relocated:
        return
    columns = {row[1] for row in database.execute("PRAGMA table_info(messages)")}
    if "id" not in columns:
        return

    def migrated_path(value):
        if not value:
            return None
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        try:
            return relocated.get(path.resolve())
        except (OSError, RuntimeError, ValueError):
            return None

    if "image_path" in columns:
        for message_id, path in database.execute("SELECT id, image_path FROM messages WHERE image_path <> ''"):
            new_path = migrated_path(path)
            if new_path:
                database.execute("UPDATE messages SET image_path=? WHERE id=?", (new_path, message_id))

    if {"role", "content"}.issubset(columns):
        # Earlier releases embedded generated image paths in the assistant's text.
        for message_id, content in database.execute(
            "SELECT id, content FROM messages WHERE role='assistant' AND content LIKE '%Изображение готово и сохранено:%'"
        ):
            match = _LEGACY_IMAGE_MESSAGE.search(content)
            new_path = migrated_path(match[2].strip()) if match else None
            if new_path:
                new_content = content[:match.start(2)] + new_path + content[match.end(2):]
                database.execute("UPDATE messages SET content=? WHERE id=?", (new_content, message_id))
                if "image_path" in columns:
                    database.execute(
                        "UPDATE messages SET image_path=? WHERE id=? AND image_path=''",
                        (new_path, message_id),
                    )
