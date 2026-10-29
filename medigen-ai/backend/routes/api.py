"""REST API routes (all under /api)."""
import os
import time
from collections import defaultdict, deque

from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory

from models import generation as repo
from services import categories as cat
from services import storage
from services.generator import GenerationError, generate_images, provider_info
from services.validation import ValidationError, validate_generate_payload

api = Blueprint("api", __name__, url_prefix="/api")

# --- tiny in-memory rate limiter (per IP) ---------------------------------
_hits = defaultdict(deque)


def _rate_limited():
    cfg = current_app.config
    now = time.time()
    window = cfg["RATE_LIMIT_WINDOW_SECONDS"]
    q = _hits[request.remote_addr or "unknown"]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= cfg["RATE_LIMIT_REQUESTS"]:
        return int(window - (now - q[0])) + 1
    q.append(now)
    return 0


def error(message, status, code, field=None):
    body = {"error": {"message": message, "code": code}}
    if field:
        body["error"]["field"] = field
    return jsonify(body), status


# --- routes ----------------------------------------------------------------
@api.get("/health")
def health():
    info = provider_info(current_app.config)
    return jsonify({
        "status": "ok",
        "provider": info["provider"],
        "model": info["model"],
        "demo_mode": info["is_demo"],
        "problems": info["problems"],
        "disclaimer": current_app.config["DISCLAIMER"],
    })


@api.get("/categories")
def categories():
    cfg = current_app.config
    return jsonify({
        "categories": cat.CATEGORIES,
        "styles": [{"id": k, "label": v["label"]} for k, v in cat.STYLES.items()],
        "aspect_ratios": list(cat.ASPECT_RATIOS.keys()),
        "example_prompts": cat.EXAMPLE_PROMPTS,
        "limits": {
            "max_images": cfg["MAX_IMAGES_PER_REQUEST"],
            "min_prompt": cfg["MIN_PROMPT_LENGTH"],
            "max_prompt": cfg["MAX_PROMPT_LENGTH"],
        },
    })


@api.post("/generate")
def generate():
    cfg = current_app.config
    wait = _rate_limited()
    if wait:
        return error(f"Too many requests. Please wait about {wait} seconds.", 429, "rate_limited")

    data = request.get_json(silent=True)
    if data is None:
        return error("Request body must be valid JSON.", 400, "invalid_json")
    try:
        p = validate_generate_payload(data, cfg)
    except ValidationError as e:
        return error(e.message, 400, "validation_error", e.field)

    width, height = cat.dimensions_for(p["aspect_ratio"], cfg["BASE_IMAGE_SIZE"])
    try:
        full_prompt, images = generate_images(p["prompt"], p["style"], width, height, p["num_images"], cfg)
    except GenerationError as e:
        return error(e.message, e.status, e.code)

    saved = []
    for g in images:
        filename = storage.save_image(g.image, cfg["IMAGE_DIR"])
        saved.append(repo.create_generation(
            prompt=p["prompt"], full_prompt=full_prompt, category=p["category"], style=p["style"],
            aspect_ratio=p["aspect_ratio"], width=width, height=height, seed=g.seed,
            model_name=g.model_name, provider=g.provider, is_demo=g.is_demo, filename=filename,
        ))
    return jsonify({"images": saved, "disclaimer": cfg["DISCLAIMER"]}), 201


@api.get("/history")
def history():
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(50, max(1, int(request.args.get("limit", 12))))
    except ValueError:
        return error("page and limit must be numbers.", 400, "validation_error")
    category = request.args.get("category") or None
    if category and category not in cat.CATEGORY_IDS:
        return error("Unknown category.", 400, "validation_error", "category")
    items, total = repo.list_generations(page, limit, category)
    return jsonify({"items": items, "total": total, "page": page, "limit": limit,
                    "pages": max(1, -(-total // limit))})


@api.get("/history/<int:gen_id>")
def history_item(gen_id):
    item = repo.get_generation(gen_id)
    if not item:
        return error("Generation not found.", 404, "not_found")
    return jsonify(item)


@api.delete("/history/<int:gen_id>")
def history_delete(gen_id):
    item = repo.get_generation(gen_id)
    if not item:
        return error("Generation not found.", 404, "not_found")
    storage.delete_image_file(current_app.config["IMAGE_DIR"], item["filename"])
    repo.delete_generation(gen_id)
    return jsonify({"deleted": gen_id})


@api.get("/history/<int:gen_id>/download")
def history_download(gen_id):
    item = repo.get_generation(gen_id)
    if not item:
        return error("Generation not found.", 404, "not_found")
    path = storage.safe_path(current_app.config["IMAGE_DIR"], item["filename"])
    if not path or not os.path.isfile(path):
        return error("Image file is missing on the server.", 404, "file_missing")
    buf = storage.with_disclaimer(path, current_app.config["DISCLAIMER"], item["is_demo"])
    return send_file(buf, mimetype="image/png", as_attachment=True,
                     download_name=f"medigen-{item['id']}-synthetic.png")


@api.get("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(current_app.config["IMAGE_DIR"], filename, mimetype="image/png")
