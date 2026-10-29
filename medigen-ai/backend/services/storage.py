"""Saving, serving and deleting image files safely."""
import io
import os
import uuid

from PIL import Image, ImageDraw

from services.imaging import load_font


def save_image(img, image_dir):
    """Save a PIL image as PNG under a random filename; return the filename."""
    os.makedirs(image_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    img.save(os.path.join(image_dir, filename), format="PNG")
    return filename


def safe_path(image_dir, filename):
    """Resolve a filename inside image_dir, refusing path traversal."""
    base = os.path.realpath(image_dir)
    path = os.path.realpath(os.path.join(base, filename))
    if os.path.commonpath([base, path]) != base:
        return None
    return path


def delete_image_file(image_dir, filename):
    path = safe_path(image_dir, filename)
    if path and os.path.isfile(path):
        os.remove(path)
        return True
    return False


def _wrap(draw, text, font, max_width):
    """Greedy word wrap so the label never runs off the image."""
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and draw.textlength(trial, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def with_disclaimer(path, text, is_demo=False):
    """Return PNG bytes of the image with a footer strip carrying the safety label.

    The stored original stays untouched; only the *download* gets the label.
    The strip grows (extra lines) on narrow images instead of clipping the text.
    """
    img = Image.open(path).convert("RGB")
    label = text + ("  |  DEMO PLACEHOLDER" if is_demo else "")
    size = max(11, img.width // 42)
    font = load_font(size)
    lines = _wrap(ImageDraw.Draw(img), label, font, img.width - 20)
    line_h = size + 5
    strip_h = line_h * len(lines) + 14

    out = Image.new("RGB", (img.width, img.height + strip_h), (11, 31, 58))
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    y = img.height + 7
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((img.width - w) / 2, y), line, fill="white", font=font)
        y += line_h
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf
