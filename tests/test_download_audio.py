import json
from unittest.mock import patch

import pytest

from scripts.download_audio import _extension_from_url, download_selection, license_allows_download


@pytest.mark.parametrize("value", ["CC0 1.0", "Public Domain", "CC BY 4.0", "CC-BY-NC-SA 4.0"])
def test_explicit_reusable_licenses_are_allowed(value):
    assert license_allows_download(value)


@pytest.mark.parametrize("value", ["unknown", "all rights reserved", "CC BY-ND 4.0", "unclear"])
def test_unknown_or_no_derivative_licenses_are_rejected(value):
    assert not license_allows_download(value)


def test_extension_is_taken_from_url_without_mime_probe():
    assert _extension_from_url("https://example.org/music/track.OGG?download=1") == ".ogg"
    assert _extension_from_url("https://example.org/download/42") == ".audio"


def _selection():
    return {
        "schema_version": "1.0",
        "job_id": "job",
        "confirmed_at": "2026-09-05T00:00:00Z",
        "source_recommendations": "manual-confirmation",
        "items": [
            {
                "id": 1,
                "title": "Track",
                "type": "music",
                "duration_seconds": 60,
                "source_page_url": "https://example.org/track",
                "direct_download_url": "https://example.org/track.ogg",
                "author": "Artist",
                "license": "CC0 1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            }
        ],
    }


def test_download_selection_reuses_nonempty_previous_download_without_hash(tmp_path):
    audio = tmp_path / "workspace" / "job" / "downloads" / "01-track.ogg"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"existing bytes")
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(_selection()), encoding="utf-8")
    report_path = tmp_path / "workspace" / "job" / "download-report.json"
    report_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": 1,
                        "title": "Track",
                        "download_status": "downloaded",
                        "local_path": str(audio),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with patch("scripts.download_audio._download_one") as download:
        report = download_selection(selection_path, tmp_path / "workspace")

    download.assert_not_called()
    assert report["summary"]["downloaded"] == 1
    assert report["verification"]["sha256_computed"] is False


def test_download_selection_writes_incremental_checkpoint(tmp_path):
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(_selection()), encoding="utf-8")
    completed = {
        "id": 1,
        "title": "Track",
        "download_status": "downloaded",
        "local_path": str(tmp_path / "track.ogg"),
    }

    from scripts import download_audio

    real_write = download_audio.write_json
    with (
        patch("scripts.download_audio._download_one", return_value=completed),
        patch("scripts.download_audio.write_json", wraps=real_write) as write,
    ):
        report = download_selection(selection_path, tmp_path / "workspace")

    assert write.call_count >= 3
    assert report["pending"] == 0


def test_download_selection_recovers_finished_file_without_report(tmp_path):
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(_selection()), encoding="utf-8")
    audio = tmp_path / "workspace" / "job" / "downloads" / "01-Track.ogg"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"finished before interruption")

    with patch("scripts.download_audio._download_one") as download:
        report = download_selection(selection_path, tmp_path / "workspace")

    download.assert_not_called()
    assert report["summary"]["downloaded"] == 1
    assert report["items"][0]["reason"] == "recovered existing file without content verification"
