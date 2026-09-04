from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import read_json, safe_filename, write_json
except ModuleNotFoundError:
    from common import read_json, safe_filename, write_json


def group_in_order(items: list[dict], max_seconds: float = 5400, single_package: bool = False) -> tuple[list[list[dict]], list[dict]]:
    groups: list[list[dict]] = [[]]
    overflow: list[dict] = []
    used = 0.0
    for item in items:
        duration = float(item["after"]["duration_seconds"])
        if duration > max_seconds:
            overflow.append({**item, "overflow_reason": "single item exceeds package duration"})
            continue
        if used + duration > max_seconds:
            if single_package:
                overflow.append({**item, "overflow_reason": "single-package duration limit exceeded"})
                continue
            groups.append([])
            used = 0.0
        groups[-1].append(item)
        used += duration
    return [group for group in groups if group], overflow


def _license_text(items: list[dict]) -> str:
    blocks = []
    for item in items:
        blocks.append(
            "\n".join(
                (
                    f"{item['id']:02d}. {item['title']}",
                    f"Author: {item.get('author') or 'unknown'}",
                    f"Source: {item.get('source_page_url') or 'unknown'}",
                    f"License: {item.get('license') or 'unknown'}",
                    f"License URL: {item.get('license_url') or 'unknown'}",
                    f"Source SHA-256: {item.get('sha256') or 'unknown'}",
                )
            )
        )
    return "\n\n".join(blocks) + "\n"


def create_package(processing_report_path: Path, single_package: bool = False) -> dict:
    report = read_json(processing_report_path)
    job_dir = processing_report_path.parent
    items = [item for item in report["items"] if item["status"] == "processed"]
    limit = float(report["audio_profile"]["max_tonie_duration_seconds"])
    groups, overflow = group_in_order(items, limit, single_package)
    package_summaries = []

    for package_index, group in enumerate(groups, 1):
        package_dir = job_dir / f"tonie-{package_index:02d}"
        package_dir.mkdir(parents=True, exist_ok=True)
        playlist_items = []
        for track_index, item in enumerate(group, 1):
            source = Path(item["output_path"])
            name = safe_filename(f"{track_index:02d}-{item['title']}", ".mp3", 128)
            destination = package_dir / name
            shutil.copy2(source, destination)
            playlist_items.append(
                {
                    "position": track_index,
                    "recommendation_id": item["id"],
                    "title": item["title"],
                    "filename": name,
                    "duration_seconds": item["after"]["duration_seconds"],
                    "source_page_url": item.get("source_page_url"),
                    "license": item.get("license"),
                }
            )
        duration = sum(float(entry["duration_seconds"]) for entry in playlist_items)
        playlist = {
            "schema_version": "1.0",
            "job_id": report["job_id"],
            "package": package_index,
            "duration_seconds": duration,
            "duration_limit_seconds": limit,
            "items": playlist_items,
        }
        write_json(package_dir / "playlist.json", playlist)
        (package_dir / "licenses.txt").write_text(_license_text(group), encoding="utf-8", newline="\n")
        package_summaries.append(
            {"name": package_dir.name, "path": str(package_dir), "duration_seconds": duration, "item_count": len(group)}
        )

    skipped = [item for item in report["items"] if item["status"] != "processed"]
    write_json(job_dir / "overflow-items.json", overflow)
    write_json(job_dir / "skipped-items.json", skipped)
    archive = job_dir / "tonie-audio-package.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(job_dir.rglob("*")):
            if path.is_file() and path != archive and "individual-mp3" not in path.parts:
                bundle.write(path, path.relative_to(job_dir))
    result = {
        "schema_version": "1.0",
        "job_id": report["job_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "packages": package_summaries,
        "overflow_count": len(overflow),
        "skipped_count": len(skipped),
        "archive_path": str(archive),
        "archive_size_bytes": archive.stat().st_size,
    }
    write_json(job_dir / "package-report.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Group normalized MP3s into 90-minute Tonie packages")
    parser.add_argument("processing_report", type=Path)
    parser.add_argument("--single-package", action="store_true")
    args = parser.parse_args()
    result = create_package(args.processing_report.resolve(), args.single_package)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

