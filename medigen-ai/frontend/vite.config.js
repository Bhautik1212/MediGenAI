import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, requests to /api are forwarded to the Flask server,
// so the browser only ever talks to one origin (no CORS problems).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
        // Generation can take a while; do not cut the connection early.
        timeout: 600000,
        proxyTimeout: 600000,
      },
    },
  },
});
