from __future__ import annotations

from pathlib import Path


class AssetResolver:
    """Resolves canton asset files by code and supported extension priority."""

    def find_asset(self, asset_dir: Path, code: str, asset_kind: str) -> Path:
        if asset_kind not in {"crest", "flag"}:
            raise ValueError("asset_kind must be either 'crest' or 'flag'")

        candidates: list[Path] = []
        for ext in (".svg", ".png", ".jpg", ".jpeg"):
            candidates.append(asset_dir / f"{code}_{asset_kind}{ext}")

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"No asset found for {code} ({asset_kind}). Expected one of: "
            f"{asset_dir / (code + '_' + asset_kind + '.svg')}, .png, .jpg, .jpeg"
        )
