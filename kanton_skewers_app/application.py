from __future__ import annotations

import argparse
from pathlib import Path

from kanton_skewers_app.asset_resolver import AssetResolver
from kanton_skewers_app.canton_catalog import CantonCatalog
from kanton_skewers_app.crest_downloader import CrestDownloader
from kanton_skewers_app.flag_downloader import FlagDownloader
from kanton_skewers_app.http_client import HttpClient
from kanton_skewers_app.kanton_skewers_pdf_generator import KantonSkewersPdfGenerator
from kanton_skewers_app.pdf_motif_renderer import PdfMotifRenderer
from kanton_skewers_app.variant_set_builder import VariantSetBuilder


class Application:
    """Main CLI application for downloading assets and generating PDFs."""

    def __init__(self) -> None:
        catalog = CantonCatalog()
        resolver = AssetResolver()
        renderer = PdfMotifRenderer()
        http_client = HttpClient(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        )

        self._catalog = catalog
        self._generator = KantonSkewersPdfGenerator(catalog=catalog, resolver=resolver, renderer=renderer)
        self._variant_builder = VariantSetBuilder(generator=self._generator)
        self._crest_downloader = CrestDownloader(http_client=http_client, catalog=catalog, output_dir=Path("assets"))
        self._flag_downloader = FlagDownloader(http_client=http_client, catalog=catalog, output_dir=Path("assets"))

    def run(self, argv: list[str] | None = None) -> int:
        parser = self._build_parser()
        args = parser.parse_args(argv)

        if args.command == "download-crests":
            return self._run_download_crests(args)
        if args.command == "download-flags":
            return self._run_download_flags(args)
        if args.command == "generate":
            return self._run_generate(args)
        if args.command == "generate-variants":
            return self._run_generate_variants(args)

        parser.print_help()
        return 1

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Kanton Skewers toolkit (download assets + generate PDFs).")
        subparsers = parser.add_subparsers(dest="command")

        crest_parser = subparsers.add_parser(
            "download-crests",
            help="Download all 26 canton crest assets",
        )
        crest_parser.add_argument("--pause-seconds", type=float, default=0.3)
        crest_parser.add_argument("--max-retries", type=int, default=5)
        crest_parser.add_argument("--no-skip-existing", action="store_true")

        flag_parser = subparsers.add_parser(
            "download-flags",
            help="Download all 26 canton flag assets",
        )
        flag_parser.add_argument("--thumbnail-width-px", type=int, default=640)
        flag_parser.add_argument("--pause-seconds", type=float, default=3.5)
        flag_parser.add_argument(
            "--safe-rate-limit",
            action="store_true",
            help="Use a slower request pace to reduce 429 rate-limit errors",
        )
        flag_parser.add_argument("--thumbnail-max-retries", type=int, default=5)
        flag_parser.add_argument("--download-max-retries", type=int, default=5)
        flag_parser.add_argument("--no-skip-existing", action="store_true")

        generate_parser = subparsers.add_parser("generate", help="Generate one PDF set")
        self._add_generate_arguments(generate_parser)

        variants_parser = subparsers.add_parser(
            "generate-variants",
            help="Generate scaled variants and merge into one PDF",
        )
        self._add_generate_arguments(variants_parser)
        variants_parser.add_argument(
            "--scales",
            default="1,1.5,2,2.5,3,3.5,4,4.5,5,5.5",
            help="Comma-separated scales, e.g. 1,1.5,2,2.5",
        )
        variants_parser.add_argument(
            "--merged-out",
            type=Path,
            default=Path("kanton_skewers_variants_merged.pdf"),
            help="Output path for merged PDF",
        )
        variants_parser.add_argument(
            "--temp-prefix",
            default="kanton_skewers_variant",
            help="Filename prefix for temporary variant files",
        )
        variants_parser.add_argument(
            "--keep-parts",
            action="store_true",
            help="Do not delete temporary per-scale PDFs",
        )

        return parser

    def _add_generate_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("cantons", nargs="+", help="Canton codes, e.g. AG SO ZH SH AI")
        parser.add_argument("--count", type=int, default=1, help="Labels per canton")
        parser.add_argument("--assets", type=Path, default=Path("assets"), help="Asset folder")
        parser.add_argument("--out", type=Path, default=None, help="Output PDF path")
        parser.add_argument(
            "--tab-mm",
            type=float,
            default=15.0,
            help="Fold tab width in mm (kept for compatibility; fold now auto-matches cover width)",
        )
        parser.add_argument("--flag-mm", type=float, default=42.0, help="Visible motif area width in mm")
        parser.add_argument("--height-mm", type=float, default=18.0, help="Strip height in mm")
        parser.add_argument("--margin-mm", type=float, default=10.0, help="Page margin in mm")
        parser.add_argument("--gap-mm", type=float, default=4.0, help="Gap between strips in mm")
        parser.add_argument("--no-frame", action="store_true", help="Disable dashed helper frame")
        parser.add_argument("--motif-mode", choices=["crest", "flag"], default="crest")
        parser.add_argument(
            "--flag-layout",
            choices=["square", "full"],
            default="square",
            help="Flag mode layout: centered square or full motif area",
        )
        parser.add_argument(
            "--flag-fit",
            choices=["contain", "cover"],
            default="cover",
            help="Flag mode fit strategy inside the selected layout",
        )

    def _run_download_crests(self, args: argparse.Namespace) -> int:
        failed = self._crest_downloader.download_all(
            skip_existing=not args.no_skip_existing,
            pause_seconds=args.pause_seconds,
            max_retries=args.max_retries,
        )
        if failed:
            print(f"Completed with failures: {', '.join(failed)}")
            return 1
        print("Done. Assets are in ./assets (files named *_crest.*)")
        return 0

    def _run_download_flags(self, args: argparse.Namespace) -> int:
        pause_seconds = max(args.pause_seconds, 6.0) if args.safe_rate_limit else args.pause_seconds
        failed = self._flag_downloader.download_all(
            skip_existing=not args.no_skip_existing,
            thumbnail_width_px=args.thumbnail_width_px,
            pause_seconds=pause_seconds,
            thumbnail_max_retries=args.thumbnail_max_retries,
            download_max_retries=args.download_max_retries,
        )
        if failed:
            print(f"Completed with failures: {', '.join(failed)}")
            return 1
        print("Done. Assets are in ./assets (files named *_flag.*)")
        return 0

    def _default_generate_out(self, cantons: list[str]) -> Path:
        normalized = self._catalog.normalize_codes(cantons)
        if len(normalized) == 1:
            return Path(f"kanton_skewers_{normalized[0]}.pdf")
        return Path(f"kanton_skewers_{'_'.join(normalized)}.pdf")

    def _run_generate(self, args: argparse.Namespace) -> int:
        out = args.out or self._default_generate_out(args.cantons)
        self._generator.generate(
            codes=args.cantons,
            asset_dir=args.assets,
            out=out,
            count_per_canton=args.count,
            tab_mm=args.tab_mm,
            flag_mm=args.flag_mm,
            height_mm=args.height_mm,
            margin_mm=args.margin_mm,
            gap_mm=args.gap_mm,
            show_text=False,
            show_frame=not args.no_frame,
            motif_mode=args.motif_mode,
            flag_layout=args.flag_layout,
            flag_fit=args.flag_fit,
        )
        print(f"Created PDF: {out}")
        return 0

    def _parse_scales(self, scales_arg: str) -> list[float]:
        values: list[float] = []
        for raw in scales_arg.split(","):
            stripped = raw.strip()
            if not stripped:
                continue
            values.append(float(stripped))

        if not values:
            raise ValueError("No valid scales provided")
        if any(scale <= 0 for scale in values):
            raise ValueError("Scales must be > 0")

        return values

    def _run_generate_variants(self, args: argparse.Namespace) -> int:
        scales = self._parse_scales(args.scales)
        merged_out = args.merged_out
        if merged_out.suffix.lower() != ".pdf":
            merged_out = merged_out.with_suffix(".pdf")

        part_files = self._variant_builder.build(
            codes=args.cantons,
            scales=scales,
            asset_dir=args.assets,
            base_tab_mm=args.tab_mm,
            base_flag_mm=args.flag_mm,
            base_height_mm=args.height_mm,
            margin_mm=args.margin_mm,
            gap_mm=args.gap_mm,
            count_per_canton=args.count,
            show_text=False,
            show_frame=not args.no_frame,
            motif_mode=args.motif_mode,
            flag_layout=args.flag_layout,
            flag_fit=args.flag_fit,
            merged_out=merged_out,
            temp_prefix=args.temp_prefix,
            cleanup_parts=not args.keep_parts,
        )

        print(f"Created merged PDF: {merged_out}")
        if args.keep_parts:
            print("Kept variant files:")
            for path in part_files:
                print(f" - {path}")
        return 0
