/// <reference types="vite/client" />

declare module "virtual:credits" {
  const credits: import("./ui/creditsData").Credits;
  export default credits;
}

interface ImportMetaEnv {
  /** "true" in builds made for the Playwright runs that read `window.__appState`. */
  readonly VITE_E2E?: string;
}
