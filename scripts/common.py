from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
SPACE_RUN = re.compile(r"\s+")
DASH_RUN = re.compile(r"-{2,}")


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def safe_filename(value: str, extension: str = "", max_chars: int = 128) -> str:
    stem = DASH_RUN.sub("-", SPACE_RUN.sub(" ", INVALID_FILENAME.sub("-", value))).strip(" .-") or "audio"
    ext = extension if not extension or extension.startswith(".") else f".{extension}"
    allowed = max(1, max_chars - len(ext))
    stem = stem[:allowed].rstrip(" .-") or "audio"
    return f"{stem}{ext}"


def run_command(args: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
