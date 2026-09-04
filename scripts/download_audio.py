from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.common import PROJECT_ROOT, read_json, safe_filename, write_json
except ModuleNotFoundError:
    from common import PROJECT_ROOT, read_json, safe_filename, write_json

from jsonschema import Draft202012Validator, FormatChecker

ALLOWED_LICENSE_MARKERS = (
    "cc0",
    "public domain",
    "cc by",
    "creative commons attribution",
)
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}
MAX_REDIRECTS = 5


class DownloadRejected(RuntimeError):
    """Raised when a URL or response violates download policy."""


def is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value.split("%", 1)[0])
    return not any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def validate_public_url(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise DownloadRejected("only http/https URLs are allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise DownloadRejected("URL must contain a hostname and no credentials")
    try:
        addresses = {
            entry[4][0]
            for entry in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise DownloadRejected(f"hostname resolution failed: {exc}") from exc
    if not addresses or not all(is_public_ip(address) for address in addresses):
        raise DownloadRejected("URL resolves to a local, private, or reserved address")
    return parsed


def license_allows_download(value: str) -> bool:
    normalized = value.casefold().replace("-", " ")
    if any(marker in normalized for marker in ("no derivatives", "cc by nd", "unknown", "unclear")):
        return False
    return any(marker in normalized for marker in ALLOWED_LICENSE_MARKERS)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass
class FetchResult:
    final_url: str
    content_type: str
    extension: str
    size: int
    sha256: str


def _looks_like_audio(header: bytes, content_type: str) -> bool:
    mp3_frame = len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
    signatures = (
        header.startswith(b"ID3"),
        mp3_frame,
        header.startswith(b"OggS"),
        header.startswith(b"fLaC"),
        header.startswith(b"RIFF") and header[8:12] == b"WAVE",
        len(header) >= 12 and header[4:8] == b"ftyp",
    )
    return content_type in ALLOWED_CONTENT_TYPES and any(signatures)


def fetch_audio(
    url: str,
    destination_stem: Path,
    *,
    max_bytes: int = 500 * 1024 * 1024,
    timeout: int = 120,
) -> tuple[Path, FetchResult]:
    opener = urllib.request.build_opener(NoRedirectHandler())
    current = url
    response = None
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(current)
        request = urllib.request.Request(
            current,
            headers={"User-Agent": "TonieAudioCurator/1.0 (+local-user-tool)"},
        )
        try:
            response = opener.open(request, timeout=timeout)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise
            location = exc.headers.get("Location")
            if not location:
                raise DownloadRejected("redirect response had no Location header") from exc
            current = urllib.parse.urljoin(current, location)
    else:
        raise DownloadRejected("too many redirects")

    assert response is not None
    final_url = response.geturl()
    validate_public_url(final_url)
    content_type = response.headers.get_content_type().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        response.close()
        raise DownloadRejected(f"unsupported MIME type: {content_type}")
    declared = response.headers.get("Content-Length")
    if declared and int(declared) > max_bytes:
        response.close()
        raise DownloadRejected("declared file size exceeds configured limit")

    extension = ALLOWED_CONTENT_TYPES[content_type]
    destination = destination_stem.with_suffix(extension)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{extension}.part")
    digest = hashlib.sha256()
    size = 0
    header = b""
    try:
        with response, temporary.open("wb") as output:
            while chunk := response.read(64 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise DownloadRejected("download exceeded configured size limit")
                if len(header) < 32:
                    header += chunk[: 32 - len(header)]
                digest.update(chunk)
                output.write(chunk)
        if not _looks_like_audio(header, content_type):
            raise DownloadRejected("MIME type and file signature do not identify supported audio")
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination, FetchResult(final_url, content_type, extension, size, digest.hexdigest())


def download_selection(selection_path: Path, workspace_root: Path) -> dict:
    selection = read_json(selection_path)
    schema = read_json(PROJECT_ROOT / "schemas" / "selection.schema.json")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(selection)
    job_id = selection["job_id"]
    job_dir = workspace_root / job_id
    download_dir = job_dir / "downloads"
    records = []
    hashes: dict[str, Path] = {}
    max_bytes = int(os.getenv("TONIE_MAX_DOWNLOAD_BYTES", str(500 * 1024 * 1024)))
    timeout = int(os.getenv("TONIE_READ_TIMEOUT_SECONDS", "120"))

    for item in selection["items"]:
        record = {
            "id": item["id"],
            "title": item["title"],
            "source_page_url": item["source_page_url"],
            "final_download_url": None,
            "author": item.get("author"),
            "license": item.get("license"),
            "license_url": item.get("license_url"),
            "retrieved_at": item.get("retrieved_at"),
            "downloaded_at": None,
            "sha256": None,
            "download_status": None,
            "reason": None,
            "local_path": None,
            "type": item.get("type", "other"),
        }
        if not license_allows_download(str(item.get("license", ""))):
            record.update(download_status="skipped_license_unclear", reason="license is not in the explicit allowlist")
            records.append(record)
            continue
        stem = download_dir / f"{item['id']:02d}-{safe_filename(item['title'], max_chars=100)}"
        try:
            fetched_pair = None
            last_network_error = None
            for attempt in range(3):
                try:
                    fetched_pair = fetch_audio(
                        item["direct_download_url"], stem, max_bytes=max_bytes, timeout=timeout
                    )
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code in {404, 410}:
                        raise FileNotFoundError(f"source returned HTTP {exc.code}") from exc
                    if exc.code < 500 or attempt == 2:
                        raise
                    last_network_error = exc
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last_network_error = exc
                    if attempt == 2:
                        raise
                time.sleep(0.25 * (2**attempt))
            if fetched_pair is None:
                raise last_network_error or RuntimeError("download attempts exhausted")
            path, fetched = fetched_pair
            if fetched.sha256 in hashes:
                path.unlink(missing_ok=True)
                path = hashes[fetched.sha256]
                reason = f"duplicate content; reusing item at {path.name}"
            else:
                hashes[fetched.sha256] = path
                reason = None
            record.update(
                final_download_url=fetched.final_url,
                downloaded_at=datetime.now(UTC).isoformat(),
                sha256=fetched.sha256,
                download_status="downloaded",
                reason=reason,
                local_path=str(path),
                size_bytes=fetched.size,
                content_type=fetched.content_type,
            )
        except DownloadRejected as exc:
            status = "failed_size_limit" if "size" in str(exc) else "failed_invalid_audio"
            record.update(download_status=status, reason=str(exc))
        except FileNotFoundError as exc:
            record.update(download_status="skipped_not_found", reason=str(exc))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            record.update(download_status="failed_network", reason=str(exc))
        records.append(record)

    report = {
        "schema_version": "1.0",
        "job_id": job_id,
        "created_at": datetime.now(UTC).isoformat(),
        "items": records,
        "summary": {
            status: sum(record["download_status"] == status for record in records)
            for status in (
                "downloaded",
                "skipped_not_found",
                "skipped_license_unclear",
                "failed_invalid_audio",
                "failed_network",
                "failed_size_limit",
            )
        },
    }
    write_json(job_dir / "download-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely download confirmed, licensed audio")
    parser.add_argument("selection", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("workspace"))
    args = parser.parse_args()
    report = download_selection(args.selection.resolve(), args.workspace.resolve())
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["summary"]["downloaded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
