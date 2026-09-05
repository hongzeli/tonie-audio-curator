import json

from scripts.upload_google_drive import prepare_upload_plan


def test_upload_plan_contains_only_direct_delivery_files(tmp_path):
    delivery = tmp_path / "tonie-01"
    delivery.mkdir()
    (delivery / "01-track.mp3").write_bytes(b"mp3")
    (delivery / "playlist.json").write_text(json.dumps({"items": [{"filename": "01-track.mp3"}]}), encoding="utf-8")
    (delivery / "stale.mp3").write_bytes(b"old")
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


def test_upload_plan_refreshes_files_but_preserves_destination(tmp_path):
    delivery = tmp_path / "tonie-01"
    delivery.mkdir()
    config = tmp_path / "drive.json"
    config.write_text(json.dumps({"delivery_folder_id": "fixed-parent"}), encoding="utf-8")
    playlist = delivery / "playlist.json"
    playlist.write_text(json.dumps({"items": []}), encoding="utf-8")
    first = prepare_upload_plan(tmp_path, config)
    first["destination_id"] = "already-created"
    (tmp_path / "drive-upload-plan.json").write_text(json.dumps(first), encoding="utf-8")
    (delivery / "recovered.mp3").write_bytes(b"mp3")
    playlist.write_text(json.dumps({"items": [{"filename": "recovered.mp3"}]}), encoding="utf-8")
    config.unlink()
    second = prepare_upload_plan(tmp_path, config)
    assert second["destination_name"] == first["destination_name"]
    assert second["destination_id"] == "already-created"
    assert second["target_parent_id"] == "fixed-parent"
    assert [item["file_name"] for item in second["files"]] == ["recovered.mp3", "playlist.json"]
    playlist.write_text(json.dumps({"items": []}), encoding="utf-8")
    assert len(prepare_upload_plan(tmp_path, config)["files"]) == 1
