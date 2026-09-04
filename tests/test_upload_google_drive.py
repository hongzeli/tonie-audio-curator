from scripts.upload_google_drive import verify_readback


def test_readback_requires_every_file_and_exact_size():
    manifest = {"files": [{"relative_path": "tonie-01/01.mp3", "size_bytes": 42}]}
    assert verify_readback(
        manifest,
        [{"relative_path": "tonie-01/01.mp3", "size_bytes": 42, "id": "x", "parent_id": "p"}],
    )["ok"]
    assert not verify_readback(manifest, [])["ok"]
    assert not verify_readback(
        manifest,
        [{"relative_path": "tonie-01/01.mp3", "size_bytes": 41, "id": "x", "parent_id": "p"}],
    )["ok"]

