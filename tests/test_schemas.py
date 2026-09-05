import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]


def load_schema(name):
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def recommendation(identifier):
    return {
        "id": identifier,
        "title": f"Item {identifier}",
        "type": "music",
        "language": "instrumental",
        "duration_seconds": 120,
        "age_range": "0+",
        "recommendation_reason": "Recognized work in a gentle recording",
        "source_name": "Example archive",
        "source_page_url": "https://example.org/item",
        "license": "CC0",
        "download_status": "available",
        "safety_tags": ["calm"],
        "reputation": {
            "score": 80,
            "work_evidence": ["Included by an educational institution"],
            "recording_evidence": ["Positive source review"],
            "play_count_signal": "available",
        },
    }


def test_recommendations_accepts_up_to_eight_items():
    validator = Draft202012Validator(load_schema("recommendations.schema.json"))
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "profile": {},
        "items": [recommendation(number) for number in range(1, 9)],
    }
    validator.validate(payload)
    payload["items"].append(recommendation(8))
    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_recommendation_requires_reputation_evidence():
    validator = Draft202012Validator(load_schema("recommendations.schema.json"))
    item = recommendation(1)
    del item["reputation"]
    with pytest.raises(ValidationError):
        validator.validate(
            {
                "schema_version": "1.0",
                "created_at": datetime.now(UTC).isoformat(),
                "profile": {},
                "items": [item],
            }
        )


def test_selection_rejects_unknown_license():
    validator = Draft202012Validator(load_schema("selection.schema.json"))
    payload = {
        "schema_version": "1.0",
        "job_id": "example-job",
        "confirmed_at": datetime.now(UTC).isoformat(),
        "source_recommendations": "workspace/example-job/recommendations.json",
        "items": [
            {
                "id": 1,
                "title": "Example",
                "type": "music",
                "source_page_url": "https://example.org/item",
                "direct_download_url": "https://example.org/item.mp3",
                "license": "unknown",
            }
        ],
    }
    with pytest.raises(ValidationError):
        validator.validate(payload)
