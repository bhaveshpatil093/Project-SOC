import React from 'react'
import PropTypes from 'prop-types'
import { AlertTriangle, X } from 'lucide-react'

export const ConfirmDialog = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  onConfirm,
  onCancel,
  danger = false,
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
      <div
        className="absolute inset-0 bg-[var(--bg\_primary)]/80 backdrop-blur-sm transition-opacity"
        onClick={onCancel}
      ></div>
      <div className="relative bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl shadow-2xl max-w-md w-full animate-in zoom-in-95 duration-200">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <div
              className={`p-3 rounded-full ${danger ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'}`}
            >
              <AlertTriangle className="h-6 w-6" />
            </div>
            <button
              onClick={onCancel}
              className="text-[var(--text\_secondary)] hover:text-[var(--text\_secondary)] transition-colors p-1"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <h3 className="text-xl font-bold text-[var(--text\_primary)] mb-2">{title}</h3>
          <p className="text-[var(--text\_secondary)] text-sm leading-relaxed">{message}</p>
        </div>

        <div className="bg-[var(--bg\_secondary)]/50 px-6 py-4 rounded-b-xl border-t border-[var(--border)]/50 flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirm()
              onCancel()
            }}
            className={`px-4 py-2 text-sm font-medium text-[var(--text\_primary)] rounded-lg transition-colors ${
              danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

ConfirmDialog.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  confirmLabel: PropTypes.string,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  danger: PropTypes.bool,
}
