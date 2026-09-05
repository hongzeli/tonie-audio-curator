import json

from scripts.package_audio import finalize_delivery


def test_finalize_writes_playlist_and_licenses_without_zip(tmp_path):
    delivery = tmp_path / "tonie-01"
    delivery.mkdir()
    audio = delivery / "01-track.mp3"
    audio.write_bytes(b"mp3")
    report = {
        "job_id": "job",
        "summary": {"requested": 1, "downloaded": 1, "processed": 1, "failed": 0, "download_failed": 0},
        "items": [
            {
                "id": 1,
                "title": "Track",
                "status": "processed",
                "output_path": str(audio),
                "duration_seconds": 60,
                "author": "Artist",
                "license": "CC0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "source_page_url": "https://example.org/track",
            }
        ],
    }
    path = tmp_path / "processing-report.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    summary = finalize_delivery(path)

    assert summary["mp3_count"] == 1
    assert summary["zip_created"] is False
    assert (delivery / "playlist.json").is_file()
    assert (delivery / "licenses.txt").is_file()
    assert not list(tmp_path.glob("*.zip"))
