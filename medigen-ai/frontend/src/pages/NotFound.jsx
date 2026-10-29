import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { EmptyState } from "../components/States.jsx";

export default function NotFound() {
  return (
    <div className="container page">
      <EmptyState
        icon={Compass}
        title="Page not found"
        action={
          <Link to="/" className="btn btn-primary">
            Back to home
          </Link>
        }
      >
        The page you are looking for does not exist.
      </EmptyState>
    </div>
  );
}
