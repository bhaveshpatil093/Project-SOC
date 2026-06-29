import React, { useEffect, useState, useRef } from 'react'

export const ThreatGauge = React.memo(
  ({ score = 0, size: defaultSize = 200, showLabel = true, label = 'Threat Score' }) => {
    const [animatedScore, setAnimatedScore] = useState(0)
    const containerRef = useRef(null)
    const [containerWidth, setContainerWidth] = useState(0)

    useEffect(() => {
      if (!containerRef.current) return
      const observer = new ResizeObserver((entries) => {
        for (let entry of entries) {
          setContainerWidth(entry.contentRect.width)
        }
      })
      observer.observe(containerRef.current)
      return () => observer.disconnect()
    }, [])

    useEffect(() => {
      // Slight delay so the transition triggers naturally on component mount
      const timer = setTimeout(() => setAnimatedScore(score), 50)
      return () => clearTimeout(timer)
    }, [score])

    // Determine actual size to render
    const size = containerWidth > 0 && containerWidth < 400 ? 120 : defaultSize

    const normalizedScore = Math.min(Math.max(animatedScore, 0), 100)

    let color = '#22c55e' // 0-30: Green
    let level = 'Low'
    if (normalizedScore >= 81) {
      color = '#ef4444' // 81-100: Red
      level = 'Critical'
    } else if (normalizedScore >= 61) {
      color = '#f97316' // 61-80: Orange
      level = 'High'
    } else if (normalizedScore >= 31) {
      color = '#eab308' // 31-60: Yellow
      level = 'Medium'
    }

    const strokeWidth = 16
    const radius = 100 - strokeWidth
    const circumference = radius * Math.PI
    const strokeDashoffset = circumference - (normalizedScore / 100) * circumference

    const isPulse = normalizedScore >= 80

    return (
      <div
        ref={containerRef}
        className="relative flex flex-col items-center justify-center w-full min-w-[120px]"
        style={{ height: size * 0.65 }}
      >
        <div
          style={{ width: size, height: size * 0.65 }}
          className="relative flex flex-col items-center justify-center"
        >
          <svg viewBox="0 0 200 120" className="w-full h-full overflow-visible">
            <defs>
              {isPulse && (
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              )}
            </defs>

            {/* Pulse Arc Glow Behind */}
            {isPulse && (
              <path
                d={`M ${strokeWidth} 100 A ${radius} ${radius} 0 0 1 ${200 - strokeWidth} 100`}
                fill="transparent"
                stroke={color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="animate-pulse opacity-40"
                filter="url(#glow)"
                style={{ transition: 'stroke-dashoffset 1s ease-out' }}
              />
            )}

            {/* Background Arc */}
            <path
              d={`M ${strokeWidth} 100 A ${radius} ${radius} 0 0 1 ${200 - strokeWidth} 100`}
              fill="transparent"
              stroke="#1e293b"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />

            {/* Foreground Arc */}
            <path
              d={`M ${strokeWidth} 100 A ${radius} ${radius} 0 0 1 ${200 - strokeWidth} 100`}
              fill="transparent"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              style={{ transition: 'stroke-dashoffset 1s ease-out, stroke 0.3s ease' }}
            />
          </svg>

          <div className="absolute bottom-0 flex flex-col items-center translate-y-3">
            <span
              className="font-bold text-[var(--text-primary)] leading-none"
              style={{ fontSize: size * 0.28 }}
            >
              {normalizedScore.toFixed(0)}
            </span>
            <span
              className="font-semibold tracking-wide mt-2"
              style={{ color, fontSize: size * 0.08 }}
            >
              {level}
            </span>
            {showLabel && (
              <span
                className="text-[var(--text-secondary)] font-medium uppercase tracking-wider mt-1"
                style={{ fontSize: size * 0.06 }}
              >
                {label}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  },
)
