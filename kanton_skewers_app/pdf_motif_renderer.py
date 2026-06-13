from __future__ import annotations

from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

try:
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg
except ImportError:
    renderPDF = None
    svg2rlg = None


class PdfMotifRenderer:
    """Draws raster or SVG motifs into reportlab canvases."""

    def draw(self, c: canvas.Canvas, path: Path, x: float, y: float, w: float, h: float, fit: str = "contain") -> None:
        if path.suffix.lower() == ".svg":
            self._draw_svg(c, path, x, y, w, h, fit=fit)
        else:
            self._draw_image(c, path, x, y, w, h, fit=fit)

    def _draw_svg(
        self,
        c: canvas.Canvas,
        path: Path,
        x: float,
        y: float,
        w: float,
        h: float,
        fit: str,
    ) -> None:
        if svg2rlg is None or renderPDF is None:
            raise RuntimeError("SVG support is missing. Install dependencies via requirements.txt")

        drawing = svg2rlg(str(path))
        if drawing is None:
            raise RuntimeError(f"Could not load SVG: {path}")

        if fit == "cover":
            scale = max(w / drawing.width, h / drawing.height)
        else:
            scale = min(w / drawing.width, h / drawing.height)

        draw_w = drawing.width * scale
        draw_h = drawing.height * scale

        c.saveState()
        if fit == "cover":
            clip = c.beginPath()
            clip.rect(x, y, w, h)
            c.clipPath(clip, stroke=0, fill=0)

        c.translate(x + (w - draw_w) / 2, y + (h - draw_h) / 2)
        c.scale(scale, scale)
        renderPDF.draw(drawing, c, 0, 0)
        c.restoreState()

    def _draw_image(
        self,
        c: canvas.Canvas,
        path: Path,
        x: float,
        y: float,
        w: float,
        h: float,
        fit: str,
    ) -> None:
        img = ImageReader(str(path))
        iw, ih = img.getSize()

        if fit == "cover":
            scale = max(w / iw, h / ih)
        else:
            scale = min(w / iw, h / ih)

        draw_w = iw * scale
        draw_h = ih * scale

        c.saveState()
        if fit == "cover":
            clip = c.beginPath()
            clip.rect(x, y, w, h)
            c.clipPath(clip, stroke=0, fill=0)

        c.drawImage(
            img,
            x + (w - draw_w) / 2,
            y + (h - draw_h) / 2,
            width=draw_w,
            height=draw_h,
            mask="auto",
        )
        c.restoreState()
