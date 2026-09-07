import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api and /auth are proxied to the FastAPI backend in dev,
// so the frontend never needs to know the backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000",
    },
  },
});
