// Next.js instrumentation hook — runs once when the server process starts.
// Node.js 22+ exposes a built-in `localStorage` global that exists but whose
// methods throw unless `--localstorage-file` is supplied.  This causes SSR
// crashes when any client-component code references localStorage during the
// server-side render pass (React 19 pre-renders client components).
// We replace the broken stub with a safe no-op so SSR never throws.

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const ls = (globalThis as Record<string, unknown>).localStorage;
    if (ls !== undefined && typeof (ls as Storage).getItem !== "function") {
      Object.defineProperty(globalThis, "localStorage", {
        value: {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
          clear: () => {},
          key: () => null,
          length: 0,
        },
        writable: true,
        configurable: true,
      });
    }
  }
}
