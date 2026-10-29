"""Input validation for the /api/generate endpoint."""
import re

from services.categories import ASPECT_RATIOS, CATEGORY_IDS, STYLES

# Prompts that try to pass synthetic output off as real clinical material.
BLOCKED_PHRASES = [
    "real patient", "patient name", "fake medical record", "forged", "fake diagnosis",
    "fake prescription", "medical certificate", "fake report",
]


class ValidationError(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def validate_generate_payload(data, cfg):
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    prompt = data.get("prompt")
    if not isinstance(prompt, str):
        raise ValidationError("Prompt is required.", "prompt")
    prompt = re.sub(r"\s+", " ", prompt).strip()
    prompt = "".join(ch for ch in prompt if ch.isprintable())

    if len(prompt) < cfg["MIN_PROMPT_LENGTH"]:
        raise ValidationError(
            f"Prompt is too short. Please describe the image in at least {cfg['MIN_PROMPT_LENGTH']} characters.",
            "prompt",
        )
    if len(prompt) > cfg["MAX_PROMPT_LENGTH"]:
        raise ValidationError(f"Prompt is too long (maximum {cfg['MAX_PROMPT_LENGTH']} characters).", "prompt")
    lowered = prompt.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase in lowered:
            raise ValidationError(
                "This prompt asks for content that could be mistaken for real clinical records. "
                "MediGen AI only creates clearly synthetic educational images.",
                "prompt",
            )

    category = data.get("category", "brain_mri")
    if category not in CATEGORY_IDS:
        raise ValidationError("Unknown category.", "category")

    style = data.get("style", "scan")
    if style not in STYLES:
        raise ValidationError("Unknown style.", "style")

    aspect = data.get("aspect_ratio", "1:1")
    if aspect not in ASPECT_RATIOS:
        raise ValidationError("Unsupported aspect ratio.", "aspect_ratio")

    num = data.get("num_images", 1)
    if isinstance(num, bool) or not isinstance(num, int):
        raise ValidationError("Number of images must be a whole number.", "num_images")
    if not 1 <= num <= cfg["MAX_IMAGES_PER_REQUEST"]:
        raise ValidationError(
            f"You can generate between 1 and {cfg['MAX_IMAGES_PER_REQUEST']} images at a time.", "num_images"
        )

    return {"prompt": prompt, "category": category, "style": style, "aspect_ratio": aspect, "num_images": num}
