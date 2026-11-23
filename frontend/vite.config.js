import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";
import { indexingFiles, publicSite } from "./src/data/publicIndexing.js";

// Preview builds use bundled demo data without a backend.
// Normal builds communicate with FastAPI at VITE_API_URL.

const integrationApiProxy = {
  name: "reprocare-local-integration-api",
  apply: "serve",
  config({ server }, { isPreview }) {
    const loopbackHosts = [undefined, "localhost", "127.0.0.1", "::1"];
    if (isPreview || server?.port !== 15173 || !loopbackHosts.includes(server?.host)) return;

    return {
      define: { "import.meta.env.REPROCARE_LOCAL_API_PROXY": "true" },
      server: {
        proxy: { "/api": { target: "http://127.0.0.1:18100" } },
      },
    };
  },
};

function publicIndexing(mode) {
  const env = loadEnv(mode, process.cwd(), "VITE_PUBLIC_SITE_URL");
  const origin = publicSite(env.VITE_PUBLIC_SITE_URL);
  return {
    name: "reprocare-public-indexing",
    configureServer(server) {
      const { robots, sitemap } = indexingFiles(null);
      for (const [url, source, contentType] of [
        ["/robots.txt", robots, "text/plain"],
        ["/sitemap.xml", sitemap, "application/xml"],
      ]) {
        server.middlewares.use(url, (_request, response) => {
          response.setHeader("Content-Type", contentType + "; charset=utf-8");
          response.end(source);
        });
      }
    },
    generateBundle() {
      const { robots, sitemap } = indexingFiles(origin);
      this.emitFile({ type: "asset", fileName: "robots.txt", source: robots });
      this.emitFile({ type: "asset", fileName: "sitemap.xml", source: sitemap });
    },
  };
}

export default defineConfig(({ mode }) => {
  const isPreview = mode === "preview";

  if (isPreview) {
    process.env.VITE_DEMO_MODE = "true";
  }

  return {
    plugins: [react(), integrationApiProxy, ...(isPreview ? [viteSingleFile()] : [publicIndexing(mode)])],

    server: {
      port: 5173,
    },

    build: {
      outDir: isPreview ? "dist-preview" : "dist",

      // Preserve the single-file HTML preview.
      // Split vendor dependencies only in normal builds.
      ...(!isPreview && {
        rollupOptions: {
          output: {
            manualChunks(id) {
              if (!id.includes("node_modules")) {
                return;
              }

              if (id.includes("lucide-react")) {
                return "icons-vendor";
              }

              if (
                id.includes("/react/") ||
                id.includes("/react-dom/") ||
                id.includes("/scheduler/")
              ) {
                return "react-vendor";
              }
            },
          },
        },
      }),
    },

    test: {
      environment: "jsdom",
      setupFiles: "./src/test-setup.js",
      globals: true,
    },
  };
});
