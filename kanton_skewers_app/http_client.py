from __future__ import annotations

import json
import ssl
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, Request, build_opener, install_opener, urlopen, urlretrieve

import certifi


class HttpClient:
    """Shared HTTP helper with cert bundle, user-agent, and retry support."""

    def __init__(self, user_agent: str = "kanton-skewers-app/1.0") -> None:
        self._user_agent = user_agent

    def _ssl_context(self) -> ssl.SSLContext:
        return ssl.create_default_context(cafile=certifi.where())

    def install_global_https_opener(self) -> None:
        opener = build_opener(HTTPSHandler(context=self._ssl_context()))
        opener.addheaders = [("User-Agent", self._user_agent)]
        install_opener(opener)

    def _retry_wait_seconds(self, retry_after: str, attempt: int, max_retry_wait_seconds: int) -> int:
        if retry_after.isdigit():
            return min(max_retry_wait_seconds, int(retry_after))

        if retry_after:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                wait_seconds = int((retry_at - datetime.now(timezone.utc)).total_seconds())
                if wait_seconds > 0:
                    return min(max_retry_wait_seconds, wait_seconds)
            except (TypeError, ValueError, OverflowError):
                pass

        return min(max_retry_wait_seconds, 2 * attempt)

    def read_json(
        self,
        url: str,
        timeout_seconds: int = 40,
        max_retries: int = 5,
        max_retry_wait_seconds: int = 30,
    ) -> dict:
        req = Request(url, headers={"User-Agent": self._user_agent})
        for attempt in range(1, max_retries + 1):
            try:
                with urlopen(req, context=self._ssl_context(), timeout=timeout_seconds) as response:
                    return json.load(response)
            except HTTPError as err:
                if err.code == 429 and attempt < max_retries:
                    wait_seconds = self._retry_wait_seconds(
                        retry_after=err.headers.get("Retry-After", ""),
                        attempt=attempt,
                        max_retry_wait_seconds=max_retry_wait_seconds,
                    )
                    print(f"  Rate limited (429), waiting {wait_seconds}s and retrying...")
                    time.sleep(wait_seconds)
                    continue
                raise
            except URLError:
                if attempt < max_retries:
                    wait_seconds = min(max_retry_wait_seconds, 2 * attempt)
                    print(f"  Network error, waiting {wait_seconds}s and retrying...")
                    time.sleep(wait_seconds)
                    continue
                raise

        raise RuntimeError(f"Failed to read JSON after {max_retries} attempts: {url}")

    def download_file_with_retries(
        self,
        url: str,
        target: Path,
        max_retries: int = 5,
        max_retry_wait_seconds: int = 30,
    ) -> None:
        for attempt in range(1, max_retries + 1):
            try:
                urlretrieve(url, target)
                return
            except HTTPError as err:
                if err.code == 429 and attempt < max_retries:
                    wait_seconds = self._retry_wait_seconds(
                        retry_after=err.headers.get("Retry-After", ""),
                        attempt=attempt,
                        max_retry_wait_seconds=max_retry_wait_seconds,
                    )
                    print(f"  Rate limited (429), waiting {wait_seconds}s and retrying...")
                    time.sleep(wait_seconds)
                    continue
                raise
            except URLError:
                if attempt < max_retries:
                    wait_seconds = min(max_retry_wait_seconds, 2 * attempt)
                    print(f"  Network error, waiting {wait_seconds}s and retrying...")
                    time.sleep(wait_seconds)
                    continue
                raise
