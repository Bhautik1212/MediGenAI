"""Static catalogue: image categories, styles and aspect ratios.

Styles work by appending descriptive words to the user's prompt, so they
function with any text-to-image model.
"""

CATEGORIES = [
    {
        "id": "brain_mri",
        "label": "Brain MRI-style",
        "icon": "brain",
        "description": "Grayscale cross-sections that resemble MRI slices.",
        "suggested_prompt": "Generate a synthetic brain MRI-style image showing anatomical structures with clear contrast.",
        "recommended_style": "scan",
    },
    {
        "id": "chest_xray",
        "label": "Chest X-ray-style",
        "icon": "scan",
        "description": "Radiograph-like views of the chest for education demos.",
        "suggested_prompt": "Create a synthetic chest X-ray-style image for an educational medical imaging demonstration.",
        "recommended_style": "scan",
    },
    {
        "id": "microscopy",
        "label": "Microscopic cells",
        "icon": "microscope",
        "description": "Laboratory-microscope views of cells and tissue.",
        "suggested_prompt": "Generate a microscopic illustration of human blood cells under a laboratory microscope.",
        "recommended_style": "microscopy",
    },
    {
        "id": "skin_lesion",
        "label": "Skin-lesion-style",
        "icon": "droplet",
        "description": "Dermatology-style close-ups (synthetic, non-diagnostic).",
        "suggested_prompt": "Create a synthetic dermatology-style close-up of a benign skin surface for an educational imaging demonstration.",
        "recommended_style": "scan",
    },
    {
        "id": "anatomy",
        "label": "Anatomical illustration",
        "icon": "heart-pulse",
        "description": "Textbook-style labelled-free drawings of organs and systems.",
        "suggested_prompt": "Create a detailed educational illustration of the human heart showing its major anatomical structures.",
        "recommended_style": "illustration",
    },
]

STYLES = {
    "scan": {
        "label": "Medical scan",
        "suffix": "grayscale medical imaging scan, high contrast, clinical imaging look, no text",
    },
    "microscopy": {
        "label": "Microscopy",
        "suffix": "laboratory microscope photograph, stained cells, shallow depth of field, no text",
    },
    "illustration": {
        "label": "Textbook illustration",
        "suffix": "clean educational medical illustration, textbook style, white background, no text",
    },
    "diagram": {
        "label": "Line art",
        "suffix": "detailed black and white line art anatomical drawing, white background, no text",
    },
}

ASPECT_RATIOS = {
    "1:1": (1, 1),
    "4:3": (4, 3),
    "3:4": (3, 4),
    "16:9": (16, 9),
}

NEGATIVE_PROMPT = "text, letters, watermark, logo, patient name, signature, label, blurry, deformed"

CATEGORY_IDS = {c["id"] for c in CATEGORIES}

# Presented in the Prompt Library (Workspace page). Users can edit before generating.
EXAMPLE_PROMPTS = [
    {"category": "brain_mri", "text": CATEGORIES[0]["suggested_prompt"]},
    {"category": "chest_xray", "text": CATEGORIES[1]["suggested_prompt"]},
    {"category": "microscopy", "text": CATEGORIES[2]["suggested_prompt"]},
    {"category": "anatomy", "text": CATEGORIES[4]["suggested_prompt"]},
    {"category": "skin_lesion", "text": CATEGORIES[3]["suggested_prompt"]},
    {"category": "microscopy", "text": "Create a microscopic view of plant cell walls stained for a biology lab handout."},
]


def dimensions_for(aspect_ratio, base_size):
    """Return (width, height) where the longest side == base_size, both multiples of 8."""
    w, h = ASPECT_RATIOS[aspect_ratio]
    longest = max(w, h)
    width = round(base_size * w / longest / 8) * 8
    height = round(base_size * h / longest / 8) * 8
    return int(width), int(height)
