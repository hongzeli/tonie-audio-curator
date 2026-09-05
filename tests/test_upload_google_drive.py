import json

from scripts.upload_google_drive import prepare_upload_plan


def test_upload_plan_contains_only_direct_delivery_files(tmp_path):
    delivery = tmp_path / "tonie-01"
    delivery.mkdir()
    (delivery / "01-track.mp3").write_bytes(b"mp3")
    (delivery / "playlist.json").write_text("{}", encoding="utf-8")
    (delivery / "licenses.txt").write_text("CC0", encoding="utf-8")
    (tmp_path / "processing-report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "old.zip").write_bytes(b"zip")
    config = tmp_path / "drive.json"
    config.write_text(json.dumps({"delivery_folder_id": "fixed-parent"}), encoding="utf-8")

    plan = prepare_upload_plan(tmp_path, config)

    assert plan["target_parent_id"] == "fixed-parent"
    assert plan["readback_required"] is False
    assert [item["file_name"] for item in plan["files"]] == [
        "01-track.mp3",
        "playlist.json",
        "licenses.txt",
    ]
    assert all(not item["file_name"].endswith(".zip") for item in plan["files"])
