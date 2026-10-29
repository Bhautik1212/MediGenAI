"""Central configuration for the MediGen AI backend.

Everything that can change between machines (tokens, model names, limits)
is read from environment variables / the .env file, so no secret is ever
written into source code or sent to the browser.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Config:
    # --- Paths ---------------------------------------------------------
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "medigen.db"))
    IMAGE_DIR = os.getenv("IMAGE_DIR", str(BASE_DIR / "generated_images"))

    # --- Generation mode ----------------------------------------------
    # auto        -> Hugging Face if a token exists, otherwise demo
    # huggingface -> hosted inference only
    # local       -> local diffusers pipeline only (GPU strongly recommended)
    # comfyui     -> a local ComfyUI server (for quantized/custom workflows)
    # demo        -> clearly labelled placeholder images (NOT AI generated)
    GENERATION_MODE = os.getenv("GENERATION_MODE", "auto").lower()

    # --- Hosted inference (Hugging Face) ------------------------------
    HF_API_TOKEN = os.getenv("HF_API_TOKEN", "").strip()
    HF_MODEL_ID = os.getenv("HF_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
    HF_API_URL = os.getenv(
        "HF_API_URL", "https://router.huggingface.co/hf-inference/models/{model}"
    )
    HF_TIMEOUT_SECONDS = _int("HF_TIMEOUT_SECONDS", 120)
    HF_MODEL_LOADING_RETRIES = _int("HF_MODEL_LOADING_RETRIES", 2)

    # --- ComfyUI server (GGUF / quantized models) ----------------------
    COMFYUI_API_URL = os.getenv("COMFYUI_API_URL", "http://127.0.0.1:8188").rstrip("/")
    COMFYUI_TIMEOUT_SECONDS = _int("COMFYUI_TIMEOUT_SECONDS", 900)
    COMFYUI_POLL_INTERVAL_SECONDS = _int("COMFYUI_POLL_INTERVAL_SECONDS", 2)
    COMFYUI_UNET_NAME = os.getenv(
        "COMFYUI_UNET_NAME", "qwen-image-2.1-UC-Q4_K_M.gguf"
    )
    COMFYUI_CLIP_NAME = os.getenv(
        "COMFYUI_CLIP_NAME", "qwen3vl_8b_int8_convrot.safetensors"
    )
    COMFYUI_VAE_NAME = os.getenv(
        "COMFYUI_VAE_NAME", "qwen_image_2.1_vae_bf16.safetensors"
    )
    COMFYUI_STEPS = _int("COMFYUI_STEPS", 25)

    # --- Local inference (diffusers) ----------------------------------
    LOCAL_MODEL_ID = os.getenv("LOCAL_MODEL_ID", "stable-diffusion-v1-5/stable-diffusion-v1-5")
    LOCAL_STEPS = _int("LOCAL_STEPS", 25)

    # --- Image size / limits ------------------------------------------
    # Longest side used for the selected aspect ratio. SDXL likes 1024,
    # Stable Diffusion 1.5 likes 512. Must be a multiple of 8.
    BASE_IMAGE_SIZE = _int("BASE_IMAGE_SIZE", 768)
    MAX_IMAGES_PER_REQUEST = _int("MAX_IMAGES_PER_REQUEST", 4)
    MIN_PROMPT_LENGTH = 10
    MAX_PROMPT_LENGTH = _int("MAX_PROMPT_LENGTH", 500)
    RATE_LIMIT_REQUESTS = _int("RATE_LIMIT_REQUESTS", 10)  # generate calls ...
    RATE_LIMIT_WINDOW_SECONDS = _int("RATE_LIMIT_WINDOW_SECONDS", 60)  # ... per window per IP

    # --- Web -----------------------------------------------------------
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]
    MAX_CONTENT_LENGTH = 64 * 1024  # request bodies are tiny JSON; reject anything bigger

    DISCLAIMER = "AI-generated synthetic image — not for clinical use."
