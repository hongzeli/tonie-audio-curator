import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.common import PROJECT_ROOT, read_json, write_json
from scripts.process_audio import AudioProcessingError, process_one, process_report


def setup_job(tmp_path):
    items = []
    for number in (1, 2):
        source = tmp_path / f"{number}.wav"
        source.write_bytes(b"source")
        items.append({"id": number, "title": f"Track {number}", "local_path": str(source),
                      "download_status": "downloaded", "license": "CC0"})
    download = tmp_path / "download.json"
    write_json(download, {"job_id": "job", "items": items})
    profile = tmp_path / "profile.json"
    write_json(profile, read_json(PROJECT_ROOT / "config" / "audio-profile.json"))
    return download, tmp_path / "output", profile


def convert(source, destination, profile):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"converted")
    return {"status": "processed", "output_path": str(destination)}


def test_repeat_run_skips_ffmpeg_and_checkpoints_each_completion(tmp_path):
    args = setup_job(tmp_path)
    from scripts import process_audio

    with (patch("scripts.process_audio.process_one", side_effect=convert) as ffmpeg,
          patch("scripts.process_audio.write_json", wraps=process_audio.write_json) as save):
        first = process_report(*args)
        assert first["summary"]["processed"] == 2
        assert any(call.args[1]["summary"]["pending"] == 1 for call in save.call_args_list)
        second = process_report(*args)
    assert ffmpeg.call_count == 2
    assert second["summary"]["reused"] == 2


def test_interruption_resumes_from_saved_completion(tmp_path):
    args = setup_job(tmp_path)

    def interrupted_save(path, report):
        write_json(path, report)
        if report["summary"]["pending"] == 1:
            raise KeyboardInterrupt

    with (patch("scripts.process_audio.process_one", side_effect=convert),
          patch("scripts.process_audio.write_json", side_effect=interrupted_save),
          pytest.raises(KeyboardInterrupt)):
        process_report(*args)
    saved = read_json(args[1] / "job" / "processing-report.json")
    assert saved["summary"]["processed"] == 1
    with patch("scripts.process_audio.process_one", side_effect=convert) as ffmpeg:
        resumed = process_report(*args)
    assert ffmpeg.call_count == 1
    assert resumed["summary"]["reused"] == 1


@pytest.mark.parametrize("change", ["profile", "source", "missing", "empty", "legacy"])
def test_changed_or_missing_inputs_invalidate_reuse(tmp_path, change):
    args = setup_job(tmp_path)
    with patch("scripts.process_audio.process_one", side_effect=convert) as ffmpeg:
        report = process_report(*args)
        if change == "profile":
            profile = read_json(args[2])
            profile["bitrate_kbps"] = 192
            write_json(args[2], profile)
        elif change == "source":
            (tmp_path / "1.wav").write_bytes(b"changed source")
        elif change == "missing":
            Path(report["items"][0]["output_path"]).unlink()
        elif change == "empty":
            Path(report["items"][0]["output_path"]).write_bytes(b"")
        else:
            for item in report["items"]:
                item.pop("reuse_key")
            write_json(args[1] / "job" / "processing-report.json", report)
        process_report(*args)
    assert ffmpeg.call_count == (4 if change in {"profile", "legacy"} else 3)


def test_timeout_cleans_temp_preserves_old_output_and_other_items_continue(tmp_path):
    args = setup_job(tmp_path)
    destination = args[1] / "job" / "tonie-01" / "01-Track 1.mp3"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old output")
    temporary = destination.with_suffix(".tmp.mp3")

    def run(command, **kwargs):
        output = Path(command[-1])
        output.write_bytes(b"partial")
        if output == temporary:
            raise subprocess.TimeoutExpired(command, 900)
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch("scripts.process_audio.run_command", side_effect=run):
        report = process_report(*args)
    assert report["summary"]["failed"] == 1
    assert report["summary"]["processed"] == 1
    assert "timed out" in report["items"][0]["reason"]
    assert not temporary.exists()
    assert destination.read_bytes() == b"old output"
    with patch("scripts.process_audio.process_one", side_effect=convert) as ffmpeg:
        resumed = process_report(*args)
    assert ffmpeg.call_count == 1
    assert resumed["summary"]["reused"] == 1
    assert resumed["summary"]["processed"] == 2


def test_timeout_is_a_processing_error(tmp_path):
    profile = read_json(PROJECT_ROOT / "config" / "audio-profile.json")
    with (patch("scripts.process_audio.run_command", side_effect=subprocess.TimeoutExpired("ffmpeg", 900)),
          pytest.raises(AudioProcessingError, match="timed out")):
        process_one(tmp_path / "input.wav", tmp_path / "output.mp3", profile)
