import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertTriangle, Images, Loader2, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { generateImages, getCategories, getHealth } from "../services/api.js";
import { DISCLAIMER, paramsFromItem } from "../services/format.js";
import CategoryIcon from "../components/CategoryIcon.jsx";
import DetailsModal from "../components/DetailsModal.jsx";
import ImageCard from "../components/ImageCard.jsx";
import { EmptyState, ErrorBanner, Spinner } from "../components/States.jsx";

export default function Workspace() {
  const location = useLocation();
  const navigate = useNavigate();

  // Data from the backend
  const [meta, setMeta] = useState(null);
  const [health, setHealth] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Form state
  const [category, setCategory] = useState("brain_mri");
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("scan");
  const [aspect, setAspect] = useState("1:1");
  const [count, setCount] = useState(1);

  // Generation state
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);
  const [lastRequest, setLastRequest] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [selected, setSelected] = useState(null);

  const run = useCallback(async (params) => {
    setStatus("loading");
    setError(null);
    setLastRequest(params);
    try {
      const data = await generateImages(params);
      setResults(data.images);
      setStatus("done");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }, []);

  // Load categories + backend health once. If we arrived from "Regenerate"
  // in the gallery, pre-fill the form and start generating straight away.
  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    Promise.all([getCategories(), getHealth()])
      .then(([m, h]) => {
        if (cancelled) return;
        setMeta(m);
        setHealth(h);
        const prefill = location.state?.prefill;
        if (prefill) {
          setCategory(prefill.category);
          setPrompt(prefill.prompt);
          setStyle(prefill.style);
          setAspect(prefill.aspect_ratio);
          setCount(1);
          navigate(location.pathname, { replace: true, state: null });
          run(paramsFromItem(prefill));
        } else {
          setPrompt(m.categories[0].suggested_prompt);
          setStyle(m.categories[0].recommended_style);
        }
      })
      .catch((err) => !cancelled && setLoadError(err));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  // Elapsed-seconds counter shown while a request is running.
  useEffect(() => {
    if (status !== "loading") return undefined;
    setElapsed(0);
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [status]);

  const categoryLabels = useMemo(
    () => Object.fromEntries((meta?.categories || []).map((c) => [c.id, c.label])),
    [meta]
  );
  const styleLabels = useMemo(() => Object.fromEntries((meta?.styles || []).map((s) => [s.id, s.label])), [meta]);

  if (loadError) {
    return (
      <div className="container page">
        <ErrorBanner error={loadError} onRetry={() => setReloadKey((k) => k + 1)} />
      </div>
    );
  }
  if (!meta) {
    return (
      <div className="container page">
        <Spinner label="Connecting to the backend…" />
      </div>
    );
  }

  const { limits } = meta;
  const promptLength = prompt.trim().length;
  const promptTooShort = promptLength < limits.min_prompt;
  const promptTooLong = promptLength > limits.max_prompt;
  const loading = status === "loading";
  const canGenerate = !loading && !promptTooShort && !promptTooLong;

  const chooseCategory = (c) => {
    setCategory(c.id);
    setPrompt(c.suggested_prompt);
    setStyle(c.recommended_style);
  };

  const applyExample = (ex) => {
    const c = meta.categories.find((x) => x.id === ex.category);
    setCategory(ex.category);
    setPrompt(ex.text);
    if (c) setStyle(c.recommended_style);
  };

  const submit = (e) => {
    e.preventDefault();
    if (!canGenerate) return;
    run({ prompt: prompt.trim(), category, style, aspect_ratio: aspect, num_images: count });
  };

  const regenerateOne = (item) => {
    setCategory(item.category);
    setPrompt(item.prompt);
    setStyle(item.style);
    setAspect(item.aspect_ratio);
    run(paramsFromItem(item));
  };

  const regenerateOpenItem = (item) => {
    setSelected(null);
    regenerateOne(item);
  };

  return (
    <div className="container page">
      <header className="page-header">
        <h1>Image Generation Workspace</h1>
        <p>Describe a medical-style image, choose its settings, and a diffusion model will generate it.</p>
      </header>

      {health?.demo_mode && (
        <div className="banner banner-warn" role="status">
          <AlertTriangle size={18} />
          <div className="banner-body">
            <strong>Demo mode is active — no AI model is configured.</strong>
            <span>
              Images will be placeholders marked “NOT AI-GENERATED”. Add a Hugging Face token to{" "}
              <code>backend/.env</code> for real generation (see README).
            </span>
          </div>
        </div>
      )}
      {health && !health.demo_mode && health.problems?.length > 0 && (
        <div className="banner banner-error" role="alert">
          <AlertTriangle size={18} />
          <div className="banner-body">
            <strong>Backend configuration problem</strong>
            <span>{health.problems.join(" ")}</span>
          </div>
        </div>
      )}

      <div className="workspace-grid">
        {/* ---------- Left: controls ---------- */}
        <form className="panel controls" onSubmit={submit}>
          <section>
            <h3 className="panel-title">1. Image category</h3>
            <div className="category-grid">
              {meta.categories.map((c) => (
                <button
                  type="button"
                  key={c.id}
                  className={`category-tile ${category === c.id ? "selected" : ""}`}
                  onClick={() => chooseCategory(c)}
                  aria-pressed={category === c.id}
                  title={c.description}
                >
                  <CategoryIcon name={c.icon} />
                  <span>{c.label}</span>
                </button>
              ))}
            </div>
          </section>

          <section>
            <h3 className="panel-title">2. Describe the image</h3>
            <label htmlFor="prompt" className="sr-only">
              Prompt
            </label>
            <textarea
              id="prompt"
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the synthetic medical-style image you want…"
              aria-invalid={promptTooShort || promptTooLong}
            />
            <div className={`field-hint ${promptTooLong ? "error" : ""}`}>
              <span>
                {promptTooShort
                  ? `Write at least ${limits.min_prompt} characters.`
                  : "Tip: mention the structure, view and level of detail you want."}
              </span>
              <span>
                {promptLength}/{limits.max_prompt}
              </span>
            </div>
          </section>

          <section>
            <h3 className="panel-title">3. Settings</h3>
            <div className="settings-grid">
              <div className="field">
                <label htmlFor="style">Image style</label>
                <select id="style" value={style} onChange={(e) => setStyle(e.target.value)}>
                  {meta.styles.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="aspect">Aspect ratio</label>
                <select id="aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
                  {meta.aspect_ratios.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="count">Number of images</label>
                <select id="count" value={count} onChange={(e) => setCount(Number(e.target.value))}>
                  {Array.from({ length: limits.max_images }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {count > 1 && (
              <p className="field-hint">
                <span>Each image is generated one after another, so {count} images take about {count}× longer.</span>
              </p>
            )}
          </section>

          <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={!canGenerate}>
            {loading ? (
              <>
                <Loader2 size={18} className="spin" /> Generating…
              </>
            ) : (
              <>
                <Sparkles size={18} /> Generate Image
              </>
            )}
          </button>
          <p className="safety-note">
            <ShieldAlert size={14} /> {DISCLAIMER}
          </p>
        </form>

        {/* ---------- Right: prompts + results ---------- */}
        <div className="results-col">
          <section className="panel">
            <h3 className="panel-title">Example prompt library</h3>
            <p className="panel-sub">Click an example to load it into the editor, then change it however you like.</p>
            <div className="example-list">
              {meta.example_prompts.map((ex, i) => (
                <button type="button" key={i} className="example-item" onClick={() => applyExample(ex)}>
                  <span className="chip">{categoryLabels[ex.category]}</span>
                  <span>{ex.text}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="panel results-panel" aria-live="polite">
            <div className="results-head">
              <h3 className="panel-title">Result</h3>
              {status === "done" && lastRequest && (
                <button className="btn btn-secondary btn-sm" onClick={() => run(lastRequest)} disabled={loading}>
                  <RefreshCw size={14} /> Regenerate
                </button>
              )}
            </div>

            {status === "idle" && (
              <EmptyState icon={Images} title="No image yet">
                Choose a category, check your prompt, then press <strong>Generate Image</strong>. Generated images
                are saved automatically to the gallery.
              </EmptyState>
            )}

            {loading && (
              <div className="progress-box" role="status">
                <div className="progress-track">
                  <div className="progress-bar" />
                </div>
                <p>
                  <strong>Generating {count > 1 ? `${count} images` : "image"}… {elapsed}s</strong>
                </p>
                <p className="meta-text">
                  The prompt is being sent to the diffusion model, which turns random noise into an image over many
                  denoising steps. Hosted models can take 10–60 s per image, and longer on the very first request
                  while the model loads.
                </p>
              </div>
            )}

            {status === "error" && <ErrorBanner error={error} onRetry={lastRequest ? () => run(lastRequest) : null} />}

            {status === "done" && !loading && (
              <div className="image-grid results-grid">
                {results.map((img) => (
                  <ImageCard
                    key={img.id}
                    item={img}
                    categoryLabel={categoryLabels[img.category]}
                    onOpen={setSelected}
                    onRegenerate={regenerateOne}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {selected && (
        <DetailsModal
          item={selected}
          categoryLabel={categoryLabels[selected.category]}
          styleLabel={styleLabels[selected.style]}
          onClose={() => setSelected(null)}
          onRegenerate={regenerateOpenItem}
        />
      )}
    </div>
  );
}
