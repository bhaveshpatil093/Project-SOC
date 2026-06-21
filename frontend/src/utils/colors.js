export const THREAT_COLORS = {
  critical: { bg: '#ef4444', text: '#ffffff', light: '#fef2f2' },
  high: { bg: '#f97316', text: '#ffffff', light: '#fff7ed' },
  medium: { bg: '#eab308', text: '#000000', light: '#fefce8' },
  low: { bg: '#22c55e', text: '#ffffff', light: '#f0fdf4' },
}

export const getThreatColor = (level) => {
  const l = (level || '').toLowerCase()
  return THREAT_COLORS[l] || { bg: '#64748b', text: '#ffffff', light: '#f8fafc' }
}

export const getScoreColor = (score) => {
  const s = parseFloat(score)
  if (isNaN(s)) return '#64748b'
  if (s >= 80) return '#ef4444'
  if (s >= 60) return '#f97316'
  if (s >= 30) return '#eab308'
  return '#22c55e'
}

export const getMitreColor = (tactic) => {
  if (!tactic) return '#64748b'
  let hash = 0
  for (let i = 0; i < tactic.length; i++) {
    hash = tactic.charCodeAt(i) + ((hash << 5) - hash)
  }
  const colors = [
    '#3b82f6', // blue-500
    '#8b5cf6', // violet-500
    '#ec4899', // pink-500
    '#14b8a6', // teal-500
    '#f43f5e', // rose-500
    '#d946ef', // fuchsia-500
    '#0ea5e9', // sky-500
    '#10b981', // emerald-500
  ]
  return colors[Math.abs(hash) % colors.length]
}
