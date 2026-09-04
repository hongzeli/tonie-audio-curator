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
        "type": "story",
        "language": "de",
        "duration_seconds": 120,
        "age_range": "4-6",
        "recommendation_reason": "Age appropriate",
        "source_name": "Example archive",
        "source_page_url": "https://example.org/item",
        "license": "CC0",
        "download_status": "available",
        "safety_tags": [],
    }


def test_recommendations_requires_exactly_twenty_items():
    validator = Draft202012Validator(load_schema("recommendations.schema.json"))
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "profile": {},
        "items": [recommendation(number) for number in range(1, 21)],
    }
    validator.validate(payload)
    payload["items"].pop()
    with pytest.raises(ValidationError):
        validator.validate(payload)


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
                "type": "story",
                "source_page_url": "https://example.org/item",
                "direct_download_url": "https://example.org/item.mp3",
                "license": "unknown",
            }
        ],
    }
    with pytest.raises(ValidationError):
        validator.validate(payload)

