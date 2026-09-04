from scripts.common import safe_filename


def test_safe_filename_removes_windows_reserved_characters():
    assert safe_filename('A <bad>: "title"?', ".mp3") == "A -bad- -title.mp3"


def test_safe_filename_respects_character_limit():
    result = safe_filename("a" * 200, ".mp3", 128)
    assert len(result) == 128
    assert result.endswith(".mp3")


def test_safe_filename_never_returns_empty_stem():
    assert safe_filename("...", ".mp3") == "audio.mp3"
