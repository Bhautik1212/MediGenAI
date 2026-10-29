# MediGen AI – Presentation Outline and Viva Preparation

## Part 1 – Presentation outline (12–15 minutes, 11 slides)

| # | Slide | Key points to say | Time |
|---|---|---|---|
| 1 | **Title** | MediGen AI – text-to-image generation for medical-style *educational* images. Team names, subject, guide. | 0.5 min |
| 2 | **Problem & motivation** | Real medical images are hard to share (privacy, scarcity, cost). Generative AI can create *synthetic* examples for learning — but it needs careful limits. | 1 min |
| 3 | **Objectives** | Build a working web app; use a real pretrained diffusion model; save history; be honest about limitations. | 1 min |
| 4 | **What is Generative AI?** | Models that create new content. Compare discriminative (classify) vs generative (create). Examples: GANs, VAEs, diffusion, LLMs. | 1.5 min |
| 5 | **How diffusion works** | Forward: add noise. Reverse: remove noise step by step. Latent space, text conditioning (CLIP + cross-attention), seed. Use a simple noise→image diagram. | 2 min |
| 6 | **System architecture** | React → REST → Flask → (Hugging Face API / local diffusers / demo) → SQLite + image files. Why the token is only in the backend. | 1.5 min |
| 7 | **Live demo** | Landing → pick category → edit prompt → generate → download → regenerate → gallery → details → delete. Show the "synthetic" labels. | 3 min |
| 8 | **Implementation highlights** | Provider abstraction; validation + rate limit; error handling; labelled demo mode; download label; automated backend tests. | 1 min |
| 9 | **Safety & limitations** | Not for clinical use; anatomical errors; bias; not validated data; misuse risk; what we did about it. | 1 min |
| 10 | **Results & future work** | Observed quality and generation time (fill in your own measurements). Future: fine-tune on public datasets (with ethics approval), image-to-image, evaluation metrics (FID), expert review. | 1 min |
| 11 | **Conclusion & Q&A** | Summary and thanks. | 0.5 min |

**Demo tips**
- Generate one or two images *before* the presentation so the gallery isn't empty if the internet fails.
- Check the yellow demo banner is **not** showing before you say "AI-generated".
- Keep prompts short and specific; generation can take 10–60 s — talk through the diffusion slide while it runs.
- Have a screenshot of a successful generation as a backup.

---

## Part 2 – Viva questions and answers

### Generative AI basics

**1. What is Generative AI?**
AI that creates new content (images, text, audio, code) that follows patterns learned from training data, instead of only classifying or predicting a label.

**2. Difference between discriminative and generative models?**
A discriminative model learns the boundary between classes ("is this X-ray normal?"). A generative model learns the data distribution itself, so it can produce new samples ("draw an X-ray-style image").

**3. Name some generative model families.**
GANs (generator vs discriminator), VAEs (encoder–decoder with a latent space), autoregressive models (e.g., GPT for text), and diffusion models (e.g., Stable Diffusion).

**4. Why did you choose a diffusion model?**
Diffusion models currently give high-quality, stable image generation, are easy to condition on text, and pretrained versions are freely available. GANs are harder to train and can suffer from mode collapse.

### Diffusion and Stable Diffusion

**5. Explain how a diffusion model works.**
Training: take real images, add noise in many small steps, and teach a neural network to predict the added noise. Generation: start from pure noise and repeatedly remove the predicted noise until an image appears.

**6. What is "latent diffusion"?**
Instead of denoising full-size pixel images, Stable Diffusion works on a much smaller compressed representation (the latent). A VAE encodes/decodes between pixels and latents. This is far cheaper in memory and time.

**7. How does the text prompt influence the image?**
A text encoder (CLIP) turns the prompt into embeddings. The denoising network (U-Net) uses them through cross-attention at every step, so the noise removal is steered toward the description.

**8. What is the seed?**
A number that sets the initial random noise. Same model + prompt + settings + seed gives (nearly) the same image, so we store the seed to help reproduce results.

**9. What is a negative prompt?**
Text describing what the model should move *away* from. We use it to reduce text, watermarks and logos in the output.

**10. What does the number of steps do?**
More denoising steps usually give more refined images but take longer; there are diminishing returns after about 30–50.

### The project

**11. Explain your architecture.**
React frontend sends JSON to a Flask REST API. Flask validates the request, builds the final prompt, calls the image model (Hugging Face API or local diffusers), saves the PNG, stores metadata in SQLite, and returns image URLs. The gallery reads the history endpoints.

**12. Which model do you use and where does it run?**
Stable Diffusion XL through the Hugging Face Inference API by default (no GPU needed). Optionally Stable Diffusion 1.5 locally through `diffusers`. Both are pretrained — we did not train a model ourselves.

**13. Did you train the model?**
No. We use a pretrained model for inference. Training a diffusion model needs huge datasets and GPU clusters. Our contribution is the application, prompt design, pipeline integration, storage and responsible-use design.

**14. Why is the API token in the backend?**
Anything in frontend code is visible to every user. The backend keeps it in `.env` (never committed), and the browser only talks to our own API.

**15. What happens if there is no token or no GPU?**
The app switches to demo mode, which creates a *labelled placeholder* — never presented as AI output. It shows a banner, a red "NOT AI-GENERATED" strip on the image, a "Demo – not AI" badge, and stores `is_demo = true`.

**16. How do you handle failures?**
Timeouts, unreachable service, model loading (retry), invalid token, quota limits and corrupted responses each map to a clear JSON error and HTTP status; the UI shows it with a retry button. Nothing is saved on failure.

**17. What validation and security measures did you add?**
Prompt length limits, whitelist of categories/styles/aspect ratios, integer limits for image count, blocked phrases, per-IP rate limit, request size limit, CORS restricted to the frontend origin, parameterized SQL queries, and path-traversal protection when serving/deleting files.

**18. Why SQLite?**
It's a single-file database that needs no server — ideal for a student demo. It stores the prompt, settings, model, seed, file name and timestamp for each image.

**19. How does delete work "safely"?**
The backend looks up the record, removes the file only if its resolved path is inside the images folder, then deletes the row. Unknown IDs return 404.

**20. How did you test the system?**
20 automated unit/integration tests (validation, full workflow, error cases with a mocked Hugging Face response) plus a manual checklist including a real-generation check with a token.

### Medical imaging, ethics and limitations

**21. Can the generated images be used for diagnosis or training clinical AI?**
No. They are synthetic, may have wrong anatomy, and aren't validated. They could only be considered after independent review by qualified experts.

**22. What are the main limitations?**
General-purpose model (not trained on validated medical data), anatomical inaccuracies, dataset bias, hallucinated details, no clinical meaning, and risk that realistic fakes could mislead people.

**23. What are the risks of synthetic medical images?**
Misinformation or fraud (fake scans), false confidence in unvalidated data, privacy concerns if models memorize real patient images, and bias being amplified.

**24. What did you do to reduce misuse?**
Labelled every image and download "AI-generated synthetic image — not for clinical use", blocked prompts that ask for fake records, no real patient data, and a clear About page with limitations.

**25. How could a medical-grade version be built?**
Fine-tune on properly licensed, de-identified datasets with ethics approval; evaluate with metrics such as FID and with clinician review; check for bias and privacy leakage; follow regulation.

### Possible follow-ups

**26. How is quality evaluated for generated images?**
Quantitatively with metrics like FID or CLIP score (how well the image matches the prompt), and qualitatively by human/expert review. We evaluated by visual inspection only.

**27. What would you improve with more time?**
Image-to-image editing, saving prompt favourites, user accounts, a job queue with live progress, a proper production server (Gunicorn/Waitress), and expert-reviewed evaluation.

**28. What is the difference between a GAN and a diffusion model?**
A GAN trains a generator against a discriminator in one adversarial game and produces an image in a single pass; a diffusion model trains a denoiser and generates through many small steps. Diffusion is usually more stable to train and more diverse.

**29. Why do generated hands/organs sometimes look wrong?**
The model learns statistical appearance, not anatomy rules; complex structures with many parts are hard to get globally consistent.

**30. Is the output truly random?**
It depends on the seed. With a fixed seed and settings you get nearly the same image; a new seed gives a new variation.
