from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import quote, unquote

from kanton_skewers_app.canton_catalog import CantonCatalog
from kanton_skewers_app.http_client import HttpClient


class FlagDownloader:
    """Downloads canton flag assets based on Wikidata P41 and Wikimedia thumbs."""

    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    COMMONS_API = "https://commons.wikimedia.org/w/api.php"
    SPARQL_QUERY = (
        "SELECT ?iso ?flag WHERE { "
        "?canton wdt:P31 wd:Q23058; wdt:P17 wd:Q39; wdt:P300 ?iso; wdt:P41 ?flag. "
        "}"
    )

    def __init__(self, http_client: HttpClient, catalog: CantonCatalog, output_dir: Path | None = None) -> None:
        self._http_client = http_client
        self._catalog = catalog
        self._output_dir = output_dir or Path("assets")

    def _fetch_wikidata_file_urls(self) -> dict[str, str]:
        params = f"format=json&query={quote(self.SPARQL_QUERY)}"
        url = f"{self.SPARQL_ENDPOINT}?{params}"
        data = self._http_client.read_json(url)

        result: dict[str, str] = {}
        for row in data["results"]["bindings"]:
            iso = row["iso"]["value"]
            code = iso.split("-")[-1].upper()
            result[code] = row["flag"]["value"]

        expected = set(self._catalog.valid_codes())
        received = set(result.keys())
        if expected != received:
            missing = sorted(expected - received)
            extra = sorted(received - expected)
            raise RuntimeError(
                f"Wikidata mismatch. Missing: {missing or 'none'}. Extra: {extra or 'none'}."
            )

        return result

    def _file_name_from_file_path_url(self, file_url: str) -> str:
        marker = "/Special:FilePath/"
        if marker not in file_url:
            raise ValueError(f"Unexpected file URL format: {file_url}")
        return unquote(file_url.split(marker, 1)[1])

    def _thumbnail_url(self, filename: str, width_px: int, max_retries: int = 5) -> str:
        params = (
            f"action=query&format=json&titles=File:{quote(filename)}"
            f"&prop=imageinfo&iiprop=url&iiurlwidth={width_px}"
        )
        url = f"{self.COMMONS_API}?{params}"
        data = self._http_client.read_json(url, max_retries=max_retries)

        page = next(iter(data["query"]["pages"].values()))
        image_info = page.get("imageinfo", [])
        if not image_info or "thumburl" not in image_info[0]:
            title = page.get("title", filename)
            raise RuntimeError(f"No thumbnail URL found for {title}")
        return image_info[0]["thumburl"]

    def _existing_asset_path(self, code: str) -> Path | None:
        for ext in (".svg", ".png", ".jpg", ".jpeg"):
            candidate = self._output_dir / f"{code}_flag{ext}"
            if candidate.exists():
                return candidate
        return None

    def download_all(
        self,
        skip_existing: bool = True,
        thumbnail_width_px: int = 640,
        pause_seconds: float = 3.5,
        thumbnail_max_retries: int = 5,
        download_max_retries: int = 5,
    ) -> list[str]:
        self._http_client.install_global_https_opener()
        self._output_dir.mkdir(parents=True, exist_ok=True)

        file_urls = self._fetch_wikidata_file_urls()
        failed: list[str] = []

        for code in sorted(file_urls):
            existing = self._existing_asset_path(code)
            if skip_existing and existing is not None:
                print(f"{code}: already exists -> {existing}")
                continue

            file_url = file_urls[code]
            filename = self._file_name_from_file_path_url(file_url)
            target = self._output_dir / f"{code}_flag.png"

            try:
                thumb_url = self._thumbnail_url(
                    filename,
                    width_px=thumbnail_width_px,
                    max_retries=thumbnail_max_retries,
                )
                print(f"{code}: {filename} -> {target}")
                self._http_client.download_file_with_retries(
                    thumb_url,
                    target,
                    max_retries=download_max_retries,
                    max_retry_wait_seconds=5,
                )
            except Exception as err:  # noqa: BLE001
                print(f"  Failed for {code}: {err}")
                failed.append(code)
            finally:
                time.sleep(pause_seconds)

        return failed
