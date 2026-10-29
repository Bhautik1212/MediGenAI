import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X } from "lucide-react";
import Logo from "./Logo.jsx";

const LINKS = [
  { to: "/workspace", label: "Workspace" },
  { to: "/gallery", label: "Gallery" },
  { to: "/about", label: "About" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Link to="/" className="navbar-brand" onClick={close} aria-label="MediGen AI home">
          <Logo />
        </Link>

        <nav className={`navbar-links ${open ? "is-open" : ""}`} aria-label="Main">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              onClick={close}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              {l.label}
            </NavLink>
          ))}
          <Link to="/workspace" className="btn btn-primary btn-sm nav-cta" onClick={close}>
            Start Generating
          </Link>
        </nav>

        <button
          className="navbar-toggle"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
    </header>
  );
}
