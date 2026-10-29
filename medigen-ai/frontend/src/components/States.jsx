import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="state-box">
      {Icon && (
        <div className="state-icon">
          <Icon size={28} />
        </div>
      )}
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorBanner({ error, onRetry }) {
  if (!error) return null;
  const message = typeof error === "string" ? error : error.message;
  return (
    <div className="banner banner-error" role="alert">
      <AlertTriangle size={18} />
      <div className="banner-body">
        <strong>Something went wrong</strong>
        <span>{message}</span>
      </div>
      {onRetry && (
        <button className="btn btn-ghost btn-sm" onClick={onRetry}>
          <RefreshCw size={14} /> Try again
        </button>
      )}
    </div>
  );
}

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="spinner-row" role="status">
      <Loader2 size={18} className="spin" />
      <span>{label}</span>
    </div>
  );
}

export function SkeletonGrid({ count = 6 }) {
  return (
    <div className="image-grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="skeleton skeleton-img" />
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-line short" />
        </div>
      ))}
    </div>
  );
}
