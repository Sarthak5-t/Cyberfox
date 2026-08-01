import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

const BACKEND = process.env.CYBERFOX_DASHBOARD_URL ?? "http://127.0.0.1:9119";

/**
 * The dev frontends force the auth gate on the backend
 * (`CYBERFOX_DASHBOARD_FORCE_AUTH=1` in `dev.mjs`), so the Vite dev HTML
 * must present the same gated flag the production `index.html` does — no
 * token scraping: auth calls route to the backend through the proxy below.
 * No-op in production builds.
 */
function cyberfoxDevAuthFlag(): Plugin {
  return {
    name: "cyberfox:dev-auth-gated",
    apply: "serve",
    transformIndexHtml() {
      return [
        {
          tag: "script",
          injectTo: "head",
          children:
            "window.__CYBERFOX_AUTH_REQUIRED__=true;" +
            "window.__CYBERFOX_DASHBOARD_EMBEDDED_CHAT__=true;",
        },
      ];
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), cyberfoxDevAuthFlag()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@cyberfox/shared": path.resolve(__dirname, "../apps/shared/src"),
    },
    // When @cyberfox/ui is symlinked via `file:./vendor/@cyberfox/ui`,
    // Node's module resolution would pick up shared deps from
    // vendor/@cyberfox/ui/node_modules/*, giving us two copies + breaking
    // hooks (useRef-of-null), webgl contexts, etc. Force everything that
    // exists in BOTH places to use the dashboard's copy.
    //
    // Don't list packages here that only exist in the DS (nanostores,
    // @nanostores/react) — Vite dedupe errors out when it can't find
    // them at the project root.
    dedupe: [
      "react",
      "react-dom",
      "@react-three/fiber",
      "@react-three/drei",
      "@observablehq/plot",
      "three",
      "leva",
      "gsap",
    ],
  },
  build: {
    outDir: "../cyberfox_cli/web_dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      // Auth routes (password-login, session, logout, ws-ticket) hit the
      // real backend, not a dev auth server.
      "/api/auth": {
        target: BACKEND,
        changeOrigin: true,
      },
      "/auth": {
        target: BACKEND,
        changeOrigin: true,
      },
      // Main backend handles everything else
      "/api": {
        target: BACKEND,
        ws: true,
      },
      "/dashboard-plugins": BACKEND,
    },
  },
});
