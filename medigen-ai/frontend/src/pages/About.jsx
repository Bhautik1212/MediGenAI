import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";

export default function About() {
  return (
    <div className="container page about">
      <header className="page-header">
        <h1>About MediGen AI</h1>
        <p>A short guide to the ideas behind this project, written in plain language.</p>
      </header>

      <div className="banner banner-warn">
        <AlertTriangle size={18} />
        <div className="banner-body">
          <strong>Academic demonstration only</strong>
          <span>
            Images made here are synthetic and not for clinical use. They are not real scans, they are not validated,
            and they must never be used for diagnosis or medical decisions.
          </span>
        </div>
      </div>

      <section className="prose">
        <h2>What is Generative AI?</h2>
        <p>
          Generative AI is a type of machine learning that creates new content — text, images, audio or code — instead
          of only labelling existing data. A model studies a very large collection of examples, learns the patterns in
          them, and then produces new samples that follow those patterns. MediGen AI uses a generative model that
          creates images.
        </p>

        <h2>How diffusion models generate images</h2>
        <p>
          This project uses a <strong>diffusion model</strong> (Stable Diffusion). It is trained in two ideas:
        </p>
        <ol>
          <li>
            <strong>Forward process (training):</strong> real training images are gradually ruined by adding a little
            random noise at each step until only noise remains. The network learns to predict the noise that was added.
          </li>
          <li>
            <strong>Reverse process (generation):</strong> we start from pure random noise and repeatedly ask the
            network to remove a little noise. After many steps (usually 20–50) a clean image appears.
          </li>
        </ol>
        <p>
          Stable Diffusion does this in a compressed “latent” space, which makes it much faster than working directly
          on pixels. A decoder then turns the final latent into the picture you see.
        </p>

        <h2>The role of text prompts</h2>
        <p>
          A text encoder (CLIP or similar) converts the prompt into numbers that describe its meaning. During every
          denoising step these numbers guide the network, nudging the image towards the description. That is why a
          clearer prompt usually gives a more relevant result. In MediGen AI the final text sent to the model is your
          prompt plus short style words you selected (for example “grayscale medical imaging scan”). A negative prompt
          also tells the model to avoid things such as text and watermarks.
        </p>

        <h2>How the application works</h2>
        <ol>
          <li>The React frontend collects your prompt and settings.</li>
          <li>It sends a JSON request to the Flask backend: <code>POST /api/generate</code>.</li>
          <li>The backend validates the input, builds the final prompt, and calls the image model — either the Hugging
            Face hosted inference API or a local Stable Diffusion pipeline.</li>
          <li>The returned image is saved as a PNG file and its details (prompt, model, seed, size, time) are stored in
            a SQLite database.</li>
          <li>The backend replies with the image records, and the frontend displays them. The gallery reads the same
            records through <code>GET /api/history</code>.</li>
        </ol>
        <p>
          The API token for the hosted service stays in the backend’s environment file; the browser never sees it. If no
          model is configured, the app switches to a clearly labelled demo mode that produces placeholders — these are
          not AI-generated.
        </p>

        <h2>Limitations of AI-generated medical imagery</h2>
        <ul>
          <li>
            <strong>Not clinically accurate.</strong> Models learn what images look like, not human anatomy. Organs can
            have wrong shapes, missing parts or impossible structures.
          </li>
          <li>
            <strong>General-purpose training data.</strong> Stable Diffusion was not trained specifically on validated
            medical scans, so outputs only resemble the style of medical images.
          </li>
          <li>
            <strong>Bias.</strong> Training data is uneven. Some body types, ages, skin tones or conditions can be
            over- or under-represented, and the model will reflect that.
          </li>
          <li>
            <strong>Not validated training data.</strong> Synthetic images should not be used to train or test clinical
            systems unless they are independently reviewed and validated by qualified experts.
          </li>
          <li>
            <strong>Risk of misuse.</strong> Realistic fake scans could mislead people, so every image is labelled
            synthetic and every download carries a printed notice.
          </li>
          <li>
            <strong>No diagnosis.</strong> This tool cannot diagnose disease and does not replace medical professionals.
          </li>
        </ul>

        <p>
          <Link to="/workspace" className="btn btn-primary">
            Try the workspace
          </Link>
        </p>
      </section>
    </div>
  );
}
