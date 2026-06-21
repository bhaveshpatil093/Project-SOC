import { useEffect } from 'react'

export function useKeyboardShortcuts(handlers) {
  useEffect(() => {
    const handler = (e) => {
      // Ignore if user is typing in an input or textarea
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

      const key = e.key.toLowerCase()
      if (handlers[key]) {
        e.preventDefault()
        handlers[key]()
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handlers])
}
