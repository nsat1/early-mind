import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const API_ORIGIN = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": API_ORIGIN,
      "/media": API_ORIGIN,
      "/docs": API_ORIGIN,
      "/openapi.json": API_ORIGIN,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/setup-tests.ts"],
    unstubGlobals: true,
  },
});
