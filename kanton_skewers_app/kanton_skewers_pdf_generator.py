from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from kanton_skewers_app.asset_resolver import AssetResolver
from kanton_skewers_app.canton_catalog import CantonCatalog
from kanton_skewers_app.pdf_motif_renderer import PdfMotifRenderer


class KantonSkewersPdfGenerator:
    """Generates A4 PDFs with canton skewer-label strips."""

    def __init__(
        self,
        catalog: CantonCatalog,
        resolver: AssetResolver,
        renderer: PdfMotifRenderer,
    ) -> None:
        self._catalog = catalog
        self._resolver = resolver
        self._renderer = renderer

    def generate(
        self,
        codes: list[str],
        asset_dir: Path,
        out: Path,
        count_per_canton: int,
        tab_mm: float,
        flag_mm: float,
        height_mm: float,
        bleed_mm: float,
        margin_mm: float,
        gap_mm: float,
        show_text: bool,
        show_frame: bool,
        motif_mode: str,
        flag_layout: str = "square",
        flag_fit: str = "cover",
    ) -> None:
        normalized_codes = self._catalog.normalize_codes(codes)
        self._catalog.validate_codes(normalized_codes)

        if count_per_canton < 1:
            raise ValueError("count_per_canton must be at least 1")
        if bleed_mm <= 0:
            raise ValueError("bleed_mm must be > 0")
        if motif_mode not in {"crest", "flag"}:
            raise ValueError("motif_mode must be either 'crest' or 'flag'")
        if flag_layout not in {"square", "full"}:
            raise ValueError("flag_layout must be either 'square' or 'full'")
        if flag_fit not in {"contain", "cover"}:
            raise ValueError("flag_fit must be either 'contain' or 'cover'")

        asset_kind = "crest" if motif_mode == "crest" else "flag"

        assets = {
            code: self._resolver.find_asset(asset_dir=asset_dir, code=code, asset_kind=asset_kind)
            for code in normalized_codes
        }

        items: list[str] = []
        for code in normalized_codes:
            items.extend([code] * count_per_canton)

        page_size = landscape(A4)
        page_w, page_h = page_size
        margin = margin_mm * mm
        gap = gap_mm * mm
        flag_w = flag_mm * mm
        strip_h = height_mm * mm
        bleed_tick = bleed_mm * mm
        effective_gap = self._effective_strip_gap(gap=gap, tick=bleed_tick)
        effective_flag_w = strip_h if flag_layout == "square" else flag_w
        tab_w = effective_flag_w
        strip_w = tab_w + effective_flag_w

        usable_w = page_w - 2 * margin
        usable_h = page_h - 2 * margin
        cols = int((usable_w + effective_gap) // (strip_w + effective_gap))
        rows = int((usable_h + effective_gap) // (strip_h + effective_gap))
        per_page = cols * rows

        if per_page <= 0:
            raise ValueError("Layout does not fit on A4. Reduce dimensions.")

        c = canvas.Canvas(str(out), pagesize=page_size)
        c.setTitle(f"Kanton Skewers {' '.join(normalized_codes)}")

        made = 0
        total = len(items)
        while made < total:
            for row in range(rows):
                for col in range(cols):
                    if made >= total:
                        break

                    code = items[made]
                    x = margin + col * (strip_w + effective_gap)
                    y = page_h - margin - strip_h - row * (strip_h + effective_gap)
                    self._draw_strip(
                        c=c,
                        x=x,
                        y=y,
                        code=code,
                        canton_name=self._catalog.canton_name(code),
                        asset=assets[code],
                        tab_w=tab_w,
                        flag_w=effective_flag_w,
                        h=strip_h,
                        bleed_tick=bleed_tick,
                        show_text=show_text,
                        show_frame=show_frame,
                        motif_mode=motif_mode,
                        flag_layout=flag_layout,
                        flag_fit=flag_fit,
                    )
                    made += 1

            c.setFont("Helvetica", 6)
            c.drawString(
                margin,
                5 * mm,
                (
                    f"Cantons: {', '.join(normalized_codes)} | "
                    "cut at corner marks, fold once at the dashed line"
                ),
            )

            if made < total:
                c.showPage()

        c.save()

    def _draw_strip(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        code: str,
        canton_name: str,
        asset: Path,
        tab_w: float,
        flag_w: float,
        h: float,
        bleed_tick: float,
        show_text: bool,
        show_frame: bool,
        motif_mode: str,
        flag_layout: str,
        flag_fit: str,
    ) -> None:
        total_w = tab_w + flag_w
        fold_x = x + tab_w

        self._draw_cut_corner_marks(c=c, x=x, y=y, w=total_w, h=h, tick=bleed_tick)

        if show_frame:
            c.setLineWidth(0.15)
            c.setDash(1, 2)
            c.rect(x, y, total_w, h)

        self._draw_back_panel_guide(c=c, x=x, y=y, w=tab_w, h=h)

        c.setDash()

        if motif_mode == "flag":
            if flag_layout == "square":
                flag_size = min(flag_w, h)
                flag_x = fold_x + (flag_w - flag_size) / 2
                flag_y = y + (h - flag_size) / 2
                self._renderer.draw(c, asset, flag_x, flag_y, flag_size, flag_size, fit=flag_fit)
            else:
                self._renderer.draw(c, asset, fold_x, y, flag_w, h, fit=flag_fit)
            return

        padding = 2 * mm
        motif_size = h - 2 * padding
        if show_text:
            motif_x = fold_x + padding
        else:
            motif_x = fold_x + (flag_w - motif_size) / 2
        motif_y = y + padding

        self._renderer.draw(c, asset, motif_x, motif_y, motif_size, motif_size, fit="contain")

        if show_text:
            text_x = motif_x + motif_size + 1.8 * mm
            c.setFont("Helvetica-Bold", 7)
            c.drawString(text_x, y + h * 0.57, code)
            c.setFont("Helvetica", 5.5)
            c.drawString(text_x, y + h * 0.32, canton_name)

    def _draw_cut_corner_marks(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        w: float,
        h: float,
        tick: float,
    ) -> None:
        long_len = tick * 0.75
        gap = max(0.5 * mm, tick * 0.35)

        c.saveState()
        c.setLineWidth(0.7)
        c.setLineCap(1)
        c.setDash()

        # bottom-left corner (inside directions: +x, +y)
        self._draw_split_corner_mark(c, x, y, inside_dx=1, inside_dy=1, long_len=long_len, gap=gap)
        # bottom-right corner (inside directions: -x, +y)
        self._draw_split_corner_mark(
            c,
            x + w,
            y,
            inside_dx=-1,
            inside_dy=1,
            long_len=long_len,
            gap=gap,
        )
        # top-left corner (inside directions: +x, -y)
        self._draw_split_corner_mark(
            c,
            x,
            y + h,
            inside_dx=1,
            inside_dy=-1,
            long_len=long_len,
            gap=gap,
        )
        # top-right corner (inside directions: -x, -y)
        self._draw_split_corner_mark(
            c,
            x + w,
            y + h,
            inside_dx=-1,
            inside_dy=-1,
            long_len=long_len,
            gap=gap,
        )

        c.restoreState()

    def _draw_split_corner_mark(
        self,
        c: canvas.Canvas,
        cx: float,
        cy: float,
        inside_dx: int,
        inside_dy: int,
        long_len: float,
        gap: float,
    ) -> None:
        # Horizontal outside long segment
        c.line(
            cx - (inside_dx * gap),
            cy,
            cx - (inside_dx * (gap + long_len)),
            cy,
        )
        # Vertical outside long segment
        c.line(
            cx,
            cy - (inside_dy * gap),
            cx,
            cy - (inside_dy * (gap + long_len)),
        )

    def _draw_back_panel_guide(self, c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
        c.saveState()
        c.setLineWidth(0.35)
        c.setDash(2, 2)
        # Dashed outline around the back panel, excluding the fold edge itself.
        c.line(x, y, x + w, y)
        c.line(x, y + h, x + w, y + h)
        c.line(x, y, x, y + h)
        c.restoreState()

    def _effective_strip_gap(self, gap: float, tick: float) -> float:
        long_len = tick * 0.75
        corner_gap = max(0.5 * mm, tick * 0.35)
        min_gap = 2 * (corner_gap + long_len)
        return max(gap, min_gap)
