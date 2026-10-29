export default function Logo({ size = 34, withText = true }) {
  return (
    <span className="logo">
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="#0b1f3a" />
        <path
          d="M4 17h6l3-7 4 13 3-8 2 2h6"
          fill="none"
          stroke="#2dd4bf"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {withText && (
        <span className="logo-text">
          MediGen<span className="logo-ai"> AI</span>
        </span>
      )}
    </span>
  );
}
