import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import Logo from "./Logo.jsx";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div className="footer-brand">
          <Logo size={28} />
          <p>Academic project for the Generative AI course. Built with React, Flask and Stable Diffusion.</p>
        </div>
        <div className="footer-links">
          <Link to="/workspace">Workspace</Link>
          <Link to="/gallery">Gallery</Link>
          <Link to="/about">About &amp; Limitations</Link>
        </div>
      </div>
      <div className="footer-notice">
        <div className="container">
          <ShieldAlert size={16} />
          <span>
            For education and research demonstration only. Images are AI-generated and synthetic — not for clinical
            use, diagnosis, or medical decisions.
          </span>
        </div>
      </div>
    </footer>
  );
}
