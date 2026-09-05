from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts.common import PROJECT_ROOT, read_json, safe_filename, write_json
except ModuleNotFoundError:
    from common import PROJECT_ROOT, read_json, safe_filename, write_json


ALLOWED_LICENSE_MARKERS = (
    "cc0",
    "public domain",
    "cc by",
    "creative commons attribution",
)


class DownloadTooLarge(RuntimeError):
    """Raised when a download exceeds the configured byte limit."""


@dataclass
class FetchResult:
    final_url: str
    size: int


def license_allows_download(value: str) -> bool:
    normalized = value.casefold().replace("-", " ")
    if any(marker in normalized for marker in ("no derivatives", "cc by nd", "unknown", "unclear")):
        return False
    return any(marker in normalized for marker in ALLOWED_LICENSE_MARKERS)


def _extension_from_url(url: str) -> str:
    suffix = Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).suffix
    if 1 < len(suffix) <= 10 and suffix[1:].isalnum():
        return suffix.casefold()
    return ".audio"


def fetch_audio(
    url: str,
    destination_stem: Path,
    *,
    max_bytes: int = 250 * 1024 * 1024,
    timeout: int = 25,
) -> tuple[Path, FetchResult]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TonieAudioCuratorFast/2.0 (+local-user-tool)"},
    )
    response = urllib.request.urlopen(request, timeout=timeout)  # noqa: S310
    final_url = response.geturl()
    declared = response.headers.get("Content-Length")
    if declared and int(declared) > max_bytes:
        response.close()
        raise DownloadTooLarge("declared file size exceeds configured limit")

    extension = _extension_from_url(final_url)
    destination = Path(f"{destination_stem}{extension}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{destination}.part")
    size = 0
    try:
        with response, temporary.open("wb") as output:
            while chunk := response.read(256 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise DownloadTooLarge("download exceeded configured size limit")
                output.write(chunk)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination, FetchResult(final_url=final_url, size=size)


def _base_record(item: dict) -> dict:
    return {
        "id": item["id"],
        "title": item["title"],
        "type": item.get("type", "other"),
        "duration_seconds": item.get("duration_seconds"),
        "source_page_url": item["source_page_url"],
        "final_download_url": None,
        "author": item.get("author"),
        "license": item.get("license"),
        "license_url": item.get("license_url"),
        "downloaded_at": None,
        "download_status": None,
        "reason": None,
        "local_path": None,
        "size_bytes": None,
    }


def _download_one(item: dict, download_dir: Path, max_bytes: int, timeout: int, attempts: int) -> dict:
    record = _base_record(item)
    if not license_allows_download(str(item.get("license", ""))):
        record.update(download_status="skipped_license_unclear", reason="license is not in the allowlist")
        return record

    stem = download_dir / f"{item['id']:02d}-{safe_filename(item['title'], max_chars=100)}"
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            path, fetched = fetch_audio(
                item["direct_download_url"],
                stem,
                max_bytes=max_bytes,
                timeout=timeout,
            )
            record.update(
                final_download_url=fetched.final_url,
                downloaded_at=datetime.now(UTC).isoformat(),
                download_status="downloaded",
                local_path=str(path),
                size_bytes=fetched.size,
            )
            return record
        except urllib.error.HTTPError as exc:
            if exc.code in {404, 410}:
                record.update(download_status="skipped_not_found", reason=f"source returned HTTP {exc.code}")
                return record
            last_error = exc
            if exc.code != 429 and exc.code < 500:
                break
        except DownloadTooLarge as exc:
            record.update(download_status="failed_size_limit", reason=str(exc))
            return record
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(0.5 * (2**attempt))

    record.update(download_status="failed_network", reason=str(last_error or "download failed"))
    return record


def _build_report(job_id: str, ordered_items: list[dict], records: dict[int, dict]) -> dict:
    statuses = (
        "downloaded",
        "skipped_not_found",
        "skipped_license_unclear",
        "failed_network",
        "failed_size_limit",
    )
    items = [records[item["id"]] for item in ordered_items if item["id"] in records]
    return {
        "schema_version": "2.0-fast",
        "job_id": job_id,
        "updated_at": datetime.now(UTC).isoformat(),
        "items": items,
        "summary": {status: sum(record["download_status"] == status for record in items) for status in statuses},
        "pending": len(ordered_items) - len(items),
        "verification": {
            "public_url_checked": False,
            "mime_or_signature_checked": False,
            "sha256_computed": False,
        },
    }


def download_selection(selection_path: Path, workspace_root: Path) -> dict:
    selection = read_json(selection_path)
    schema = read_json(PROJECT_ROOT / "schemas" / "selection.schema.json")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(selection)
    job_id = selection["job_id"]
    job_dir = workspace_root / job_id
    download_dir = job_dir / "downloads"
    report_path = job_dir / "download-report.json"

    records: dict[int, dict] = {}
    if report_path.exists():
        for record in read_json(report_path).get("items", []):
            path = Path(record.get("local_path") or "")
            if record.get("download_status") == "downloaded" and path.is_file() and path.stat().st_size > 0:
                records[record["id"]] = record

    for item in selection["items"]:
        if item["id"] in records:
            continue
        stem = f"{item['id']:02d}-{safe_filename(item['title'], max_chars=100)}"
        recovered = next(
            (
                path
                for path in sorted(download_dir.glob(f"{stem}.*"))
                if path.is_file() and not path.name.endswith(".part") and path.stat().st_size > 0
            ),
            None,
        )
        if recovered:
            record = _base_record(item)
            record.update(
                download_status="downloaded",
                local_path=str(recovered),
                size_bytes=recovered.stat().st_size,
                reason="recovered existing file without content verification",
            )
            records[item["id"]] = record

    max_bytes = int(os.getenv("TONIE_MAX_DOWNLOAD_BYTES", str(250 * 1024 * 1024)))
    timeout = int(os.getenv("TONIE_READ_TIMEOUT_SECONDS", "25"))
    attempts = max(1, int(os.getenv("TONIE_DOWNLOAD_ATTEMPTS", "3")))
    workers = max(1, int(os.getenv("TONIE_DOWNLOAD_WORKERS", "4")))
    pending = [item for item in selection["items"] if item["id"] not in records]

    write_json(report_path, _build_report(job_id, selection["items"], records))
    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tonie-download")
    futures: dict[Future[dict], dict] = {
        executor.submit(_download_one, item, download_dir, max_bytes, timeout, attempts): item for item in pending
    }
    try:
        for future in as_completed(futures):
            record = future.result()
            records[record["id"]] = record
            write_json(report_path, _build_report(job_id, selection["items"], records))
    except KeyboardInterrupt:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=True)

    report = _build_report(job_id, selection["items"], records)
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Quickly download confirmed, licensed audio with checkpoints")
    parser.add_argument("selection", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("workspace"))
    args = parser.parse_args()
    report = download_selection(args.selection.resolve(), args.workspace.resolve())
    print(json.dumps({"job_id": report["job_id"], **report["summary"], "pending": report["pending"]}, ensure_ascii=False))
    return 0 if report["summary"]["downloaded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
