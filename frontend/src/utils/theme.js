export const THEMES = {
    dark: {
        bg_primary:     "#0f172a",   // slate-900
        bg_secondary:   "#1e293b",   // slate-800
        bg_tertiary:    "#334155",   // slate-700
        text_primary:   "#f1f5f9",   // slate-100
        text_secondary: "#94a3b8",   // slate-400
        border:         "#334155",   // slate-700
        accent:         "#3b82f6",   // blue-500
        critical:       "#ef4444",
        high:           "#f97316",
        medium:         "#eab308",
        low:            "#22c55e",
    },
    light: {
        bg_primary:     "#f8fafc",   // slate-50
        bg_secondary:   "#ffffff",
        bg_tertiary:    "#f1f5f9",   // slate-100
        text_primary:   "#0f172a",   // slate-900
        text_secondary: "#475569",   // slate-600
        border:         "#e2e8f0",   // slate-200
        accent:         "#2563eb",   // blue-600
        critical:       "#dc2626",
        high:           "#ea580c",
        medium:         "#ca8a04",
        low:            "#16a34a",
    }
};

export function applyTheme(theme) {
    // Set CSS variables on :root
    Object.entries(THEMES[theme]).forEach(([key, value]) => {
        document.documentElement.style.setProperty(`--${key}`, value);
    });
    localStorage.setItem("soc-theme", theme);
}

export function getInitialTheme() {
    return localStorage.getItem("soc-theme")
        || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
