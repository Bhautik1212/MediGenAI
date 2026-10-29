# MediGen AI – AI-Powered Medical Image Generation System

A college project for the **Generative AI** subject. The web app turns a text description into a *synthetic* medical-style
image (brain-MRI-style, chest-X-ray-style, microscope cells, skin-lesion-style, anatomical illustration) using a
pretrained **Stable Diffusion** model, saves every result with its metadata, and shows them in a gallery.

> **AI-generated synthetic image — not for clinical use.**
> This is an academic demonstration. The images are not real scans, are not validated, and must never be used for
> diagnosis or any medical decision.

---

## 1. Features

| Area | What it does |
|---|---|
| Landing page | Branding, headline, feature cards, workflow section |
| Workspace | Category picker (auto-fills prompt), editable prompt, example library, style, aspect ratio, 1–4 images, progress/elapsed timer, result cards with Download / Regenerate / metadata |
| Gallery | Paginated history, category filter, details modal, download, regenerate, delete |
| About | Plain-language explanation of Generative AI, diffusion, prompts, architecture, limitations |
| Backend | Flask REST API, validation, rate limit, SQLite history, safe file handling |
| Safety | Every card, modal, footer and **downloaded PNG** carries the "synthetic – not for clinical use" label; blocked-phrase check on prompts |

## 2. Architecture

```
 Browser (React + Vite)                    Flask backend                          AI model
┌──────────────────────┐   REST/JSON   ┌─────────────────────────┐   HTTPS   ┌──────────────────────────┐
│ Landing / Workspace  │ ────────────► │ routes/api.py           │ ────────► │ Hugging Face Inference   │
│ Gallery / About      │               │  validate → rate-limit  │           │ API (Stable Diffusion)   │
│ services/api.js      │ ◄──────────── │ services/generator.py ──┼─┐         └──────────────────────────┘
└──────────────────────┘  image URLs   │ services/storage.py     │ │  OR     ┌──────────────────────────┐
                                       │ models/generation.py    │ └───────► │ Local diffusers pipeline │
                                       │   │                     │           │ (your GPU/CPU)           │
                                       │   ▼                     │           └──────────────────────────┘
                                       │ SQLite (history)        │   OR (nothing configured)
                                       │ generated_images/*.png  │  ───────► Demo mode: labelled placeholder
                                       └─────────────────────────┘           (NOT AI)
```

**Why this design?** The browser never talks to the AI service directly, so the API token stays in the backend's `.env`
file. The three providers share one function (`generate_images`), so the rest of the app does not care which one ran.

### Project structure

```
medigen-ai/
├── README.md
├── docs/PRESENTATION_AND_VIVA.md
├── backend/
│   ├── app.py                  # app factory + entry point
│   ├── config.py               # reads .env (token, model, limits)
│   ├── requirements.txt        # base dependencies
│   ├── requirements-local.txt  # OPTIONAL: torch + diffusers for local generation
│   ├── .env.example
│   ├── routes/api.py           # all /api endpoints
│   ├── services/
│   │   ├── generator.py        # Hugging Face / local / ComfyUI / demo providers
│   │   ├── categories.py       # categories, styles, aspect ratios, example prompts
│   │   ├── validation.py       # input checks
│   │   ├── storage.py          # save/serve/delete files, adds download label
│   │   └── imaging.py          # font helpers for labels
│   ├── models/generation.py    # SQL queries for the history table
│   ├── database/db.py          # SQLite connection + schema
│   ├── generated_images/       # PNG files are stored here
│   └── tests/test_api.py       # automated backend tests
└── frontend/
    ├── package.json, vite.config.js, index.html
    └── src/
        ├── App.jsx, main.jsx
        ├── pages/        Landing, Workspace, Gallery, About, NotFound
        ├── components/   Navbar, Footer, Logo, ImageCard, DetailsModal, States, CategoryIcon
        ├── services/     api.js (all fetch calls), format.js
        └── styles/       base.css (tokens), components.css, pages.css
```

## 3. Generative AI methodology

**Model.** The default hosted option uses Stable Diffusion XL (`stabilityai/stable-diffusion-xl-base-1.0`) through the
Hugging Face Inference API. This setup can also use Qwen Image 2.1 GGUF through ComfyUI or Stable Diffusion 1.5 via
the `diffusers` library.

**How a prompt becomes an image**

1. *Prompt building (our code).* The backend appends style words to the user's text, e.g.
   `"<your prompt>, grayscale medical imaging scan, high contrast, no text"`, and sends a fixed **negative prompt**
   (`text, watermark, logo, patient name, …`) so the model avoids unwanted content.
2. *Text encoding.* The model's text encoder (CLIP) converts the prompt into embedding vectors.
3. *Latent diffusion.* Generation starts from random noise in a compressed **latent space**. A U-Net repeatedly predicts
   the noise in the latent, conditioned on the text embeddings through cross-attention, and removes a little of it each
   step (~20–50 steps).
4. *Decoding.* A VAE decoder converts the final latent into pixels.
5. *Seed.* A random **seed** decides the starting noise. We store it, so the same prompt + seed + settings can be
   reproduced on the same model.
6. *Storage.* The backend saves the PNG and a database row (prompt, full prompt, category, style, size, seed, model,
   provider, timestamp).

**Training idea (for explanation).** During training, real images are noised step by step and the network learns to
predict that noise (forward process). Generation runs it backwards (reverse process).

**Honest limits.** These are general-purpose models, not validated medical imaging systems. Output *resembles* the style
of medical imagery but can have wrong anatomy and bias. See the About page and §9.

## 4. Choosing how images are generated

Pick the option that fits your hardware. Set `GENERATION_MODE` in `backend/.env`.

| Option | Needs | Speed | Notes |
|---|---|---|---|
| **A. Hugging Face hosted** | Free account + access token, internet | ~10–60 s/image (first call may wait while model loads) | No GPU needed. Free usage is limited; models/providers offered on the free tier can change over time. |
| **B. Local diffusers** | NVIDIA GPU recommended; CPU works slowly with a small model | seconds on GPU; minutes on CPU | Model downloads on first use. Use `segmind/tiny-sd` and `BASE_IMAGE_SIZE=384` for a CPU-only attempt. |
| **C. Qwen Image 2.1 via ComfyUI** | ComfyUI, ComfyUI-GGUF custom nodes, compatible GPU, model files | depends on GPU | Uses the `abenzerps/Qwen-Image-2.1-Uncensored-Quantized` Q4_K_M GGUF and submits jobs to ComfyUI's API. |
| **D. Demo mode** | Nothing | instant | Draws a **placeholder** marked "DEMO MODE – NOT AI-GENERATED". Use only to show the UI when no model is available. Stored with `is_demo = true` and shown with a "Demo – not AI" badge. |

With `GENERATION_MODE=auto`: Hugging Face if `HF_API_TOKEN` is set, otherwise demo mode. Set
`GENERATION_MODE=comfyui` to use the local Qwen model. The Workspace shows a
yellow banner whenever demo mode is active, so a placeholder can never be mistaken for AI output.

The Qwen quantized repository contains model files, not a hosted inference endpoint. Setting `HF_MODEL_ID` to this
repository will not work with the Hugging Face Inference API.

### Qwen Image 2.1 ComfyUI setup

1. Install the maintained [ComfyUI-GGUF custom nodes](https://github.com/leejet/ComfyUI-GGUF) in
   `ComfyUI/custom_nodes/ComfyUI-GGUF` and install that extension's requirements in ComfyUI's Python environment.
2. Download `qwen-image-2.1-UC-Q4_K_M.gguf`, `qwen3vl_8b_int8_convrot.safetensors`, and
   `qwen_image_2.1_vae_bf16.safetensors` from
   [the model repository](https://huggingface.co/abenzerps/Qwen-Image-2.1-Uncensored-Quantized).
3. Put the GGUF in ComfyUI's `models/unet` directory, the text encoder in `models/clip`, and the VAE in
   `models/vae`. Restart ComfyUI and check that it is available at `http://127.0.0.1:8188`.
4. Set `GENERATION_MODE=comfyui` in `backend/.env`. The `COMFYUI_*` defaults match those filenames and the local
   ComfyUI URL. Restart Flask.

The backend submits a Qwen Image workflow through ComfyUI's API, waits for its generated PNG, and saves it to the
existing history/gallery. If ComfyUI reports a missing node or model, verify the extension loaded and that each
filename in `.env` exactly matches the file in the corresponding ComfyUI model folder.

**Failure handling.** Timeouts (504), unreachable service (503), model still loading (auto-retry, then 503), bad token
(502), quota/rate limit (429), missing model (502), corrupted image (502) and invalid input (400) all return a JSON
error `{"error": {"message", "code"}}` that the UI displays with a *Try again* button. Nothing is saved when generation
fails.

## 5. Installation on Windows

**Prerequisites:** Python 3.10+ (tick "Add Python to PATH" in the installer), Node.js 18+ (LTS), and optionally Git.

### 5.1 Get a Hugging Face token (for option A)

1. Create a free account at <https://huggingface.co>.
2. Open **Settings → Access Tokens → Create new token**. Choose *Fine-grained* and enable
   **"Make calls to Inference Providers"** (or choose a *Read* token if that option is shown).
3. Copy the token (starts with `hf_`). Treat it like a password.

### 5.2 Backend (Terminal 1 – PowerShell)

```powershell
cd medigen-ai\backend
py -m venv venv
venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
copy .env.example .env
notepad .env                       # paste your token after HF_API_TOKEN=
python app.py
```

The console prints the active provider, for example
`provider: huggingface | model: stabilityai/stable-diffusion-xl-base-1.0`. Check <http://127.0.0.1:5000/api/health>.
The database file and `generated_images/` folder are created automatically on first start.
To start both services with the root launcher, run `..\run-dev.ps1` from the `backend` folder, or
`.\run-dev.ps1` from the project root. The launcher installs `requirements-local.txt` automatically when
`GENERATION_MODE=local` and runs the backend with `backend\venv\Scripts\python.exe`, so dependencies are installed
into the same environment that runs the server.

*Local CPU-only model:* This uses `segmind/tiny-sd`, not Qwen. To reuse an already installed CPU-only PyTorch, create
the backend environment with system packages available, then install Diffusers:

```powershell
py -m venv --system-site-packages venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-local.txt
```

Set `GENERATION_MODE=local`, `LOCAL_MODEL_ID=segmind/tiny-sd`, `LOCAL_STEPS=4`, and `BASE_IMAGE_SIZE=384` in
`backend/.env`, then start `python app.py`. The model (about 2 GB) downloads on first use. CPU generation is slow;
close other applications first, especially on computers with 8 GB RAM. If memory runs low, stop generation and use a
stronger PC or hosted inference instead.

*Optional larger local model:* Install the GPU build of PyTorch first from
<https://pytorch.org/get-started/locally/>, then choose a compatible model and set `GENERATION_MODE=local`.

### 5.3 Frontend (Terminal 2)

```powershell
cd medigen-ai\frontend
npm install
npm run dev
```

Open <http://localhost:5173>. During development Vite forwards `/api/...` to Flask on port 5000.

*Production build:* `npm run build` creates `frontend/dist`. If the API runs on another address, set
`VITE_API_URL=http://host:5000` before building and add the frontend's origin to `CORS_ORIGINS`.

## 6. API reference

| Method & path | Purpose |
|---|---|
| `GET /api/health` | Status, active provider/model, `demo_mode`, configuration problems |
| `GET /api/categories` | Categories, styles, aspect ratios, example prompts, limits |
| `POST /api/generate` | Body: `{prompt, category, style, aspect_ratio, num_images}` → `201 {images:[…]}` |
| `GET /api/history?page=&limit=&category=` | Paginated generation history (newest first) |
| `GET /api/history/<id>` | One generation |
| `DELETE /api/history/<id>` | Deletes the DB row **and** the image file |
| `GET /api/history/<id>/download` | PNG with the "synthetic – not for clinical use" footer |
| `GET /api/images/<file>` | Serves a stored image |

Limits: prompt 10–500 characters, 1–4 images per request, 10 generate requests per minute per IP (configurable).

## 7. Testing

### 7.1 Automated backend tests (no internet or token needed)

```powershell
cd medigen-ai\backend
python -m unittest discover -s tests -v
```

**Expected:** all tests pass. They cover validation, rate limiting, generation providers, the full generate → history → download →
delete cycle, path-traversal protection, and every Hugging Face failure case (timeout, unreachable, bad token, quota,
missing model, model loading with retry, corrupted image). The network call is replaced by a fake response, so these
tests prove the application logic — **not** the image quality of the real model.

### 7.2 Manual test checklist

| # | Steps | Expected result |
|---|---|---|
| 1 | Open `/api/health` | JSON with `"status":"ok"` and the configured provider; `demo_mode` is `false` for real model providers |
| 2 | Open the site → *Start Generating* | Workspace loads, 5 category tiles, prompt pre-filled |
| 3 | Click each category | Prompt text and style change to match |
| 4 | Click an example prompt, edit a word, generate | Progress bar + seconds counter, then an image card |
| 5 | **Real-generation check (important)** | Card shows **no** "Demo – not AI" badge; details modal shows provider *Hugging Face Inference API* and the model name |
| 6 | Delete a character so prompt < 10 chars | Generate button disabled, hint explains why |
| 7 | Choose 2 images, 16:9 | Two cards of 16:9 shape |
| 8 | Click *Download* | PNG downloads with a navy footer reading "AI-generated synthetic image — not for clinical use." |
| 9 | Click *Regenerate* | New image with same prompt/settings, new seed |
| 10 | Open *Gallery* | New images listed, newest first; filter chips work |
| 11 | Open an image → *Delete* → *Confirm delete* | Item disappears; file removed from `backend/generated_images` |
| 12 | Gallery with no images | Empty state with a button to the workspace |
| 13 | Stop the Flask server, click Generate | Red error banner: "Cannot reach the backend…" |
| 14 | Put a wrong token in `.env`, restart, generate | Error: "The Hugging Face token was rejected…" |
| 15 | Resize to phone width | Menu collapses to a hamburger; layouts stack in one column |

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Yellow "Demo mode is active" banner | `HF_API_TOKEN` is empty. Add it to `backend/.env` and restart Flask. |
| ComfyUI connection error | Start ComfyUI and check `COMFYUI_API_URL` in `backend/.env`; the Flask backend must be able to reach that address. |
| ComfyUI rejects the workflow | Install ComfyUI-GGUF and check the Qwen GGUF, text encoder, and VAE filenames in `.env`. |
| "model was not found" / "service returned an error" | The free hosted model list changes. Try another `HF_MODEL_ID` in `.env`, or check/adjust `HF_API_URL` (see Hugging Face Inference Providers docs). |
| "free usage limit … reached" (429) | Wait for the quota to reset, use another account/token, use local mode, or demo mode for UI practice. |
| First request is slow / "model is loading" | Normal cold start; wait and retry. |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope Process Bypass`, or use `venv\Scripts\activate.bat` in cmd. |
| Frontend shows "Cannot reach the backend" | Flask isn't running on port 5000, or you opened the app on a different port than 5173 (CORS). |
| Local mode out of memory | Lower `BASE_IMAGE_SIZE` (512), generate 1 image at a time. |

## 9. Responsible use & limitations

- Educational demonstration only; **no diagnosis**, no replacement for medical professionals.
- Images are **synthetic** and may contain anatomical errors; general-purpose models are not trained on validated
  medical data and can reflect dataset bias.
- Generated images are **not validated clinical training data** unless independently reviewed by qualified experts.
- Do not enter real patient information. Prompts that ask for fake records/patient material are rejected.
- Hosted generation sends your prompt to a third-party service (Hugging Face); keep prompts generic.
- The in-memory rate limiter and Flask's development server are suitable for a demo, not for production deployment.

## 10. Presentation outline and viva questions

See [`docs/PRESENTATION_AND_VIVA.md`](docs/PRESENTATION_AND_VIVA.md).

## 11. Run command 
- venv\Scripts\Activate.ps1 
- ..\run-dev.ps1