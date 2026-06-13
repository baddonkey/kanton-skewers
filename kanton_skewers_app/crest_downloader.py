from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import quote

from kanton_skewers_app.canton_catalog import CantonCatalog
from kanton_skewers_app.http_client import HttpClient


class CrestDownloader:
    """Downloads official canton coat-of-arms assets from Wikimedia Commons."""

    BASE_URL = "https://commons.wikimedia.org/wiki/Special:Redirect/file/"

    def __init__(self, http_client: HttpClient, catalog: CantonCatalog, output_dir: Path | None = None) -> None:
        self._http_client = http_client
        self._catalog = catalog
        self._output_dir = output_dir or Path("assets")

    def download_all(
        self,
        skip_existing: bool = True,
        pause_seconds: float = 0.3,
        max_retries: int = 5,
    ) -> list[str]:
        self._http_client.install_global_https_opener()
        self._output_dir.mkdir(parents=True, exist_ok=True)

        failed: list[str] = []
        for code, filename in self._catalog.crest_filenames().items():
            target = self._output_dir / f"{code}_crest.svg"
            if skip_existing and target.exists():
                print(f"{code}: already exists -> {target}")
                continue

            url = self.BASE_URL + quote(filename)
            print(f"{code}: {filename} -> {target}")
            try:
                self._http_client.download_file_with_retries(url, target, max_retries=max_retries)
            except Exception as err:  # noqa: BLE001
                print(f"  Failed for {code}: {err}")
                failed.append(code)
            time.sleep(pause_seconds)

        return failed
