from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from pypdf import PdfWriter

from kanton_skewers_app.kanton_skewers_pdf_generator import KantonSkewersPdfGenerator


class VariantSetBuilder:
    """Creates multiple scaled variants and merges them into one PDF."""

    def __init__(self, generator: KantonSkewersPdfGenerator) -> None:
        self._generator = generator

    def build(
        self,
        codes: list[str],
        scales: list[float],
        asset_dir: Path,
        base_tab_mm: float,
        base_flag_mm: float,
        base_height_mm: float,
        bleed_mm: float,
        margin_mm: float,
        gap_mm: float,
        count_per_canton: int,
        show_text: bool,
        show_frame: bool,
        motif_mode: str,
        flag_layout: str,
        flag_fit: str,
        merged_out: Path,
        temp_prefix: str = "variant",
        cleanup_parts: bool = True,
    ) -> list[Path]:
        if not scales:
            raise ValueError("At least one scale is required")

        part_files: list[Path] = []
        skipped_scales: list[float] = []
        for scale in scales:
            scaled_flag_mm = base_flag_mm * scale
            if flag_layout == "square":
                scaled_flag_mm = base_height_mm * scale

            # Fold tab is always enforced to the same width as the cover panel.
            scaled_tab_mm = scaled_flag_mm

            if not self._fits_on_a4(
                tab_mm=scaled_tab_mm,
                flag_mm=scaled_flag_mm,
                height_mm=base_height_mm * scale,
                bleed_mm=bleed_mm,
                margin_mm=margin_mm,
                gap_mm=gap_mm,
            ):
                print(f"Skipping scale {scale}: layout does not fit on A4")
                skipped_scales.append(scale)
                continue

            label = str(scale).replace(".", "_")
            part_path = merged_out.parent / f"{temp_prefix}_x{label}.pdf"
            self._generator.generate(
                codes=codes,
                asset_dir=asset_dir,
                out=part_path,
                count_per_canton=count_per_canton,
                tab_mm=scaled_tab_mm,
                flag_mm=base_flag_mm * scale,
                height_mm=base_height_mm * scale,
                bleed_mm=bleed_mm,
                margin_mm=margin_mm,
                gap_mm=gap_mm,
                show_text=show_text,
                show_frame=show_frame,
                motif_mode=motif_mode,
                flag_layout=flag_layout,
                flag_fit=flag_fit,
            )
            part_files.append(part_path)

        if not part_files:
            if skipped_scales:
                raise ValueError(
                    "No variants fit on A4. Reduce dimensions or use smaller scales. "
                    f"Skipped scales: {', '.join(str(s) for s in skipped_scales)}"
                )
            raise ValueError("No variant files were generated")

        writer = PdfWriter()
        for part_file in part_files:
            writer.append(str(part_file))

        with merged_out.open("wb") as f:
            writer.write(f)

        if cleanup_parts:
            for part_file in part_files:
                part_file.unlink(missing_ok=True)

        return part_files

    def _fits_on_a4(
        self,
        tab_mm: float,
        flag_mm: float,
        height_mm: float,
        bleed_mm: float,
        margin_mm: float,
        gap_mm: float,
    ) -> bool:
        page_w, page_h = landscape(A4)
        margin = margin_mm * mm
        gap = self._effective_strip_gap(gap_mm=gap_mm, bleed_mm=bleed_mm) * mm
        strip_w = (tab_mm + flag_mm) * mm
        strip_h = height_mm * mm

        usable_w = page_w - 2 * margin
        usable_h = page_h - 2 * margin
        cols = int((usable_w + gap) // (strip_w + gap))
        rows = int((usable_h + gap) // (strip_h + gap))
        return cols > 0 and rows > 0

    def _effective_strip_gap(self, gap_mm: float, bleed_mm: float) -> float:
        long_len_mm = bleed_mm * 0.75
        corner_gap_mm = max(0.5, bleed_mm * 0.35)
        min_gap_mm = 2 * (corner_gap_mm + long_len_mm)
        return max(gap_mm, min_gap_mm)
