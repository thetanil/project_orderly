import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { viteSingleFile } from "vite-plugin-singlefile";

// The build is one self-contained index.html, shipped inside the Python package
// (module scripts cannot be fetched from file:// URLs, inline ones can).
export default defineConfig({
  plugins: [svelte(), viteSingleFile()],
  base: "./",
  build: { outDir: "../src/project_orderly/ui", emptyOutDir: true, chunkSizeWarningLimit: 2000 },
});
