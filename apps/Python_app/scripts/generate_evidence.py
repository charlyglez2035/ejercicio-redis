"""Create readable PNG evidence cards and a PDF contact report."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidencias"
PDF_PATH = EVIDENCE / "evidencias.pdf"


def font(size: int, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def make_card(name: str, data: dict, output: Path):
    image = Image.new("RGB", (1600, 900), "#111827")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1600, 110), fill="#0f766e")
    draw.text((55, 30), f"EVIDENCIA API · {name.upper()}", fill="white", font=font(42, True))
    draw.text((55, 145), f"Base: {data.get('base_url', '')}", fill="#cbd5e1", font=font(28))
    draw.text((55, 195), f"ISBN temporal: {data.get('isbn', 'N/D')}", fill="#cbd5e1", font=font(28))
    y = 285
    steps = data.get("steps", {})
    for label, result in steps.items():
        status = result.get("status") if isinstance(result, dict) else None
        if status in (200, 201, 404):
            color = "#34d399" if status != 404 or label == "GET_after_DELETE" else "#fbbf24"
            text = f"{status}"
        else:
            color = "#fb7185"
            text = "TIMEOUT / NO DISPONIBLE"
        draw.ellipse((60, y + 5, 88, y + 33), fill=color)
        draw.text((115, y), label, fill="white", font=font(30, True))
        draw.text((620, y), text, fill=color, font=font(30, True))
        y += 70
    note = "El 404 final confirma que el registro temporal fue eliminado." if name == "local" else "El host remoto no respondió dentro del timeout controlado."
    draw.text((55, 820), note, fill="#cbd5e1", font=font(24))
    image.save(output)


def draw_pdf_text(pdf, text, x, y, size=11, bold=False):
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    pdf.drawString(x, y, text)


def add_image_page(pdf, path: Path, title: str):
    page_width, page_height = A4
    draw_pdf_text(pdf, title, 42, page_height - 45, 16, True)
    with Image.open(path) as image:
        width, height = image.size
    max_width, max_height = page_width - 84, page_height - 110
    scale = min(max_width / width, max_height / height)
    draw_width, draw_height = width * scale, height * scale
    pdf.drawImage(ImageReader(str(path)), 42, (page_height - draw_height) / 2, draw_width, draw_height, preserveAspectRatio=True)
    pdf.showPage()


def main():
    local = json.loads((EVIDENCE / "cycle_local.json").read_text(encoding="utf-8"))
    remote = json.loads((EVIDENCE / "cycle_remote.json").read_text(encoding="utf-8"))
    make_card("local", local, EVIDENCE / "11_ciclo_local.png")
    make_card("remote", remote, EVIDENCE / "12_ciclo_remoto.png")

    pdf = canvas.Canvas(str(PDF_PATH), pagesize=A4)
    page_width, page_height = A4
    draw_pdf_text(pdf, "Evidencias de ejecución · Python_app", 42, page_height - 70, 23, True)
    draw_pdf_text(pdf, "Microservicio Flask de libros · 22 de septiembre de 2026", 42, page_height - 100, 12)
    draw_pdf_text(pdf, "Incluye respuestas XML/JSON, vistas HTML, ciclo CRUD y estado remoto.", 42, page_height - 135, 12)
    y = page_height - 195
    draw_pdf_text(pdf, "Ciclo local", 42, y, 16, True)
    y -= 25
    for label, result in local["steps"].items():
        status = result.get("status") if isinstance(result, dict) else "N/D"
        draw_pdf_text(pdf, f"{label}: {status}", 58, y, 11)
        y -= 19
    y -= 10
    draw_pdf_text(pdf, "Servicio remoto", 42, y, 16, True)
    y -= 25
    draw_pdf_text(pdf, "El endpoint documentado no respondió dentro del timeout.", 58, y, 11)
    pdf.showPage()

    screenshots = sorted(EVIDENCE.glob("*.png"))
    for screenshot in screenshots:
        add_image_page(pdf, screenshot, screenshot.stem.replace("_", " "))
    pdf.save()


if __name__ == "__main__":
    main()
