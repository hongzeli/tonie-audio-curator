from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

try:
    from scripts.common import PROJECT_ROOT, write_json
except ModuleNotFoundError:
    from common import PROJECT_ROOT, write_json


def check_environment(project_root: Path = PROJECT_ROOT) -> dict:
    executables = {}
    for name in ("python", "ffmpeg", "ffprobe", "git", "gh"):
        location = shutil.which(name)
        executables[name] = {"available": location is not None, "path": location}

    packages = {
        name: importlib.util.find_spec(name) is not None
        for name in ("jsonschema", "pytest")
    }
    directories = {}
    for name in ("workspace", "output"):
        path = project_root / name
        path.mkdir(parents=True, exist_ok=True)
        directories[name] = {"exists": path.is_dir(), "path": str(path)}

    required_ok = (
        sys.version_info >= (3, 11)
        and all(executables[name]["available"] for name in ("python", "ffmpeg", "ffprobe"))
        and all(packages.values())
    )
    return {
        "ok": required_ok,
        "python_version": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 11),
        "executables": executables,
        "packages": packages,
        "directories": directories,
        "notices": [
            "GitHub CLI is optional locally but required to create/push the private repository.",
            "Google Drive authentication is provided by the connected Codex plugin, not this script.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Tonie Audio Curator prerequisites")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = check_environment()
    if args.json_output:
        write_json(args.json_output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
