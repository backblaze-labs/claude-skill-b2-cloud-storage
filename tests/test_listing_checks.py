from __future__ import annotations

import contextlib
import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import check_listings
import check_listings_api
import listing_catalog
import pytest


class _OversizedAndSlowHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/large":
            body = b"x" * 2048
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)
            return

        if self.path == "/slow":
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                for _ in range(10):
                    self.wfile.write(b"1\r\nx\r\n")
                    self.wfile.flush()
                    time.sleep(0.05)
                self.wfile.write(b"0\r\n\r\n")
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def local_probe_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OversizedAndSlowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_http_get_rejects_oversized_response(local_probe_server: str) -> None:
    with pytest.raises(check_listings_api.ResponseTooLarge):
        check_listings_api._http_get(
            f"{local_probe_server}/large",
            max_bytes=1024,
            timeout=1,
            total_timeout=1,
        )


def test_http_get_enforces_total_read_deadline(local_probe_server: str) -> None:
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        check_listings_api._http_get(
            f"{local_probe_server}/slow",
            max_bytes=4096,
            timeout=1,
            total_timeout=0.12,
        )
    assert time.monotonic() - started < 1


def test_github_metadata_retries_before_succeeding(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def fake_http_get(*_args: object, **_kwargs: object) -> tuple[int, str, dict[str, str]]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return 503, "", {}
        return (
            200,
            json.dumps(
                {
                    "topics": list(check_listings_api.EXPECTED_TOPICS),
                    "stargazers_count": 1,
                    "forks_count": 0,
                    "archived": False,
                    "default_branch": "main",
                    "description": "test repo",
                }
            ),
            {},
        )

    monkeypatch.setattr(check_listings_api, "_http_get", fake_http_get)
    monkeypatch.setattr(check_listings_api.time, "sleep", lambda _seconds: None)

    result = check_listings_api.check_github_repo(backoff_seconds=(0.0, 0.0))

    assert attempts == 3
    assert result.status == "live"
    assert result.extras["attempts"] == 3


def test_strict_topic_failures_include_metadata_errors() -> None:
    result = check_listings_api.Result(
        "GitHub repo metadata",
        "https://api.github.com/repos/example/repo",
        "error",
        detail="GitHub metadata unavailable: HTTP 503",
    )

    assert check_listings_api.strict_topic_failures([result]) == [
        "GitHub metadata unavailable: HTTP 503"
    ]


def test_probes_are_derived_from_shared_catalog() -> None:
    assert check_listings_api.TEXT_PROBES == listing_catalog.HTTP_PROBES
    assert check_listings.PROBES == listing_catalog.BROWSER_PROBES


def test_only_filter_accepts_documented_partial_name() -> None:
    probes = check_listings.filter_probes(check_listings.PROBES, ["LobeHub"])

    assert [probe.name for probe in probes] == ["LobeHub Skills"]


class _FakeResponse:
    status: int = 200


class _FakePage:
    def goto(self, *_args: object, **_kwargs: object) -> _FakeResponse:
        return _FakeResponse()

    def wait_for_load_state(self, *_args: object, **_kwargs: object) -> None:
        return None

    def inner_text(self, *_args: object, **_kwargs: object) -> str:
        return "claude-skill-b2-cloud-storage"

    def screenshot(self, *, path: str, full_page: bool) -> None:
        assert full_page is True
        Path(path).write_bytes(b"png")


def test_screenshot_path_is_safe_for_probe_names_with_slashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check_listings, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_listings, "SCREENSHOT_DIR", tmp_path / "screens")
    probe = listing_catalog.BrowserProbeSpec(
        "owner/name",
        "https://example.com",
        match_terms=("claude-skill-b2-cloud-storage",),
    )

    result = check_listings.run_probe(_FakePage(), probe, save_screenshots=True)

    assert result.screenshot is not None
    assert result.screenshot == "screens/owner_name.png"
    assert (tmp_path / result.screenshot).read_bytes() == b"png"
