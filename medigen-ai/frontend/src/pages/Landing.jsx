import { Link } from "react-router-dom";
import { ArrowRight, Cpu, History, ImageIcon, PenLine, ShieldAlert, Sparkles, Wand2 } from "lucide-react";

const FEATURES = [
  {
    icon: Wand2,
    title: "Text-to-image generation",
    text: "Type a description and a pretrained Stable Diffusion model creates a synthetic medical-style image from it.",
  },
  {
    icon: PenLine,
    title: "Customizable prompts",
    text: "Pick a category, edit the suggested prompt, and tune style, aspect ratio and the number of images.",
  },
  {
    icon: History,
    title: "Generation history",
    text: "Every image is saved with its prompt, model and settings, so results can be reviewed and reproduced.",
  },
];

const STEPS = [
  { icon: PenLine, title: "Write a prompt", text: "Choose a category and describe the image." },
  { icon: Cpu, title: "Backend validates", text: "Flask checks the input and builds the final prompt." },
  { icon: Sparkles, title: "Diffusion model runs", text: "Noise is gradually denoised into an image that matches the text." },
  { icon: ImageIcon, title: "Save & review", text: "The image is stored, shown in the gallery and ready to download." },
];

export default function Landing() {
  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-text">
            <span className="eyebrow">Generative AI · Academic project</span>
            <h1>Explore Medical Imaging with Generative AI</h1>
            <p className="hero-lead">
              MediGen AI turns text descriptions into synthetic MRI-, X-ray- and microscope-style images using a
              diffusion model. It is built to learn how generative models work — and where they fall short.
            </p>
            <div className="hero-actions">
              <Link to="/workspace" className="btn btn-primary btn-lg">
                Start Generating <ArrowRight size={18} />
              </Link>
              <Link to="/gallery" className="btn btn-secondary btn-lg">
                Explore Gallery
              </Link>
            </div>
            <p className="hero-note">
              <ShieldAlert size={15} /> AI-generated synthetic images — not for clinical use.
            </p>
          </div>

          <div className="hero-visual" aria-hidden="true">
            <div className="flow-card">
              <div className="flow-step">
                <span className="flow-label">Prompt</span>
                <p>“Generate a synthetic brain MRI-style image with clear contrast.”</p>
              </div>
              <div className="flow-arrow">↓ diffusion model</div>
              <div className="flow-step flow-output">
                <ImageIcon size={30} />
                <span>Synthetic image appears here</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container section">
        <h2 className="section-title">What you can do</h2>
        <div className="feature-grid">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <article className="feature-card" key={title}>
              <div className="feature-icon">
                <Icon size={22} />
              </div>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <h2 className="section-title">How it works</h2>
          <ol className="steps">
            {STEPS.map(({ icon: Icon, title, text }, i) => (
              <li className="step" key={title}>
                <span className="step-num">{i + 1}</span>
                <Icon size={20} className="step-icon" />
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
          <p className="center-link">
            <Link to="/about">Read the full explanation and limitations →</Link>
          </p>
        </div>
      </section>
    </>
  );
}
