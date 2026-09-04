from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import write_json
except ModuleNotFoundError:
    from common import write_json


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_upload_manifest(
    job_dir: Path,
    target_folder_name: str = "Chatgpt工作区",
    target_folder_id: str | None = None,
) -> dict:
    allowed_names = {
        "tonie-audio-package.zip",
        "processing-report.json",
        "package-report.json",
        "overflow-items.json",
        "skipped-items.json",
    }
    files = []
    for path in sorted(job_dir.rglob("*")):
        relative = path.relative_to(job_dir)
        deliverable = (
            path.is_file()
            and (
                path.name in allowed_names
                or "individual-mp3" in relative.parts
                or any(part.startswith("tonie-") for part in relative.parts)
            )
        )
        if deliverable:
            files.append(
                {
                    "local_path": str(path.resolve()),
                    "relative_path": relative.as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "target_root_name": target_folder_name,
        "target_root_id": target_folder_id,
        "target_relative_folder": f"Tonie Audio/{job_dir.name}",
        "destination_folder_id": None,
        "rules": {
            "require_unique_target_root": True,
            "change_permissions": False,
            "overwrite_existing": False,
            "verify_by_readback": True,
        },
        "files": files,
    }
    write_json(job_dir / "drive-upload-manifest.json", manifest)
    return manifest


def verify_readback(manifest: dict, remote_items: list[dict]) -> dict:
    remote = {item["relative_path"]: item for item in remote_items}
    expected_parent_id = manifest.get("destination_folder_id")
    checks = []
    for expected in manifest["files"]:
        actual = remote.get(expected["relative_path"])
        checks.append(
            {
                "relative_path": expected["relative_path"],
                "ok": bool(
                    actual
                    and int(actual.get("size_bytes", -1)) == expected["size_bytes"]
                    and (not expected_parent_id or actual.get("parent_id") == expected_parent_id)
                ),
                "expected_size_bytes": expected["size_bytes"],
                "actual_size_bytes": actual.get("size_bytes") if actual else None,
                "remote_id": actual.get("id") if actual else None,
                "parent_id": actual.get("parent_id") if actual else None,
            }
        )
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or verify a Google Drive plugin upload (this script never handles credentials)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("job_dir", type=Path)
    prepare.add_argument("--target-folder-id")
    verify = subparsers.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("remote_listing", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_upload_manifest(args.job_dir.resolve(), target_folder_id=args.target_folder_id)
    else:
        result = verify_readback(
            json.loads(args.manifest.read_text(encoding="utf-8")),
            json.loads(args.remote_listing.read_text(encoding="utf-8")),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
