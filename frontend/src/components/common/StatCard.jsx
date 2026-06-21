import React from 'react'
import PropTypes from 'prop-types'
import { LoadingSpinner } from './LoadingSpinner'

export const StatCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'blue',
  loading = false,
}) => {
  const bgColors = {
    blue: 'bg-blue-500/10 text-blue-500 border-blue-500/50',
    red: 'bg-red-500/10 text-red-500 border-red-500/50',
    green: 'bg-green-500/10 text-green-500 border-green-500/50',
    orange: 'bg-orange-500/10 text-orange-500 border-orange-500/50',
    purple: 'bg-purple-500/10 text-purple-500 border-purple-500/50',
    slate: 'bg-[var(--text_secondary)]/10 text-[var(--text_secondary)] border-[var(--border)]',
  }

  const textColors = {
    blue: 'text-blue-500',
    red: 'text-red-500',
    green: 'text-green-500',
    orange: 'text-orange-500',
    purple: 'text-purple-500',
    slate: 'text-[var(--text_primary)]',
  }

  return (
    <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 flex items-center justify-between shadow-lg transition-transform hover:-translate-y-1 hover:border-[var(--border)]">
      <div>
        <h3 className="text-[var(--text_secondary)] text-sm font-semibold uppercase tracking-wider mb-2">
          {title}
        </h3>
        {loading ? (
          <div className="h-10 flex items-center">
            <LoadingSpinner size="sm" centered={false} />
          </div>
        ) : (
          <div className={`text-4xl font-bold ${textColors[color] || textColors.blue}`}>
            {value}
          </div>
        )}
        {subtitle && (
          <p className="text-xs text-[var(--text_secondary)] mt-2 font-medium">{subtitle}</p>
        )}
      </div>
      {Icon && (
        <div
          className={`p-4 rounded-xl border ${bgColors[color] || bgColors.blue} flex items-center justify-center shrink-0 ml-4`}
        >
          <Icon className="h-8 w-8" />
        </div>
      )}
    </div>
  )
}

StatCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  subtitle: PropTypes.node,
  icon: PropTypes.elementType,
  color: PropTypes.oneOf(['blue', 'red', 'green', 'orange', 'purple', 'slate']),
  loading: PropTypes.bool,
}
