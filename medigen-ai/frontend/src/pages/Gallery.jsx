import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, Images, Sparkles } from "lucide-react";
import { getCategories, getHistory } from "../services/api.js";
import DetailsModal from "../components/DetailsModal.jsx";
import ImageCard from "../components/ImageCard.jsx";
import { EmptyState, ErrorBanner, SkeletonGrid } from "../components/States.jsx";

const PAGE_SIZE = 12;

export default function Gallery() {
  const navigate = useNavigate();
  const [meta, setMeta] = useState(null);
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null); // { items, total, pages }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, h] = await Promise.all([getCategories(), getHistory({ page, limit: PAGE_SIZE, category })]);
      setMeta(m);
      // If the last item of a page was deleted, step back one page.
      if (h.items.length === 0 && page > 1) {
        setPage(page - 1);
        return;
      }
      setData(h);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [page, category]);

  useEffect(() => {
    load();
  }, [load]);

  const categoryLabels = useMemo(
    () => Object.fromEntries((meta?.categories || []).map((c) => [c.id, c.label])),
    [meta]
  );
  const styleLabels = useMemo(() => Object.fromEntries((meta?.styles || []).map((s) => [s.id, s.label])), [meta]);

  const changeCategory = (id) => {
    setCategory(id);
    setPage(1);
  };

  const regenerate = (item) => navigate("/workspace", { state: { prefill: item } });

  const handleDeleted = () => {
    setSelected(null);
    load();
  };

  const isEmpty = data && data.total === 0;

  return (
    <div className="container page">
      <header className="page-header">
        <h1>Generated Image Gallery</h1>
        <p>Every image you generate is saved here with its prompt and settings. All images are synthetic.</p>
      </header>

      {meta && (
        <div className="filter-row" role="group" aria-label="Filter by category">
          <button className={`filter-chip ${category === "" ? "active" : ""}`} onClick={() => changeCategory("")}>
            All
          </button>
          {meta.categories.map((c) => (
            <button
              key={c.id}
              className={`filter-chip ${category === c.id ? "active" : ""}`}
              onClick={() => changeCategory(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      {error && <ErrorBanner error={error} onRetry={load} />}
      {loading && !data && !error && <SkeletonGrid />}

      {isEmpty && !error && (
        <EmptyState
          icon={Images}
          title={category ? "No images in this category yet" : "Your gallery is empty"}
          action={
            <Link to="/workspace" className="btn btn-primary">
              <Sparkles size={16} /> Generate your first image
            </Link>
          }
        >
          {category
            ? "Try another category or generate a new image."
            : "Images you generate in the workspace will appear here."}
        </EmptyState>
      )}

      {data && data.items.length > 0 && (
        <>
          <p className="meta-text gallery-count">
            {data.total} image{data.total === 1 ? "" : "s"}
          </p>
          <div className={`image-grid ${loading ? "is-refreshing" : ""}`}>
            {data.items.map((item) => (
              <ImageCard
                key={item.id}
                item={item}
                categoryLabel={categoryLabels[item.category]}
                onOpen={setSelected}
                onRegenerate={regenerate}
              />
            ))}
          </div>

          {data.pages > 1 && (
            <nav className="pagination" aria-label="Pagination">
              <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft size={16} /> Previous
              </button>
              <span>
                Page {page} of {data.pages}
              </span>
              <button className="btn btn-ghost btn-sm" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
                Next <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}

      {selected && (
        <DetailsModal
          item={selected}
          categoryLabel={categoryLabels[selected.category]}
          styleLabel={styleLabels[selected.style]}
          onClose={() => setSelected(null)}
          onRegenerate={regenerate}
          onDeleted={handleDeleted}
        />
      )}
    </div>
  );
}
