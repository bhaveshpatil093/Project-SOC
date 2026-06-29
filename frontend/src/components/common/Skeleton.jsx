import React from 'react'

export function SkeletonCard({ lines = 3, className = "" }) {
  return (
    <div className={`p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border)] animate-pulse ${className}`}>
      <div className="h-4 bg-gray-700/50 rounded w-1/3 mb-4"></div>
      <div className="space-y-3">
        {[...Array(lines)].map((_, i) => (
          <div key={i} className="h-3 bg-gray-700/30 rounded w-full"></div>
        ))}
        <div className="h-3 bg-gray-700/30 rounded w-5/6"></div>
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 6, className = "" }) {
  return (
    <div className={`w-full bg-[var(--bg-secondary)] rounded-xl border border-[var(--border)] animate-pulse overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex border-b border-[var(--border)] bg-black/20 p-4 gap-4">
        {[...Array(cols)].map((_, i) => (
          <div key={i} className="h-3 bg-gray-700/50 rounded flex-1"></div>
        ))}
      </div>
      {/* Body */}
      <div className="divide-y divide-[var(--border)]">
        {[...Array(rows)].map((_, rowIndex) => (
          <div key={rowIndex} className="flex p-4 gap-4">
            {[...Array(cols)].map((_, colIndex) => (
              <div key={colIndex} className="h-3 bg-gray-700/30 rounded flex-1"></div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonGauge({ className = "" }) {
  return (
    <div className={`flex flex-col items-center justify-center p-6 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border)] animate-pulse ${className}`}>
      <div className="w-32 h-32 rounded-full border-8 border-gray-700/30 mb-4"></div>
      <div className="h-4 bg-gray-700/50 rounded w-24"></div>
    </div>
  )
}
