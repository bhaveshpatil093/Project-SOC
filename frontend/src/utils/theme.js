export const THEMES = {
  dark: {
    'bg-primary': '#09090b', // zinc-950 (true dark)
    'bg-secondary': '#18181b', // zinc-900 (slightly lighter for panels)
    'bg-tertiary': '#27272a', // zinc-800
    'text-primary': '#fafafa', // zinc-50
    'text-secondary': '#a1a1aa', // zinc-400
    border: '#27272a', // zinc-800
    accent: '#3b82f6', // blue-500
    critical: '#ef4444', // red-500
    high: '#f97316', // orange-500
    medium: '#eab308', // yellow-500
    low: '#10b981', // emerald-500
  },
  light: {
    'bg-primary': '#f8fafc', // slate-50
    'bg-secondary': '#ffffff',
    'bg-tertiary': '#f1f5f9', // slate-100
    'text-primary': '#09090b', // zinc-950
    'text-secondary': '#52525b', // zinc-600
    border: '#e4e4e7', // zinc-200
    accent: '#2563eb', // blue-600
    critical: '#dc2626', // red-600
    high: '#ea580c', // orange-600
    medium: '#ca8a04', // yellow-600
    low: '#059669', // emerald-600
  },
}

export function applyTheme(theme) {
  // Set CSS variables on :root
  Object.entries(THEMES[theme]).forEach(([key, value]) => {
    document.documentElement.style.setProperty(`--${key}`, value)
  })
  localStorage.setItem('soc-theme', theme)
}

export function getInitialTheme() {
  return (
    localStorage.getItem('soc-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  )
}
