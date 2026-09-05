from scripts.research_commons import parse_candidates


def test_parse_candidates_filters_license_and_returns_compact_metadata():
    payload = {
        "query": {
            "pages": [
                {
                    "title": "File:Gentle.ogg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/gentle.ogg",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Gentle.ogg",
                            "duration": 90,
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY 4.0"},
                                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                                "Artist": {"value": "<b>Artist</b>"},
                            },
                        }
                    ],
                },
                {
                    "title": "File:Restricted.ogg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/restricted.ogg",
                            "extmetadata": {"LicenseShortName": {"value": "All rights reserved"}},
                        }
                    ],
                },
            ]
        }
    }

    items = parse_candidates(payload, 30)

    assert len(items) == 1
    assert items[0]["title"] == "Gentle.ogg"
    assert items[0]["author"] == "Artist"
    assert items[0]["duration_seconds"] == 90
