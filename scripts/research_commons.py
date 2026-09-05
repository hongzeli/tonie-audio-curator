from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import write_json
    from scripts.download_audio import license_allows_download
except ModuleNotFoundError:
    from common import write_json
    from download_audio import license_allows_download


API_URL = "https://commons.wikimedia.org/w/api.php"
TAG = re.compile(r"<[^>]+>")


def _metadata_value(metadata: dict, key: str) -> str | None:
    value = metadata.get(key, {}).get("value")
    if value is None:
        return None
    return html.unescape(TAG.sub("", str(value))).strip() or None


def parse_candidates(payload: dict, limit: int) -> list[dict]:
    candidates = []
    seen_urls = set()
    for page in payload.get("query", {}).get("pages", []):
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata") or {}
        license_name = _metadata_value(metadata, "LicenseShortName") or "unknown"
        url = info.get("url")
        if not url or url in seen_urls or not license_allows_download(license_name):
            continue
        seen_urls.add(url)
        candidates.append(
            {
                "title": page.get("title", "").removeprefix("File:"),
                "source_name": "Wikimedia Commons",
                "source_page_url": info.get("descriptionurl"),
                "direct_download_url": url,
                "duration_seconds": info.get("duration", "unknown"),
                "author": _metadata_value(metadata, "Artist"),
                "license": license_name,
                "license_url": _metadata_value(metadata, "LicenseUrl"),
                "retrieved_at": datetime.now(UTC).isoformat(),
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def search_commons(query: str, limit: int = 30, timeout: int = 25) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": f"filetype:audio {query}",
        "gsrnamespace": "6",
        "gsrlimit": str(min(50, max(limit * 2, 20))),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
    }
    request = urllib.request.Request(
        f"{API_URL}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "TonieAudioCuratorFast/2.0 (+local-user-tool)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return parse_candidates(json.load(response), limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Save a compact licensed Wikimedia Commons candidate pool")
    parser.add_argument("query", help="One concise search query assembled from the user's request")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates = search_commons(args.query, max(1, min(args.limit, 30)))
    write_json(
        args.output,
        {
            "schema_version": "1.0",
            "query": args.query,
            "created_at": datetime.now(UTC).isoformat(),
            "items": candidates,
        },
    )
    print(json.dumps({"candidate_count": len(candidates), "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0 if candidates else 2


if __name__ == "__main__":
    raise SystemExit(main())
