import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { LoadingSpinner } from './LoadingSpinner'
import { EmptyState } from './EmptyState'

export const DataTable = ({ columns, data, loading, emptyMessage }) => {
  const [sortKey, setSortKey] = useState(null)
  const [sortOrder, setSortOrder] = useState('asc')

  const handleSort = (key, sortable) => {
    if (!sortable) return
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortOrder('asc')
    }
  }

  const sortedData = React.useMemo(() => {
    const arr = [...(data || [])]
    if (!sortKey) return arr

    return arr.sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]

      if (aVal === bVal) return 0
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      }
      return sortOrder === 'asc' ? (aVal < bVal ? -1 : 1) : aVal > bVal ? -1 : 1
    })
  }, [data, sortKey, sortOrder])

  return (
    <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg w-full">
      <div className="overflow-x-auto">
        <table className="w-full text-left whitespace-nowrap">
          <thead className="bg-[var(--bg\_primary)]/80 border-b border-[var(--border)]">
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className={`px-6 py-4 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider ${col.sortable ? 'cursor-pointer hover:text-[var(--text\_primary)] select-none' : ''}`}
                  onClick={() => handleSort(col.key, col.sortable)}
                >
                  <div className="flex items-center gap-1.5">
                    {col.label}
                    {col.sortable && (
                      <span className="text-[var(--text\_secondary)]">
                        {sortKey === col.key ? (
                          sortOrder === 'asc' ? (
                            <ArrowUp className="h-3 w-3 text-blue-400" />
                          ) : (
                            <ArrowDown className="h-3 w-3 text-blue-400" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3 w-3" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]/50">
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-6 py-16">
                  <LoadingSpinner />
                </td>
              </tr>
            ) : sortedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-6 py-16">
                  <EmptyState
                    title="No Records Found"
                    description={emptyMessage || 'There is no data to display here.'}
                  />
                </td>
              </tr>
            ) : (
              sortedData.map((row, rIndex) => (
                <tr
                  key={row.id || row._id || rIndex}
                  className="hover:bg-[var(--bg\_tertiary)]/70 transition-colors"
                >
                  {columns.map((col, cIndex) => (
                    <td key={cIndex} className="px-6 py-4">
                      {col.render ? (
                        col.render(row[col.key], row)
                      ) : (
                        <span className="text-sm text-[var(--text\_secondary)]">
                          {row[col.key] || '—'}
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

DataTable.propTypes = {
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      render: PropTypes.func,
      sortable: PropTypes.bool,
    }),
  ).isRequired,
  data: PropTypes.array,
  loading: PropTypes.bool,
  emptyMessage: PropTypes.string,
}
