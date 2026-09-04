import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.common import write_json
from scripts.package_audio import create_package
from scripts.process_audio import process_report
from scripts.upload_google_drive import prepare_upload_manifest

pytestmark = pytest.mark.e2e


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg is unavailable")
def test_generated_public_domain_tone_can_be_normalized(tmp_path: Path):
    source = tmp_path / "generated-test-tone.wav"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5",
            "-c:a", "pcm_s16le", str(source),
        ],
        check=True,
    )
    root = Path(__file__).resolve().parents[1]
    download_report = tmp_path / "download-report.json"
    write_json(
        download_report,
        {
            "schema_version": "1.0",
            "job_id": "generated-e2e",
            "items": [
                {
                    "id": 1,
                    "title": "Generated public-domain test tone",
                    "type": "music",
                    "source_page_url": "generated-locally",
                    "license": "CC0",
                    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                    "author": "Tonie Audio Curator test suite",
                    "sha256": "generated-fixture",
                    "download_status": "downloaded",
                    "local_path": str(source),
                }
            ],
        },
    )
    output_root = tmp_path / "output"
    processing = process_report(download_report, output_root, root / "config" / "audio-profile.json")
    assert processing["summary"] == {"processed": 1, "failed": 0}
    processed = processing["items"][0]
    assert processed["after"]["codec"] == "mp3"
    assert processed["after"]["sample_rate_hz"] == 44100

    job_dir = output_root / "generated-e2e"
    package = create_package(job_dir / "processing-report.json")
    manifest = prepare_upload_manifest(job_dir, target_folder_id="test-folder-id")
    assert package["packages"][0]["item_count"] == 1
    assert Path(package["archive_path"]).is_file()
    assert manifest["target_root_id"] == "test-folder-id"
    assert any(item["relative_path"] == "tonie-audio-package.zip" for item in manifest["files"])
