"""Atomic, owner-only reads and writes.

Every file this plugin owns is written to a temporary file in the same folder,
flushed to disk, and then moved into place, so an interrupted run leaves the
previous file exactly as it was. Files are readable and writable by their owner
only, and the folders that hold them are owner only as well.

A writer that knows which folder a file belongs in passes `inside`. The folder
the file would land in is then resolved all the way through any link before
anything is written, and a folder that turns out to sit outside the one named
is refused. Every writer that puts a file into a base should pass it, so a link
planted in the shared copy cannot make a write land somewhere else on this
computer. The proposal and confirmation writers pass the base root; the marker
and the account state pass the seat folder.
"""

from __future__ import annotations

import errno
import json
import os
import tempfile
from typing import Any, Optional

from .errors import PathError

FILE_MODE = 0o600
DIR_MODE = 0o700


def ensure_dir(path: str, mode: int = DIR_MODE) -> str:
    """Create a folder and every parent, owner only, and return its path."""
    if not os.path.isdir(path):
        try:
            os.makedirs(path, mode)
        except OSError as failure:
            if failure.errno != errno.EEXIST:
                raise
        else:
            try:
                os.chmod(path, mode)
            except OSError:
                pass
    return path


def _check_inside(folder: str, inside: str) -> None:
    """Refuse a write whose folder resolves outside the one it belongs in."""
    root = os.path.realpath(inside)
    real = os.path.realpath(folder)
    if real != root and not real.startswith(root.rstrip(os.sep) + os.sep):
        raise PathError(
            "this file would land outside the folder it belongs in",
            code="outside-root",
        )


def atomic_write_text(
    path: str, text: str, mode: int = FILE_MODE, inside: Optional[str] = None
) -> str:
    """Write text to path so that readers see either the old file or the new one.

    When `inside` names a folder, the folder the file would land in is resolved
    through every link first and the write is refused when it lands outside.
    """
    folder = os.path.dirname(os.path.abspath(path))
    ensure_dir(folder)
    if inside:
        _check_inside(folder, inside)
    handle, temp_path = tempfile.mkstemp(prefix=".gtmbase-", dir=folder)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    except BaseException:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
    _sync_folder(folder)
    return path


def atomic_write_json(
    path: str, value: Any, mode: int = FILE_MODE, inside: Optional[str] = None
) -> str:
    """Write a value as formatted JSON, atomically and owner only."""
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return atomic_write_text(path, text, mode, inside=inside)


def read_text(path: str) -> Optional[str]:
    """Return the contents of a file, or None when it is not there or not a file."""
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as stream:
            return stream.read()
    except (OSError, UnicodeDecodeError):
        return None


def read_json(path: str) -> Any:
    """Return the parsed JSON at path, or None when it is missing or malformed."""
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def remove(path: str) -> bool:
    """Delete a file if it is there. Return whether anything was deleted."""
    try:
        os.unlink(path)
        return True
    except OSError:
        return False


def _sync_folder(folder: str) -> None:
    """Ask the operating system to record the new directory entry."""
    try:
        handle = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)
