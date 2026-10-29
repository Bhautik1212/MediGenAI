import { Brain, Droplet, HeartPulse, Microscope, ScanLine, Sparkles } from "lucide-react";

const ICONS = {
  brain: Brain,
  scan: ScanLine,
  microscope: Microscope,
  droplet: Droplet,
  "heart-pulse": HeartPulse,
};

export default function CategoryIcon({ name, size = 20 }) {
  const Icon = ICONS[name] || Sparkles;
  return <Icon size={size} aria-hidden="true" />;
}
