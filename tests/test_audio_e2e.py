import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.common import write_json
from scripts.package_audio import finalize_delivery
from scripts.process_audio import process_report
from scripts.upload_google_drive import prepare_upload_plan

pytestmark = pytest.mark.e2e


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg is unavailable")
def test_generated_tone_uses_fast_direct_mp3_delivery(tmp_path: Path):
    source = tmp_path / "generated-test-tone.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.5",
            "-c:a",
            "pcm_s16le",
            str(source),
        ],
        check=True,
    )
    root = Path(__file__).resolve().parents[1]
    download_report = tmp_path / "download-report.json"
    write_json(
        download_report,
        {
            "schema_version": "2.0-fast",
            "job_id": "generated-e2e",
            "items": [
                {
                    "id": 1,
                    "title": "Generated test tone",
                    "type": "music",
                    "duration_seconds": 0.5,
                    "source_page_url": "generated-locally",
                    "license": "CC0",
                    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                    "author": "test suite",
                    "download_status": "downloaded",
                    "local_path": str(source),
                }
            ],
        },
    )
    output_root = tmp_path / "output"
    processing = process_report(download_report, output_root, root / "config" / "audio-profile.json")
    assert processing["summary"]["processed"] == 1
    assert processing["audio_profile"]["output_verified"] is False

    job_dir = output_root / "generated-e2e"
    summary = finalize_delivery(job_dir / "processing-report.json")
    config = tmp_path / "drive.json"
    config.write_text(json.dumps({"delivery_folder_id": "test-folder-id"}), encoding="utf-8")
    plan = prepare_upload_plan(job_dir, config)

    assert summary["zip_created"] is False
    assert (job_dir / "tonie-01" / "01-Generated test tone.mp3").is_file()
    assert not list(job_dir.glob("*.zip"))
    assert len(plan["files"]) == 3
