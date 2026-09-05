from __future__ import annotations

import argparse
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import PROJECT_ROOT, read_json, write_json
except ModuleNotFoundError:
    from common import PROJECT_ROOT, read_json, write_json


def prepare_upload_plan(
    job_dir: Path,
    config_path: Path = PROJECT_ROOT / "config" / "google-drive.json",
) -> dict:
    plan_path = job_dir / "drive-upload-plan.json"
    previous = read_json(plan_path) if plan_path.exists() else {}

    parent_id = previous.get("target_parent_id") or read_json(config_path).get("delivery_folder_id")
    if not parent_id:
        raise ValueError("config/google-drive.json must contain delivery_folder_id")

    delivery_dir = job_dir / "tonie-01"
    playlist = read_json(delivery_dir / "playlist.json")
    paths = []
    for item in playlist["items"]:
        path = delivery_dir / item["filename"]
        if path.parent.resolve() != delivery_dir.resolve() or path.suffix.lower() != ".mp3":
            raise ValueError("playlist must reference MP3 files directly in tonie-01")
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.append(path)
    for name in ("playlist.json", "licenses.txt"):
        path = delivery_dir / name
        if path.is_file():
            paths.append(path)

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    plan = {
        **previous,
        "schema_version": "2.0-fast",
        "created_at": previous.get("created_at") or datetime.now(UTC).isoformat(),
        "target_parent_id": parent_id,
        "destination_name": previous.get("destination_name") or f"{timestamp}-{secrets.token_hex(2)}",
        "readback_required": False,
        "files": [
            {
                "local_path": str(path.resolve()),
                "file_name": path.name,
            }
            for path in paths
        ],
    }
    write_json(plan_path, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a compact direct-MP3 Google Drive upload plan")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config" / "google-drive.json")
    args = parser.parse_args()
    plan = prepare_upload_plan(args.job_dir.resolve(), args.config.resolve())
    print(
        json.dumps(
            {
                "destination_name": plan["destination_name"],
                "target_parent_id": plan["target_parent_id"],
                "file_count": len(plan["files"]),
                "readback_required": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if plan["files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
