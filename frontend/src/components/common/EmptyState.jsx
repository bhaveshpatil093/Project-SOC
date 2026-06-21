import React from 'react'
import PropTypes from 'prop-types'
import { PackageOpen } from 'lucide-react'

export const EmptyState = ({
  icon: Icon = PackageOpen,
  title,
  description,
  actionLabel,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-[var(--bg\_secondary)]/50 rounded-xl border border-dashed border-[var(--border)] animate-in fade-in duration-300">
      <div className="w-16 h-16 bg-[var(--bg\_secondary)] rounded-full flex items-center justify-center mb-4 border border-[var(--border)]">
        <Icon className="h-8 w-8 text-[var(--text\_secondary)]" />
      </div>
      <h3 className="text-lg font-bold text-[var(--text\_primary)] mb-2">{title}</h3>
      <p className="text-[var(--text\_secondary)] max-w-sm text-sm leading-relaxed mb-6">
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] text-[var(--text\_primary)] px-6 py-2 rounded-lg font-medium transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}

EmptyState.propTypes = {
  icon: PropTypes.elementType,
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  actionLabel: PropTypes.string,
  onAction: PropTypes.func,
}
