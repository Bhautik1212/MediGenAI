import { useEffect, useState } from "react";
import { Download, RefreshCw, ShieldAlert, Trash2, X } from "lucide-react";
import { assetUrl, deleteGeneration } from "../services/api.js";
import { DISCLAIMER, formatDate } from "../services/format.js";
import { ErrorBanner } from "./States.jsx";

/**
 * Large preview + full metadata for one generated image.
 * onRegenerate(item) -> repeat the same prompt/settings.
 * onDeleted(item)    -> parent removes it from its list (only shown when provided).
 */
export default function DetailsModal({ item, categoryLabel, styleLabel, onClose, onRegenerate, onDeleted }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // Close on Escape, and stop the page behind the modal from scrolling.
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const handleDelete = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteGeneration(item.id);
      onDeleted(item);
    } catch (err) {
      setError(err);
      setBusy(false);
      setConfirming(false);
    }
  };

  const rows = [
    ["Category", categoryLabel || item.category],
    ["Style", styleLabel || item.style],
    ["Model", item.model_name],
    [
      "Provider",
      item.provider === "huggingface"
        ? "Hugging Face Inference API"
        : item.provider === "comfyui"
          ? "ComfyUI (local)"
          : item.provider,
    ],
    ["Resolution", `${item.width} × ${item.height} px (${item.aspect_ratio})`],
    ["Seed", item.seed ?? "—"],
    ["Generated", formatDate(item.created_at)],
    ["Record ID", `#${item.id}`],
  ];

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Image details">
        <button className="modal-close" onClick={onClose} aria-label="Close">
          <X size={20} />
        </button>

        <div className="modal-media">
          <img src={assetUrl(item.image_url)} alt={`Synthetic image for prompt: ${item.prompt}`} />
          <div className="media-label">
            <ShieldAlert size={14} /> {DISCLAIMER}
          </div>
        </div>

        <div className="modal-info">
          <h2>Image details</h2>
          {item.is_demo && (
            <div className="banner banner-warn">
              <strong>Demo placeholder.</strong>
              <span>This image was NOT produced by an AI model. It was created in demo mode.</span>
            </div>
          )}

          <h4>Prompt</h4>
          <p className="modal-prompt">{item.prompt}</p>

          <details className="full-prompt">
            <summary>Full prompt sent to the model</summary>
            <p>{item.full_prompt}</p>
          </details>

          <dl className="meta-table">
            {rows.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>

          <ErrorBanner error={error} />

          <div className="modal-actions">
            <a className="btn btn-primary" href={assetUrl(item.download_url)} download>
              <Download size={16} /> Download
            </a>
            {onRegenerate && (
              <button className="btn btn-secondary" onClick={() => onRegenerate(item)}>
                <RefreshCw size={16} /> Regenerate
              </button>
            )}
            {onDeleted &&
              (confirming ? (
                <span className="confirm-group">
                  <button className="btn btn-danger" onClick={handleDelete} disabled={busy}>
                    {busy ? "Deleting…" : "Confirm delete"}
                  </button>
                  <button className="btn btn-ghost" onClick={() => setConfirming(false)} disabled={busy}>
                    Cancel
                  </button>
                </span>
              ) : (
                <button className="btn btn-ghost btn-danger-text" onClick={() => setConfirming(true)}>
                  <Trash2 size={16} /> Delete
                </button>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
