from __future__ import annotations


class CantonCatalog:
    """Central source of canton metadata and accepted codes."""

    def __init__(self) -> None:
        self._canton_names = {
            "AG": "Aargau",
            "AI": "Appenzell Innerrhoden",
            "AR": "Appenzell Ausserrhoden",
            "BE": "Bern",
            "BL": "Basel-Landschaft",
            "BS": "Basel-Stadt",
            "FR": "Freiburg",
            "GE": "Genf",
            "GL": "Glarus",
            "GR": "Graubuenden",
            "JU": "Jura",
            "LU": "Luzern",
            "NE": "Neuenburg",
            "NW": "Nidwalden",
            "OW": "Obwalden",
            "SG": "St. Gallen",
            "SH": "Schaffhausen",
            "SO": "Solothurn",
            "SZ": "Schwyz",
            "TG": "Thurgau",
            "TI": "Tessin",
            "UR": "Uri",
            "VD": "Waadt",
            "VS": "Wallis",
            "ZG": "Zug",
            "ZH": "Zuerich",
        }

        self._crest_filenames = {
            "AG": "Wappen Aargau matt.svg",
            "AI": "Wappen Appenzell Innerrhoden matt.svg",
            "AR": "Wappen Appenzell Ausserrhoden matt.svg",
            "BE": "Wappen Bern matt.svg",
            "BL": "Wappen Basel-Landschaft matt.svg",
            "BS": "Wappen Basel-Stadt matt.svg",
            "FR": "Wappen Freiburg matt.svg",
            "GE": "Wappen Genf matt.svg",
            "GL": "Wappen Glarus matt.svg",
            "GR": "Wappen Graubünden matt.svg",
            "JU": "Wappen Jura matt.svg",
            "LU": "Wappen Luzern matt.svg",
            "NE": "Wappen Neuenburg matt.svg",
            "NW": "Wappen Nidwalden matt.svg",
            "OW": "Wappen Obwalden matt.svg",
            "SG": "Wappen St. Gallen matt.svg",
            "SH": "Wappen Schaffhausen matt.svg",
            "SO": "Wappen Solothurn matt.svg",
            "SZ": "Wappen Schwyz matt.svg",
            "TG": "Wappen Thurgau matt.svg",
            "TI": "Wappen Tessin matt.svg",
            "UR": "Wappen Uri matt.svg",
            "VD": "Wappen Waadt matt.svg",
            "VS": "Wappen Wallis matt.svg",
            "ZG": "Wappen Zug matt.svg",
            "ZH": "Wappen Zürich matt.svg",
        }

    def canton_names(self) -> dict[str, str]:
        return dict(self._canton_names)

    def valid_codes(self) -> list[str]:
        return sorted(self._canton_names.keys())

    def normalize_codes(self, codes: list[str]) -> list[str]:
        return [code.upper() for code in codes]

    def validate_codes(self, codes: list[str]) -> None:
        invalid = [code for code in self.normalize_codes(codes) if code not in self._canton_names]
        if invalid:
            raise ValueError(
                f"Unknown canton code(s): {', '.join(invalid)}. Valid values: {', '.join(self.valid_codes())}"
            )

    def canton_name(self, code: str) -> str:
        return self._canton_names[code]

    def crest_filenames(self) -> dict[str, str]:
        return dict(self._crest_filenames)
