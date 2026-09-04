from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import PROJECT_ROOT, read_json, run_command, safe_filename, write_json
except ModuleNotFoundError:
    from common import PROJECT_ROOT, read_json, run_command, safe_filename, write_json


LOUDNORM_JSON = re.compile(r"\{\s*\"input_i\".*?\}", re.DOTALL)
NOISE_FLOOR = re.compile(r"Noise floor dB:\s*(-?(?:inf|\d+(?:\.\d+)?))", re.IGNORECASE)


class AudioProcessingError(RuntimeError):
    pass


def probe_audio(path: Path) -> dict:
    result = run_command(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,format_name:stream=index,codec_type,codec_name,sample_rate,channels",
            "-of", "json", str(path),
        ]
    )
    if result.returncode:
        raise AudioProcessingError(result.stderr.strip() or "ffprobe failed")
    parsed = json.loads(result.stdout)
    streams = [stream for stream in parsed.get("streams", []) if stream.get("codec_type") == "audio"]
    if not streams:
        raise AudioProcessingError("no audio stream found")
    stream = streams[0]
    return {
        "format": parsed.get("format", {}).get("format_name"),
        "duration_seconds": float(parsed.get("format", {}).get("duration", 0)),
        "codec": stream.get("codec_name"),
        "sample_rate_hz": int(stream.get("sample_rate", 0)),
        "channels": int(stream.get("channels", 0)),
    }


def measure_loudness(path: Path, profile: dict) -> dict:
    target_i = profile["integrated_loudness_lufs"]
    target_tp = profile["true_peak_dbtp"]
    target_lra = profile["loudness_range_lu"]
    result = run_command(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=json",
            "-f", "null", "-",
        ]
    )
    matches = LOUDNORM_JSON.findall(result.stderr)
    if result.returncode or not matches:
        raise AudioProcessingError(result.stderr.strip() or "loudnorm measurement failed")
    return json.loads(matches[-1])


def measure_noise_floor(path: Path) -> float | None:
    result = run_command(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", "astats=metadata=0:reset=0", "-f", "null", "-",
        ]
    )
    values = NOISE_FLOOR.findall(result.stderr)
    finite = [float(value) for value in values if value.casefold() != "inf"]
    return max(finite) if finite else None


def process_one(source: Path, destination: Path, item_type: str, profile: dict) -> dict:
    before = probe_audio(source)
    measured = measure_loudness(source, profile)
    noise_floor = measure_noise_floor(source)
    threshold = float(profile["denoise"]["noise_floor_threshold_db"])
    denoise = bool(profile["denoise"]["enabled"] and noise_floor is not None and noise_floor > threshold)

    loudnorm = (
        f"loudnorm=I={profile['integrated_loudness_lufs']}:TP={profile['true_peak_dbtp']}:"
        f"LRA={profile['loudness_range_lu']}:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true:print_format=summary"
    )
    filters = [loudnorm]
    if denoise:
        filters.insert(0, profile["denoise"]["filter"])

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp.mp3")
    command = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(source),
        "-map_metadata", "0", "-vn", "-af", ",".join(filters),
        "-ar", str(profile["sample_rate_hz"]),
    ]
    if item_type in {"story", "educational", "bedtime"} and before["channels"] == 1 and profile["preserve_mono_for_speech"]:
        command.extend(["-ac", "1"])
    else:
        command.extend(["-ac", "2"])
    command.extend(
        [
            "-codec:a", "libmp3lame", "-b:a", f"{profile['bitrate_kbps']}k",
            "-id3v2_version", str(profile["id3_version"]), str(temporary),
        ]
    )
    result = run_command(command, timeout=900)
    if result.returncode:
        temporary.unlink(missing_ok=True)
        raise AudioProcessingError(result.stderr.strip() or "ffmpeg encoding failed")
    temporary.replace(destination)
    after = probe_audio(destination)
    after_loudness = measure_loudness(destination, profile)
    return {
        "source_path": str(source),
        "output_path": str(destination),
        "before": before,
        "after": after,
        "measured_before": measured,
        "measured_after": after_loudness,
        "noise_floor_db": noise_floor,
        "denoise_applied": denoise,
        "filter_chain": filters,
        "status": "processed",
    }


def process_report(download_report_path: Path, output_root: Path, profile_path: Path) -> dict:
    downloads = read_json(download_report_path)
    profile = read_json(profile_path)
    job_id = downloads["job_id"]
    processed_dir = output_root / job_id / "individual-mp3"
    records = []
    for item in downloads["items"]:
        if item["download_status"] != "downloaded":
            continue
        destination = processed_dir / safe_filename(
            f"{item['id']:02d}-{item['title']}", ".mp3", profile["max_filename_chars"]
        )
        try:
            details = process_one(Path(item["local_path"]), destination, item.get("type", "other"), profile)
            details.update(
                id=item["id"], title=item["title"], author=item.get("author"),
                license=item.get("license"), license_url=item.get("license_url"),
                source_page_url=item.get("source_page_url"), sha256=item.get("sha256"),
            )
        except (AudioProcessingError, OSError, ValueError, KeyError) as exc:
            details = {"id": item["id"], "title": item["title"], "status": "failed", "reason": str(exc)}
        records.append(details)
    report = {
        "schema_version": "1.0",
        "job_id": job_id,
        "created_at": datetime.now(UTC).isoformat(),
        "audio_profile": profile,
        "items": records,
        "summary": {
            "processed": sum(record["status"] == "processed" for record in records),
            "failed": sum(record["status"] == "failed" for record in records),
        },
    }
    write_json(output_root / job_id / "processing-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize downloaded audio for Creative-Tonie")
    parser.add_argument("download_report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--profile", type=Path, default=PROJECT_ROOT / "config" / "audio-profile.json")
    args = parser.parse_args()
    report = process_report(args.download_report.resolve(), args.output.resolve(), args.profile.resolve())
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["summary"]["processed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
