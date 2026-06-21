import React from 'react'

export function EmptyState({
  icon = "📁",
  title = "No data available",
  description = "There is nothing to display here right now.",
  actionLabel,
  onAction,
  className = ""
}) {
  return (
    <div className={`flex flex-col items-center justify-center p-12 text-center bg-[var(--bg_secondary)] rounded-xl border border-dashed border-[var(--border)] ${className}`}>
      <div className="text-5xl mb-4 opacity-50 select-none filter drop-shadow-lg grayscale hover:grayscale-0 transition-all duration-500">
        {icon}
      </div>
      <h3 className="text-lg font-bold text-[var(--text_primary)] mb-2">{title}</h3>
      <p className="text-sm text-[var(--text_secondary)] max-w-sm mb-6">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
