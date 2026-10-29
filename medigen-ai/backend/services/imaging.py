"""Small Pillow helpers for drawing labels that always fit inside the image."""
from PIL import ImageFont

# DejaVu ships with most Linux systems; Arial / Segoe UI are on Windows; Helvetica on macOS.
_FONT_CANDIDATES = {
    False: ["DejaVuSans.ttf", "arial.ttf", "segoeui.ttf", "Arial.ttf", "Helvetica.ttc"],
    True: ["DejaVuSans-Bold.ttf", "arialbd.ttf", "segoeuib.ttf", "Arial Bold.ttf", "Helvetica.ttc"],
}


def load_font(size, bold=False):
    for name in _FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:  # Pillow >= 10.1 can scale its built-in font
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def fit_font(draw, text, max_width, start_size, min_size=8, bold=False):
    """Return (font, width, height) of the largest font <= start_size whose text fits max_width."""
    size = max(start_size, min_size)
    while True:
        font = load_font(size, bold)
        box = draw.textbbox((0, 0), text, font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        if width <= max_width or size <= min_size:
            return font, width, height, box
        size -= 1
