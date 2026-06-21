import React, { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

export function PageTransition({ children }) {
  const location = useLocation()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    return () => setMounted(false)
  }, [location.pathname])

  return (
    <div
      className={`transition-all duration-300 ease-out transform ${
        mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
      }`}
    >
      {children}
    </div>
  )
}
