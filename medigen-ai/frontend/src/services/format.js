export function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Short name of a model id: "stabilityai/stable-diffusion-xl-base-1.0" -> "stable-diffusion-xl-base-1.0" */
export function shortModel(name = "") {
  return name.includes("/") ? name.split("/").pop() : name;
}

/** The generate API takes these fields; rebuild them from a saved record. */
export function paramsFromItem(item, numImages = 1) {
  return {
    prompt: item.prompt,
    category: item.category,
    style: item.style,
    aspect_ratio: item.aspect_ratio,
    num_images: numImages,
  };
}

export const DISCLAIMER = "AI-generated synthetic image — not for clinical use.";
