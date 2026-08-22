"""
json_utils.py
=============
Reusable, production-friendly helpers for reading and writing JSON files.

Features
--------
- Safe reads with a configurable default if the file is missing/empty/corrupt
- Atomic writes (write to temp file + rename) to avoid corrupting data on crash
- Optional pretty-printing, key sorting, and directory auto-creation
- Update helper to read-modify-write in one call
- Proper logging and typed exceptions instead of silent failures

Usage
-----
    from json_utils import read_json, write_json, update_json

    write_json("data/config.json", {"a": 1, "b": 2})

    data = read_json("data/config.json")           # -> {"a": 1, "b": 2}
    data = read_json("data/missing.json", default={})  # -> {}

    update_json("data/config.json", lambda d: {**d, "c": 3})
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, Union

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("json_utils")

PathLike = Union[str, os.PathLike]


class JSONFileError(Exception):
    """Raised when a JSON file cannot be read or written and no default was given."""


def read_json_from_file(
    path: PathLike,
    default: Any = ...,
    encoding: str = "utf-8",
) -> Any:
    """
    Read and parse a JSON file.

    Parameters
    ----------
    path      Path to the JSON file.
    default   Value to return if the file doesn't exist or is invalid/empty.
              If omitted, errors are raised instead of swallowed.
    encoding  File encoding (default utf-8).

    Returns
    -------
    The parsed JSON content (dict/list/etc.), or `default` on failure.
    """
    file_path = Path(path)

    if not file_path.exists():
        if default is not ...:
            logger.warning(f"{file_path} not found. Returning default.")
            return default
        raise JSONFileError(f"File not found: {file_path}")

    try:
        with file_path.open("r", encoding=encoding) as f:
            content = f.read().strip()
            if not content:
                raise json.JSONDecodeError("Empty file", content, 0)
            return json.loads(content)

    except (json.JSONDecodeError, OSError) as e:
        if default is not ...:
            logger.warning(f"Failed to read {file_path} ({e}). Returning default.")
            return default
        raise JSONFileError(f"Failed to read JSON from {file_path}: {e}") from e


def write_json_to_file(
    path: PathLike,
    data: Any,
    indent: int = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    create_dirs: bool = True,
    atomic: bool = True,
    encoding: str = "utf-8",
) -> None:
    """
    Serialize `data` to JSON and write it to `path`.

    Parameters
    ----------
    path          Destination file path.
    data          Any JSON-serializable object.
    indent        Pretty-print indent width (None for compact single-line output).
    sort_keys     Sort dict keys alphabetically in the output.
    ensure_ascii  If False (default), writes UTF-8 characters directly instead of \\uXXXX escapes.
    create_dirs   Create parent directories if they don't exist.
    atomic        Write to a temp file and rename over the target, so a crash
                  mid-write can't leave a corrupted/partial file behind.
    encoding      File encoding (default utf-8).
    """
    file_path = Path(path)

    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        payload = json.dumps(
            data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii
        )
    except (TypeError, ValueError) as e:
        raise JSONFileError(f"Data is not JSON-serializable: {e}") from e

    try:
        if atomic:
            # Write to a temp file in the same directory, then atomically rename.
            fd, tmp_path = tempfile.mkstemp(
                dir=str(file_path.parent), prefix=f".{file_path.name}.", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding=encoding) as f:
                    f.write(payload)
                os.replace(tmp_path, file_path)  # atomic on POSIX and Windows
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
        else:
            with file_path.open("w", encoding=encoding) as f:
                f.write(payload)

        logger.info(f"Wrote JSON to {file_path}")

    except OSError as e:
        raise JSONFileError(f"Failed to write JSON to {file_path}: {e}") from e


def update_json(
    path: PathLike,
    updater: Callable[[Any], Any],
    default: Any = dict,
    **write_kwargs: Any,
) -> Any:
    """
    Read-modify-write helper: loads the existing JSON (or `default` if missing),
    passes it to `updater`, and writes back whatever `updater` returns.

    Parameters
    ----------
    path      Path to the JSON file.
    updater   Callable that receives the current data and returns the new data.
    default   Value (or zero-arg callable, e.g. `dict` or `list`) used if the
              file doesn't exist yet.
    write_kwargs  Extra keyword args forwarded to write_json (indent, sort_keys, etc.)

    Returns
    -------
    The new data that was written.
    """
    initial_default = default() if callable(default) else default
    current = read_json(path, default=initial_default)
    updated = updater(current)
    write_json(path, updated, **write_kwargs)
    return updated


# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------
if __name__ == "__main__":
    sample_path = "example_data.json"

    # Write
    write_json(sample_path, {"name": "Alice", "scores": [90, 85, 92]})

    # Read (with fallback if missing/corrupt)
    data = read_json(sample_path, default={})
    print("Read:", data)

    # Update in place
    update_json(sample_path, lambda d: {**d, "scores": d["scores"] + [100]})
    print("After update:", read_json(sample_path))

    # Reading a nonexistent file with a default instead of raising
    missing = read_json("does_not_exist.json", default={"empty": True})
    print("Missing file fallback:", missing)
