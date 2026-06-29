import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { FileText, Download, User, Activity, AlertTriangle, Search, Filter } from 'lucide-react'
import { formatDate } from '../../utils/formatters'
import { LoadingSpinner } from '../common/LoadingSpinner'

export const AuditLogPanel = () => {
  const [filterUser, setFilterUser] = useState('')
  const [filterAction, setFilterAction] = useState('')
  
  const { data, isLoading } = useQuery({
    queryKey: ['auditLogs', filterUser, filterAction],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filterUser) params.append('user', filterUser)
      if (filterAction) params.append('action', filterAction)
      const res = await apiClient.get(`/api/admin/audit-log?${params.toString()}`)
      return res.data || []
    },
    refetchInterval: 60000
  })

  const { data: activityData } = useQuery({
    queryKey: ['userActivity', filterUser],
    queryFn: async () => {
      if (!filterUser) return null
      const res = await apiClient.get(`/api/admin/audit-log/users/${filterUser}`)
      return res.data || null
    },
    enabled: !!filterUser
  })

  const handleExport = () => {
    window.location.href = `http://localhost:8000/api/admin/audit-log/export?since_hours=24`
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)] shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-[var(--bg-primary)] px-3 py-1.5 rounded-lg border border-[var(--border)] focus-within:border-blue-500">
            <Search className="w-4 h-4 text-[var(--text-secondary)]" />
            <input 
              type="text" 
              placeholder="Filter by user..." 
              value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}
              className="bg-transparent border-none outline-none text-sm w-40 text-[var(--text-primary)]"
            />
          </div>
          <div className="flex items-center gap-2 bg-[var(--bg-primary)] px-3 py-1.5 rounded-lg border border-[var(--border)] focus-within:border-blue-500">
            <Filter className="w-4 h-4 text-[var(--text-secondary)]" />
            <input 
              type="text" 
              placeholder="Filter by action..." 
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              className="bg-transparent border-none outline-none text-sm w-40 text-[var(--text-primary)]"
            />
          </div>
        </div>
        <button 
          onClick={handleExport}
          className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-colors text-sm"
        >
          <Download className="w-4 h-4" /> Export CSV
        </button>
      </div>

      {activityData && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-blue-500/10 rounded-lg text-blue-500"><Activity className="w-5 h-5"/></div>
            <div>
              <p className="text-xs text-[var(--text-secondary)] uppercase font-bold tracking-wider">Total Actions</p>
              <p className="text-xl font-bold text-[var(--text-primary)]">{activityData.total_actions}</p>
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-orange-500/10 rounded-lg text-orange-500"><AlertTriangle className="w-5 h-5"/></div>
            <div>
              <p className="text-xs text-[var(--text-secondary)] uppercase font-bold tracking-wider">Alerts Triaged</p>
              <p className="text-xl font-bold text-[var(--text-primary)]">{activityData.alerts_triaged}</p>
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-green-500/10 rounded-lg text-green-500"><FileText className="w-5 h-5"/></div>
            <div>
              <p className="text-xs text-[var(--text-secondary)] uppercase font-bold tracking-wider">Feedback Submitted</p>
              <p className="text-xl font-bold text-[var(--text-primary)]">{activityData.feedback_submitted}</p>
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-purple-500/10 rounded-lg text-purple-500"><User className="w-5 h-5"/></div>
            <div>
              <p className="text-xs text-[var(--text-secondary)] uppercase font-bold tracking-wider">SLM Queries</p>
              <p className="text-xl font-bold text-[var(--text-primary)]">{activityData.slm_queries}</p>
            </div>
          </div>
        </div>
      )}

      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-[var(--bg-tertiary)] border-b border-[var(--border)]">
              <tr>
                <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">Timestamp</th>
                <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">User</th>
                <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">Action</th>
                <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">Resource</th>
                <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">Result</th>
                <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">IP Address</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {isLoading ? (
                <tr><td colSpan="6" className="p-8 text-center"><LoadingSpinner /></td></tr>
              ) : data?.length === 0 ? (
                <tr><td colSpan="6" className="p-8 text-center text-[var(--text-secondary)]">No audit logs found.</td></tr>
              ) : (
                data?.map((log) => (
                  <tr key={log.event_id} className="hover:bg-[var(--bg-tertiary)]/50 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-[var(--text-secondary)]">
                      {formatDate(new Date(log.timestamp))}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-500 flex items-center justify-center font-bold text-xs">
                          {log.user.charAt(0).toUpperCase()}
                        </span>
                        <span className="font-medium text-[var(--text-primary)]">{log.user}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-[var(--text-primary)] bg-[var(--bg-primary)]/30 rounded px-2">
                      {log.action}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-[var(--text-secondary)]">{log.resource_type}</span>
                      {log.resource_id && (
                        <span className="ml-2 font-mono text-xs px-2 py-0.5 rounded bg-[var(--bg-primary)] border border-[var(--border)] text-[var(--text-primary)]">
                          {log.resource_id.substring(0, 8)}...
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        log.result === 'success' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
                      }`}>
                        {log.result}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-[var(--text-secondary)]">
                      {log.ip_address}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
