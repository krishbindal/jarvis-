"""Safe downloads must block redirects to local services and preserve files."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from executor import download_executor as downloads


class FakeResponse:
    def __init__(self, status_code=200, headers=None, chunks=()):
        self.status_code = status_code
        self.headers = headers or {}
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError("HTTP failure")

    def iter_content(self, chunk_size=8192):
        yield from self.chunks


class DownloadSafetyTests(unittest.TestCase):
    def test_redirect_to_loopback_is_blocked(self):
        redirect = FakeResponse(status_code=302, headers={"Location": "http://127.0.0.1:1234/secrets"})
        with (
            patch.object(downloads, "_is_public_host", side_effect=lambda host: host == "example.com"),
            patch.object(downloads.requests, "get", return_value=redirect) as request,
        ):
            result = downloads.download_file("https://example.com/file.txt")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "blocked_redirect")
        self.assertEqual(request.call_count, 1)
        self.assertFalse(request.call_args.kwargs["allow_redirects"])

    def test_redirect_with_missing_location_is_rejected(self):
        with (
            patch.object(downloads, "_is_public_host", return_value=True),
            patch.object(downloads.requests, "get", return_value=FakeResponse(status_code=301)),
        ):
            result = downloads.download_file("https://example.com/file.txt")
        self.assertEqual(result["status"], "invalid_redirect")

    def test_existing_download_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "file.txt").write_bytes(b"original")
            with (
                patch.object(downloads, "DEFAULT_DOWNLOAD_DIR", base),
                patch.object(downloads, "_is_public_host", return_value=True),
                patch.object(downloads.requests, "get", return_value=FakeResponse(chunks=[b"new data"])),
            ):
                result = downloads.download_file("https://example.com/file.txt")
            self.assertTrue(result["success"], result)
            self.assertEqual((base / "file.txt").read_bytes(), b"original")
            self.assertEqual(Path(result["path"]).read_bytes(), b"new data")
            self.assertEqual(result["bytes_written"], 8)
            self.assertEqual(list(base.glob("*.part")), [])

    def test_too_large_download_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            with (
                patch.object(downloads, "DEFAULT_DOWNLOAD_DIR", base),
                patch.object(downloads, "MAX_DOWNLOAD_BYTES", 3),
                patch.object(downloads, "_is_public_host", return_value=True),
                patch.object(downloads.requests, "get", return_value=FakeResponse(chunks=[b"abcd"])),
            ):
                result = downloads.download_file("https://example.com/file.txt")
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "too_large")
            self.assertFalse(list(base.iterdir()), "Partial files must be cleaned up")

    def test_no_credential_urls(self):
        self.assertIn("credentials", downloads._validate_url("https://user:pass@example.com/secret"))

    def test_video_non_youtube_url_is_rejected(self):
        with patch.object(downloads, "_is_public_host", return_value=True), patch.object(downloads.yt_dlp, "YoutubeDL") as downloader:
            result = downloads.download_video("https://example.com/media")
        self.assertFalse(result["success"])
        downloader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
