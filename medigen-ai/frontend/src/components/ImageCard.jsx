import { Download, Eye, RefreshCw } from "lucide-react";
import { assetUrl } from "../services/api.js";
import { DISCLAIMER, formatDate, shortModel } from "../services/format.js";

/**
 * One generated image with its metadata.
 * `categoryLabel` is looked up by the parent from /api/categories.
 */
export default function ImageCard({ item, categoryLabel, onOpen, onRegenerate, compact = false }) {
  return (
    <article className="image-card">
      <button className="image-card-media" onClick={() => onOpen(item)} aria-label="View image details">
        <img
          src={assetUrl(item.image_url)}
          alt={`Synthetic image for prompt: ${item.prompt}`}
          loading="lazy"
          style={{ aspectRatio: `${item.width} / ${item.height}` }}
        />
        <span className="badge badge-synthetic">Synthetic</span>
        {item.is_demo && <span className="badge badge-demo">Demo – not AI</span>}
      </button>

      <div className="image-card-body">
        <p className="image-card-prompt" title={item.prompt}>
          {item.prompt}
        </p>
        <div className="meta-row">
          {categoryLabel && <span className="chip">{categoryLabel}</span>}
          <span className="meta-text">{formatDate(item.created_at)}</span>
        </div>
        {!compact && (
          <div className="meta-text" title={item.model_name}>
            Model: {shortModel(item.model_name)} · {item.width}×{item.height}
          </div>
        )}
        <p className="card-disclaimer">{DISCLAIMER}</p>

        <div className="card-actions">
          <button className="btn btn-ghost btn-sm" onClick={() => onOpen(item)}>
            <Eye size={14} /> View
          </button>
          <a className="btn btn-ghost btn-sm" href={assetUrl(item.download_url)} download>
            <Download size={14} /> Download
          </a>
          {onRegenerate && (
            <button className="btn btn-ghost btn-sm" onClick={() => onRegenerate(item)}>
              <RefreshCw size={14} /> Regenerate
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
