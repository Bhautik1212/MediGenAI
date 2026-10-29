"""Text-to-image generation service.

Three interchangeable providers share one function, `generate_images`:

  huggingface : sends the prompt to a hosted Stable Diffusion model (REAL AI)
  local       : runs a Stable Diffusion pipeline with `diffusers` (REAL AI)
  comfyui     : submits a Qwen GGUF workflow to a ComfyUI server (REAL AI)
  demo        : draws a procedural placeholder watermarked "DEMO - NOT AI-GENERATED"
                (NOT AI; only used when nothing else is configured)

Every provider returns GeneratedImage objects that record which provider
and model really produced the picture, so the UI/database never mislead.
"""
import hashlib
import io
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

from services.categories import NEGATIVE_PROMPT, STYLES
from services.imaging import fit_font

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """An error we can explain to the user. `status` is the HTTP status to return."""

    def __init__(self, message, status=502, code="generation_failed"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


@dataclass
class GeneratedImage:
    image: Image.Image
    provider: str  # "huggingface" | "local" | "comfyui" | "demo"
    model_name: str
    seed: int
    is_demo: bool = False


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------
def local_available():
    try:
        import diffusers  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def resolve_provider(cfg):
    """Decide which provider will be used for this configuration."""
    mode = cfg["GENERATION_MODE"]
    if mode == "demo":
        return "demo"
    if mode == "huggingface":
        return "huggingface"
    if mode == "local":
        return "local"
    if mode == "comfyui":
        return "comfyui"
    # auto
    if cfg["HF_API_TOKEN"]:
        return "huggingface"
    return "demo"


def provider_info(cfg):
    provider = resolve_provider(cfg)
    model = {
        "huggingface": cfg["HF_MODEL_ID"],
        "local": cfg["LOCAL_MODEL_ID"],
        "comfyui": cfg["COMFYUI_UNET_NAME"],
        "demo": "procedural placeholder (no AI model)",
    }[provider]
    problems = []
    if provider == "huggingface" and not cfg["HF_API_TOKEN"]:
        problems.append("HF_API_TOKEN is not set.")
    if provider == "local" and not local_available():
        problems.append("torch/diffusers are not installed (see requirements-local.txt).")
    return {"provider": provider, "model": model, "is_demo": provider == "demo", "problems": problems}


def build_prompt(prompt, style):
    return f"{prompt}, {STYLES[style]['suffix']}"


# ---------------------------------------------------------------------------
# Hugging Face hosted inference
# ---------------------------------------------------------------------------
def _hf_generate_one(full_prompt, width, height, seed, cfg):
    if not cfg["HF_API_TOKEN"]:
        raise GenerationError(
            "No Hugging Face token is configured. Add HF_API_TOKEN to backend/.env or use demo mode.",
            status=503, code="not_configured",
        )
    url = cfg["HF_API_URL"].format(model=cfg["HF_MODEL_ID"])
    headers = {"Authorization": f"Bearer {cfg['HF_API_TOKEN']}", "Accept": "image/png"}
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "negative_prompt": NEGATIVE_PROMPT,
            "width": width,
            "height": height,
            "seed": seed,
        },
    }

    attempts = cfg["HF_MODEL_LOADING_RETRIES"] + 1
    for attempt in range(attempts):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=cfg["HF_TIMEOUT_SECONDS"])
        except requests.exceptions.Timeout:
            raise GenerationError(
                "The image service took too long to respond. Please try again.", status=504, code="timeout"
            )
        except requests.exceptions.RequestException:
            raise GenerationError(
                "Could not reach the image service. Check your internet connection.", status=503, code="unreachable"
            )

        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            try:
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
            except Exception:
                raise GenerationError("The service returned a corrupted image.", code="bad_image")

        if resp.status_code == 503 and attempt < attempts - 1:
            # Model is cold-starting on the server. Wait, then retry.
            wait = 15
            try:
                wait = min(int(float(resp.json().get("estimated_time", 15))), 30)
            except Exception:
                pass
            time.sleep(max(wait, 5))
            continue

        if resp.status_code in (401, 403):
            raise GenerationError(
                "The Hugging Face token was rejected. Check HF_API_TOKEN and its permissions.",
                status=502, code="auth",
            )
        if resp.status_code in (402, 429):
            raise GenerationError(
                "The free usage limit of the image service has been reached. Wait a while or try demo mode.",
                status=429, code="quota",
            )
        if resp.status_code == 404:
            raise GenerationError(
                f"Model '{cfg['HF_MODEL_ID']}' was not found on the inference service.", status=502, code="model_not_found"
            )
        if resp.status_code in (400, 410):
            detail = ""
            try:
                detail = str(resp.json().get("error") or resp.json().get("message") or "").lower()
            except Exception:
                pass
            if "not supported by provider hf-inference" in detail or "deprecated" in detail:
                raise GenerationError(
                    "The configured Hugging Face model is no longer supported by the hosted inference provider. "
                    "Update HF_MODEL_ID in backend/.env or switch to demo mode.",
                    status=502,
                    code="model_not_supported",
                )
        if resp.status_code == 503:
            raise GenerationError(
                "The model is still loading on the server. Please try again in a minute.", status=503, code="model_loading"
            )
        raise GenerationError(f"The image service returned an error (HTTP {resp.status_code}).", code="upstream_error")

    raise GenerationError("The image service is not available right now.", status=503, code="unavailable")


# ---------------------------------------------------------------------------
# Local diffusers pipeline (lazy-loaded, loaded once)
# ---------------------------------------------------------------------------
_pipeline = None
_pipeline_lock = threading.Lock()


def _get_pipeline(cfg):
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            try:
                import torch
                from diffusers import AutoPipelineForText2Image
            except ImportError:
                raise GenerationError(
                    "Local generation needs torch and diffusers. Run: pip install -r requirements-local.txt",
                    status=503, code="not_configured",
                )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(cfg["LOCAL_MODEL_ID"], torch_dtype=dtype)
            except Exception as exc:
                raise GenerationError(f"Could not load local model: {exc}", status=503, code="model_load_failed")
            _pipeline = pipe.to(device)
            if device == "cpu":
                _pipeline.enable_attention_slicing()
                _pipeline.vae.enable_slicing()
            _pipeline._medigen_device = device
        return _pipeline


def _local_generate_one(full_prompt, width, height, seed, cfg):
    import torch

    pipe = _get_pipeline(cfg)
    generator = torch.Generator(device=pipe._medigen_device).manual_seed(seed)
    try:
        with _pipeline_lock:  # one generation at a time on local hardware
            result = pipe(
                prompt=full_prompt,
                negative_prompt=NEGATIVE_PROMPT,
                width=width,
                height=height,
                num_inference_steps=cfg["LOCAL_STEPS"],
                generator=generator,
            )
    except Exception as exc:
        raise GenerationError(f"Local generation failed: {exc}", code="local_failed")
    return result.images[0].convert("RGB")


# ---------------------------------------------------------------------------
# ComfyUI server (Qwen Image 2.1 GGUF)
# ---------------------------------------------------------------------------
def _comfyui_workflow(full_prompt, width, height, seed, cfg):
    return {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": cfg["COMFYUI_UNET_NAME"]},
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": cfg["COMFYUI_CLIP_NAME"], "type": "qwen_image"},
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": cfg["COMFYUI_VAE_NAME"]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": full_prompt, "clip": ["2", 0]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEGATIVE_PROMPT, "clip": ["2", 0]},
        },
        "6": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "7": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 3.1},
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["7", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": cfg["COMFYUI_STEPS"],
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["9", 0], "filename_prefix": "medigen-qwen"},
        },
    }


def _comfyui_generate_one(full_prompt, width, height, seed, cfg):
    base_url = cfg["COMFYUI_API_URL"].rstrip("/")
    client_id = str(uuid.uuid4())
    try:
        response = requests.post(
            f"{base_url}/prompt",
            json={
                "prompt": _comfyui_workflow(full_prompt, width, height, seed, cfg),
                "client_id": client_id,
            },
            timeout=30,
        )
    except requests.exceptions.Timeout:
        raise GenerationError(
            "ComfyUI did not accept the generation request in time.",
            status=504,
            code="timeout",
        )
    except requests.exceptions.RequestException:
        raise GenerationError(
            "Could not reach ComfyUI. Start it or set COMFYUI_API_URL in backend/.env.",
            status=503,
            code="unreachable",
        )

    if response.status_code != 200:
        raise GenerationError(
            f"ComfyUI rejected the workflow (HTTP {response.status_code}). "
            "Check that the Qwen GGUF custom nodes and model files are installed.",
            status=502,
            code="workflow_rejected",
        )
    try:
        prompt_id = response.json().get("prompt_id")
    except (ValueError, AttributeError):
        prompt_id = None
    if not prompt_id:
        raise GenerationError(
            "ComfyUI returned an invalid response for the generation request.",
            code="bad_response",
        )

    deadline = time.monotonic() + cfg["COMFYUI_TIMEOUT_SECONDS"]
    history_url = f"{base_url}/history/{prompt_id}"
    while time.monotonic() < deadline:
        try:
            history_response = requests.get(history_url, timeout=15)
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException:
            raise GenerationError(
                "The connection to ComfyUI was interrupted while generating.",
                status=503,
                code="unreachable",
            )
        if history_response.status_code != 200:
            raise GenerationError(
                f"ComfyUI history request failed (HTTP {history_response.status_code}).",
                code="history_failed",
            )
        try:
            history = history_response.json().get(prompt_id, {})
        except (ValueError, AttributeError):
            raise GenerationError("ComfyUI returned invalid generation history.", code="bad_response")

        status = history.get("status", {})
        if status.get("status_str") == "error":
            raise GenerationError(
                "ComfyUI failed to run the workflow. Check its console for model or node errors.",
                code="generation_failed",
            )
        images = history.get("outputs", {}).get("10", {}).get("images", [])
        if images:
            image_info = images[0]
            try:
                image_response = requests.get(
                    f"{base_url}/view",
                    params={
                        "filename": image_info["filename"],
                        "subfolder": image_info.get("subfolder", ""),
                        "type": image_info.get("type", "output"),
                    },
                    timeout=60,
                )
            except requests.exceptions.Timeout:
                raise GenerationError(
                    "Timed out downloading the image from ComfyUI.",
                    status=504,
                    code="timeout",
                )
            except requests.exceptions.RequestException:
                raise GenerationError(
                    "Could not download the image from ComfyUI.",
                    status=503,
                    code="unreachable",
                )
            if image_response.status_code != 200:
                raise GenerationError(
                    f"ComfyUI image download failed (HTTP {image_response.status_code}).",
                    code="image_download_failed",
                )
            try:
                return Image.open(io.BytesIO(image_response.content)).convert("RGB")
            except (OSError, ValueError):
                raise GenerationError("ComfyUI returned a corrupted image.", code="bad_image")
        time.sleep(max(0.1, cfg["COMFYUI_POLL_INTERVAL_SECONDS"]))

    raise GenerationError(
        "ComfyUI generation timed out. Check its queue and available GPU memory.",
        status=504,
        code="timeout",
    )


# ---------------------------------------------------------------------------
# Demo mode (NOT AI)
# ---------------------------------------------------------------------------
def _demo_one(prompt, width, height, seed):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    cx, cy = width / 2, height / 2
    dist = np.sqrt(((x - cx) / (width / 2)) ** 2 + ((y - cy) / (height / 2)) ** 2)
    base = np.clip(0.85 - dist * 0.7, 0, 1)
    noise = rng.normal(0, 0.06, (height, width))
    arr = np.clip((base + noise) * 255, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "L").filter(ImageFilter.GaussianBlur(2)).convert("RGB")

    draw = ImageDraw.Draw(img)
    msg = "DEMO MODE - NOT AI-GENERATED"
    font, tw, th, box = fit_font(draw, msg, width - 24, max(14, width // 16), bold=True)
    top = (height - th) // 2
    draw.rectangle([0, top - th // 2, width, top + th + th // 2], fill=(180, 30, 30))
    draw.text(((width - tw) / 2 - box[0], top - box[1]), msg, fill="white", font=font)
    return img


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_images(prompt, style, width, height, count, cfg):
    provider = resolve_provider(cfg)
    full_prompt = build_prompt(prompt, style)
    results = []
    for _ in range(count):
        seed = random.randint(0, 2**31 - 1)
        if provider == "huggingface":
            try:
                img = _hf_generate_one(full_prompt, width, height, seed, cfg)
                results.append(GeneratedImage(img, "huggingface", cfg["HF_MODEL_ID"], seed))
            except GenerationError as exc:
                if cfg.get("GENERATION_MODE") == "auto" and exc.code in {
                    "model_not_supported",
                    "model_not_found",
                    "auth",
                    "not_configured",
                }:
                    seed = int(hashlib.sha256(f"{prompt}{seed}".encode()).hexdigest()[:8], 16)
                    img = _demo_one(prompt, width, height, seed)
                    results.append(GeneratedImage(img, "demo", "demo-placeholder (no AI)", seed, is_demo=True))
                else:
                    raise
        elif provider == "local":
            try:
                img = _local_generate_one(full_prompt, width, height, seed, cfg)
            except GenerationError:
                raise
            except Exception as exc:
                logger.exception("Unexpected error during local image generation")
                raise GenerationError(
                    "Local image generation failed unexpectedly. Check the backend console for details.",
                    status=500,
                    code="local_failed",
                ) from exc
            results.append(GeneratedImage(img, "local", cfg["LOCAL_MODEL_ID"], seed))
        elif provider == "comfyui":
            img = _comfyui_generate_one(full_prompt, width, height, seed, cfg)
            results.append(GeneratedImage(img, "comfyui", cfg["COMFYUI_UNET_NAME"], seed))
        else:
            seed = int(hashlib.sha256(f"{prompt}{seed}".encode()).hexdigest()[:8], 16)
            img = _demo_one(prompt, width, height, seed)
            results.append(GeneratedImage(img, "demo", "demo-placeholder (no AI)", seed, is_demo=True))
    return full_prompt, results
