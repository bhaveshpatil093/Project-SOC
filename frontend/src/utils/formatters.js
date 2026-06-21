export const formatTimestamp = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d
    .toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
    .replace(',', '')
}

// Backwards compatibility for existing components mapped to formatDate
export const formatDate = formatTimestamp

export const formatRelativeTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso

  const now = new Date()
  const diffMs = now - d
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays === 1) return 'yesterday'
  return `${diffDays} days ago`
}

export const formatThreatScore = (score) => {
  if (score === null || score === undefined) return '—'
  return parseFloat(score).toFixed(1)
}

export const formatThreatLevel = (level) => {
  if (!level) return 'UNKNOWN'
  return String(level).toUpperCase()
}

export const formatEntityKey = (key) => {
  if (!key) return '—'
  return String(key).replace(/\|/g, ' / ')
}

export const formatMitreId = (id) => {
  return id || '—'
}

export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes'
  if (!bytes) return '—'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

export const formatDuration = (ms) => {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export const truncate = (str, max) => {
  if (!str) return ''
  const s = String(str)
  return s.length > max ? s.substring(0, max) + '...' : s
}
export const formatScore = formatThreatScore
