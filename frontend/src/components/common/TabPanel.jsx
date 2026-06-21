import React from 'react'
import PropTypes from 'prop-types'

export const TabPanel = ({ tabs, activeTab, onChange, children }) => {
  return (
    <div className="w-full">
      <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl p-1 inline-flex gap-1 overflow-x-auto w-full md:w-auto mb-6 shadow-sm">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2 ${
                isActive
                  ? 'bg-blue-600 text-[var(--text\_primary)] shadow-lg'
                  : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:bg-[var(--bg\_secondary)]'
              }`}
            >
              {Icon && <Icon className="h-4 w-4" />}
              {tab.label}
            </button>
          )
        })}
      </div>
      <div className="animate-in fade-in duration-300">{children}</div>
    </div>
  )
}

TabPanel.propTypes = {
  tabs: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      icon: PropTypes.elementType,
    }),
  ).isRequired,
  activeTab: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  children: PropTypes.node,
}
