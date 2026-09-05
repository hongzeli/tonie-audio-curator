from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import read_json, write_json
except ModuleNotFoundError:
    from common import read_json, write_json


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
                )
            )
        )
    return "\n\n".join(blocks) + "\n"


def finalize_delivery(processing_report_path: Path) -> dict:
    report = read_json(processing_report_path)
    job_dir = processing_report_path.parent
    delivery_dir = job_dir / "tonie-01"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    processed = [item for item in report["items"] if item["status"] == "processed"]

    playlist_items = []
    for position, item in enumerate(processed, 1):
        output = Path(item["output_path"])
        playlist_items.append(
            {
                "position": position,
                "recommendation_id": item["id"],
                "title": item["title"],
                "filename": output.name,
                "duration_seconds": item.get("duration_seconds", "unknown"),
                "source_page_url": item.get("source_page_url"),
                "license": item.get("license"),
            }
        )

    playlist = {
        "schema_version": "2.0-fast",
        "job_id": report["job_id"],
        "duration_limit_checked": False,
        "items": playlist_items,
    }
    write_json(delivery_dir / "playlist.json", playlist)
    (delivery_dir / "licenses.txt").write_text(_license_text(processed), encoding="utf-8", newline="\n")

    summary = {
        "schema_version": "2.0-fast",
        "job_id": report["job_id"],
        "created_at": datetime.now(UTC).isoformat(),
        **report["summary"],
        "delivery_dir": str(delivery_dir.resolve()),
        "mp3_count": len(processed),
        "zip_created": False,
        "duration_limit_checked": False,
        "input_audio_verified": False,
        "output_audio_verified": False,
        "drive_readback_verified": False,
    }
    write_json(job_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Create playlist and license files without ZIP packaging")
    parser.add_argument("processing_report", type=Path)
    args = parser.parse_args()
    result = finalize_delivery(args.processing_report.resolve())
    print(
        json.dumps(
            {
                "job_id": result["job_id"],
                "mp3_count": result["mp3_count"],
                "failed": result["failed"] + result["download_failed"],
                "delivery_dir": result["delivery_dir"],
                "zip_created": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["mp3_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
