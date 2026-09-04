import socket
from unittest.mock import patch

import pytest

from scripts.download_audio import (
    DownloadRejected,
    _looks_like_audio,
    is_public_ip,
    license_allows_download,
    validate_public_url,
)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.1.2.3", "169.254.1.2", "::1", "fc00::1"])
def test_private_and_special_ips_are_rejected(address):
    assert not is_public_ip(address)


def test_public_ip_is_allowed():
    assert is_public_ip("93.184.216.34")


def test_url_credentials_are_rejected():
    with pytest.raises(DownloadRejected):
        validate_public_url("https://user:password@example.com/audio.mp3")


def test_resolved_private_address_is_rejected():
    answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    with patch("socket.getaddrinfo", return_value=answer), pytest.raises(DownloadRejected):
        validate_public_url("https://example.com/audio.mp3")


@pytest.mark.parametrize("value", ["CC0 1.0", "Public Domain", "CC BY 4.0", "CC-BY-NC-SA 4.0"])
def test_explicit_reusable_licenses_are_allowed(value):
    assert license_allows_download(value)


@pytest.mark.parametrize("value", ["unknown", "all rights reserved", "CC BY-ND 4.0", "unclear"])
def test_unknown_or_no_derivative_licenses_are_rejected(value):
    assert not license_allows_download(value)


def test_mime_and_signature_must_both_match():
    assert _looks_like_audio(b"ID3" + b"\0" * 20, "audio/mpeg")
    assert not _looks_like_audio(b"<html>not audio", "audio/mpeg")
    assert not _looks_like_audio(b"ID3" + b"\0" * 20, "text/html")

