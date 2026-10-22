/** Static, trusted bootstrap; runs before body paint and reads display choices only.
 * Keep validation aligned with parseInterfacePreferences. No user text is injected.
 */
export const THEME_INIT_SCRIPT = `(() => {
  let theme = "light";
  try {
    const value = JSON.parse(localStorage.getItem("healthlink.interface.v1") || "null");
    if (value && (value.theme === "dark" || value.theme === "system")) theme = value.theme;
  } catch { /* Blocked/corrupt storage keeps the existing light default. */ }
  document.documentElement.dataset.theme = theme === "system"
    ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : theme;
})();`;
