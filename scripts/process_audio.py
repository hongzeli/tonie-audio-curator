from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import PROJECT_ROOT, read_json, run_command, safe_filename, write_json
except ModuleNotFoundError:
    from common import PROJECT_ROOT, read_json, run_command, safe_filename, write_json


class AudioProcessingError(RuntimeError):
    pass


def process_one(source: Path, destination: Path, profile: dict) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp.mp3")
    loudnorm = (
        f"loudnorm=I={profile['integrated_loudness_lufs']}:"
        f"TP={profile['true_peak_dbtp']}:LRA={profile['loudness_range_lu']}"
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-map_metadata",
        "0",
        "-vn",
        "-af",
        loudnorm,
        "-ar",
        str(profile["sample_rate_hz"]),
        "-ac",
        "2",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        f"{profile['bitrate_kbps']}k",
        "-id3v2_version",
        str(profile["id3_version"]),
        str(temporary),
    ]
    result = run_command(command, timeout=900)
    if result.returncode:
        temporary.unlink(missing_ok=True)
        error = next((line for line in reversed(result.stderr.splitlines()) if line.strip()), "ffmpeg failed")
        raise AudioProcessingError(error)
    temporary.replace(destination)
    return {
        "source_path": str(source),
        "output_path": str(destination),
        "status": "processed",
        "normalization_requested": {
            "integrated_loudness_lufs": profile["integrated_loudness_lufs"],
            "true_peak_dbtp": profile["true_peak_dbtp"],
            "loudness_range_lu": profile["loudness_range_lu"],
        },
        "output_verified": False,
    }


def _process_record(item: dict, processed_dir: Path, profile: dict) -> dict:
    destination = processed_dir / safe_filename(
        f"{item['id']:02d}-{item['title']}",
        ".mp3",
        profile["max_filename_chars"],
    )
    try:
        details = process_one(Path(item["local_path"]), destination, profile)
        details.update(
            id=item["id"],
            title=item["title"],
            duration_seconds=item.get("duration_seconds"),
            author=item.get("author"),
            license=item.get("license"),
            license_url=item.get("license_url"),
            source_page_url=item.get("source_page_url"),
        )
        return details
    except (AudioProcessingError, OSError, ValueError, KeyError) as exc:
        return {
            "id": item["id"],
            "title": item["title"],
            "status": "failed",
            "reason": str(exc),
        }


def process_report(download_report_path: Path, output_root: Path, profile_path: Path) -> dict:
    downloads = read_json(download_report_path)
    profile = read_json(profile_path)
    job_id = downloads["job_id"]
    processed_dir = output_root / job_id / "tonie-01"
    workers = max(1, int(os.getenv("TONIE_PROCESS_WORKERS", "2")))
    records: dict[int, dict] = {}

    downloadable = []
    for item in downloads["items"]:
        if item["download_status"] == "downloaded":
            downloadable.append(item)
        else:
            records[item["id"]] = {
                "id": item["id"],
                "title": item["title"],
                "status": "download_failed",
                "reason": item.get("reason"),
            }

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tonie-process") as executor:
        futures: dict[Future[dict], dict] = {
            executor.submit(_process_record, item, processed_dir, profile): item for item in downloadable
        }
        for future in as_completed(futures):
            record = future.result()
            records[record["id"]] = record

    ordered = [records[item["id"]] for item in downloads["items"] if item["id"] in records]
    report = {
        "schema_version": "2.0-fast",
        "job_id": job_id,
        "created_at": datetime.now(UTC).isoformat(),
        "audio_profile": {
            "output_format": "mp3",
            "sample_rate_hz": profile["sample_rate_hz"],
            "bitrate_kbps": profile["bitrate_kbps"],
            "single_pass_loudnorm": True,
            "denoise_enabled": False,
            "input_probed": False,
            "output_verified": False,
        },
        "items": ordered,
        "summary": {
            "requested": len(downloads["items"]),
            "downloaded": len(downloadable),
            "processed": sum(record["status"] == "processed" for record in ordered),
            "failed": sum(record["status"] == "failed" for record in ordered),
            "download_failed": sum(record["status"] == "download_failed" for record in ordered),
        },
    }
    write_json(output_root / job_id / "processing-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert downloaded audio with one FFmpeg pass")
    parser.add_argument("download_report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--profile", type=Path, default=PROJECT_ROOT / "config" / "audio-profile.json")
    args = parser.parse_args()
    report = process_report(args.download_report.resolve(), args.output.resolve(), args.profile.resolve())
    print(json.dumps({"job_id": report["job_id"], **report["summary"]}, ensure_ascii=False))
    return 0 if report["summary"]["processed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
