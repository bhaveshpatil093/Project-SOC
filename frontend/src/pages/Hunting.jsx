import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { Badge } from '../components/common/Badge'
import { formatDate } from '../utils/formatters'
import { exportAlertsToCSV } from '../utils/exporters'
import {
  Search,
  Play,
  Save,
  Trash2,
  RefreshCw,
  Target,
  Database,
  Shield,
  Zap,
  Clock,
  ChevronRight,
  X,
  Download,
} from 'lucide-react'

const HUNT_TYPES = [
  { id: 'ioc_search', label: 'IOC Search', icon: Target, color: 'red', desc: 'Search for specific Indicators of Compromise' },
  { id: 'pattern_search', label: 'Pattern Hunt', icon: Zap, color: 'purple', desc: 'Hunt by known attack patterns (MITRE)' },
  { id: 'entity_search', label: 'Entity History', icon: Database, color: 'blue', desc: 'Full history of a specific entity' },
  { id: 'custom_query', label: 'Advanced Query', icon: Shield, color: 'amber', desc: 'Raw Elasticsearch DSL (admin only)' },
]

const PATTERNS = [
  { id: 'PAT-001', name: 'Valid Accounts (T1078)', tactic: 'Defense Evasion' },
  { id: 'PAT-002', name: 'Brute Force (T1110)', tactic: 'Credential Access' },
  { id: 'PAT-003', name: 'Command & Scripting (T1059)', tactic: 'Execution' },
  { id: 'PAT-004', name: 'Process Injection (T1055)', tactic: 'Privilege Escalation' },
  { id: 'PAT-005', name: 'Network Anomaly', tactic: 'Discovery' },
]

const TIME_RANGES = [
  { label: '7 days', value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
]

const SaveModal = ({ huntRequest, onClose, onSaved }) => {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')

  const saveMutation = useMutation({
    mutationFn: () => apiClient.post('/api/hunting/save', {
      name,
      description: desc,
      hunt_request: huntRequest,
    }),
    onSuccess: () => { onSaved(); onClose() },
  })

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[var(--bg\_primary)] w-full max-w-md rounded-xl border border-[var(--border)] shadow-2xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-lg">Save Hunt Query</h3>
          <button onClick={onClose} className="p-1 hover:bg-[var(--bg\_secondary)] rounded-md"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1">Hunt Name</label>
            <input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g., Lateral Movement Hunt"
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1">Description</label>
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              rows={3}
              placeholder="What does this hunt look for?"
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg\_secondary)] transition-colors">Cancel</button>
          <button
            onClick={() => name && saveMutation.mutate()}
            disabled={!name || saveMutation.isPending}
            className="flex-1 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save Hunt'}
          </button>
        </div>
      </div>
    </div>
  )
}

export const Hunting = () => {
  const queryClient = useQueryClient()

  // Builder state
  const [huntType, setHuntType] = useState('ioc_search')
  const [timeRange, setTimeRange] = useState(30)
  const [iocType, setIocType] = useState('ip')
  const [iocValue, setIocValue] = useState('')
  const [patternId, setPatternId] = useState('PAT-001')
  const [entityKey, setEntityKey] = useState('')
  const [includeArchived, setIncludeArchived] = useState(false)
  const [customQuery, setCustomQuery] = useState('{\n  "query": {"match_all": {}}\n}')

  // Results state
  const [huntResult, setHuntResult] = useState(null)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [highlight, setHighlight] = useState('')

  // Saved hunts
  const { data: savedHunts, refetch: refetchSaved } = useQuery({
    queryKey: ['savedHunts'],
    queryFn: async () => { const r = await apiClient.get('/api/hunting/saved'); return r.data.saved_hunts },
  })

  const huntMutation = useMutation({
    mutationFn: (payload) => apiClient.post('/api/hunting/search', payload),
    onSuccess: (res) => setHuntResult(res.data),
  })

  const deleteSavedMutation = useMutation({
    mutationFn: (id) => apiClient.delete(`/api/hunting/saved/${id}`),
    onSuccess: () => refetchSaved(),
  })

  const buildPayload = () => {
    let parameters = {}
    if (huntType === 'ioc_search') parameters = { ioc_type: iocType, ioc_value: iocValue }
    else if (huntType === 'pattern_search') parameters = { pattern_id: patternId, since_days: timeRange }
    else if (huntType === 'entity_search') parameters = { entity_key: entityKey, include_archived: includeArchived }
    else if (huntType === 'custom_query') {
      try { parameters = { es_query: JSON.parse(customQuery) } } catch { parameters = {} }
    }
    return { hunt_type: huntType, parameters, time_range_days: timeRange }
  }

  const runHunt = () => {
    setHighlight(huntType === 'ioc_search' ? iocValue : entityKey)
    huntMutation.mutate(buildPayload())
  }

  const runSaved = (saved) => {
    setHuntResult(null)
    huntMutation.mutate(saved.hunt_request)
  }

  const highlightText = (text, term) => {
    if (!term || !text) return text
    const parts = String(text).split(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'))
    return parts.map((part, i) =>
      part.toLowerCase() === term.toLowerCase()
        ? <mark key={i} className="bg-yellow-400/30 text-yellow-300 px-0.5 rounded">{part}</mark>
        : part
    )
  }

  return (
    <div className="space-y-6 max-w-[1800px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <span className="p-2 bg-purple-500/10 border border-purple-500/20 rounded-xl">
              <Search className="w-6 h-6 text-purple-400" />
            </span>
            Threat Hunting
          </h1>
          <p className="text-[var(--text\_secondary)] text-sm mt-1">Proactive threat discovery across all platform data</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6 items-start">
        {/* LEFT: Hunt Builder */}
        <div className="space-y-4">
          {/* Hunt Type Cards */}
          <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl p-4">
            <h2 className="font-bold text-sm uppercase tracking-wider text-[var(--text\_secondary)] mb-3">Hunt Type</h2>
            <div className="grid grid-cols-2 gap-2">
              {HUNT_TYPES.map(ht => {
                const Icon = ht.icon
                const active = huntType === ht.id
                return (
                  <button
                    key={ht.id}
                    onClick={() => setHuntType(ht.id)}
                    className={`p-3 rounded-xl border text-left transition-all ${active ? 'border-purple-500/50 bg-purple-500/10 text-purple-300' : 'border-[var(--border)] hover:border-purple-400/30 hover:bg-[var(--bg\_tertiary)]'}`}
                  >
                    <Icon className={`w-4 h-4 mb-1.5 ${active ? 'text-purple-400' : 'text-[var(--text\_secondary)]'}`} />
                    <div className={`text-xs font-bold ${active ? '' : 'text-[var(--text\_primary)]'}`}>{ht.label}</div>
                    <div className="text-[10px] text-[var(--text\_secondary)] mt-0.5 leading-tight">{ht.desc}</div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Dynamic Parameters */}
          <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl p-4 space-y-4">
            <h2 className="font-bold text-sm uppercase tracking-wider text-[var(--text\_secondary)]">Parameters</h2>

            {huntType === 'ioc_search' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">IOC Type</label>
                  <select
                    value={iocType}
                    onChange={e => setIocType(e.target.value)}
                    className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
                  >
                    <option value="ip">IP Address</option>
                    <option value="process">Process Name</option>
                    <option value="domain">Domain / URL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">IOC Value</label>
                  <input
                    value={iocValue}
                    onChange={e => setIocValue(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && runHunt()}
                    placeholder={iocType === 'ip' ? '185.220.101.x' : iocType === 'domain' ? 'malicious.example.com' : 'powershell.exe'}
                    className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-purple-500"
                  />
                </div>
              </>
            )}

            {huntType === 'pattern_search' && (
              <div>
                <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">Pattern</label>
                <select
                  value={patternId}
                  onChange={e => setPatternId(e.target.value)}
                  className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
                >
                  {PATTERNS.map(p => (
                    <option key={p.id} value={p.id}>{p.id} — {p.name}</option>
                  ))}
                </select>
                {patternId && (
                  <p className="text-xs text-[var(--text\_secondary)] mt-1.5">
                    Tactic: {PATTERNS.find(p => p.id === patternId)?.tactic}
                  </p>
                )}
              </div>
            )}

            {huntType === 'entity_search' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">Entity Key</label>
                  <input
                    value={entityKey}
                    onChange={e => setEntityKey(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && runHunt()}
                    placeholder="host-001 or username"
                    className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-purple-500"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeArchived}
                    onChange={e => setIncludeArchived(e.target.checked)}
                    className="rounded border-[var(--border)] bg-[var(--bg\_primary)] text-purple-500"
                  />
                  <span className="text-[var(--text\_secondary)]">Include archived/closed alerts</span>
                </label>
              </>
            )}

            {huntType === 'custom_query' && (
              <div>
                <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">Elasticsearch DSL <span className="text-amber-400">(Admin only)</span></label>
                <textarea
                  value={customQuery}
                  onChange={e => setCustomQuery(e.target.value)}
                  rows={8}
                  className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-amber-500 resize-none"
                />
              </div>
            )}

            {/* Time Range */}
            <div>
              <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-2">Time Range</label>
              <div className="flex gap-2">
                {TIME_RANGES.map(tr => (
                  <button
                    key={tr.value}
                    onClick={() => setTimeRange(tr.value)}
                    className={`flex-1 py-1.5 text-xs rounded-lg border font-medium transition-colors ${timeRange === tr.value ? 'bg-purple-500/20 border-purple-500/50 text-purple-300' : 'border-[var(--border)] text-[var(--text\_secondary)] hover:bg-[var(--bg\_tertiary)]'}`}
                  >
                    {tr.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Run Button */}
            <button
              onClick={runHunt}
              disabled={huntMutation.isPending}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl font-bold transition-all shadow-lg shadow-purple-900/30 text-sm"
            >
              {huntMutation.isPending ? (
                <><RefreshCw className="w-4 h-4 animate-spin" /> Hunting…</>
              ) : (
                <><Play className="w-4 h-4" /> Run Hunt</>
              )}
            </button>
          </div>

          {/* Saved Hunts */}
          <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between bg-black/20">
              <h2 className="font-bold text-sm uppercase tracking-wider text-[var(--text\_secondary)]">Saved Hunts</h2>
              <Save className="w-4 h-4 text-[var(--text\_secondary)]" />
            </div>
            <div className="divide-y divide-[var(--border)]">
              {savedHunts?.length === 0 && (
                <div className="p-4 text-center text-xs text-[var(--text\_secondary)]">No saved hunts yet</div>
              )}
              {savedHunts?.map(h => (
                <div key={h._id} className="p-3 flex items-center gap-3 hover:bg-[var(--bg\_tertiary)] transition-colors group">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[var(--text\_primary)] truncate">{h.name}</div>
                    <div className="text-xs text-[var(--text\_secondary)] truncate mt-0.5">{h.description}</div>
                    <div className="text-[10px] text-[var(--text\_secondary)] mt-1 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {formatDate(h.created_at)}
                    </div>
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => runSaved(h)}
                      title="Run again"
                      className="p-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => deleteSavedMutation.mutate(h._id)}
                      title="Delete"
                      className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT: Results Panel */}
        <div className="space-y-4">
          {huntMutation.isPending && (
            <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl p-16 flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full border-4 border-purple-500/30 border-t-purple-500 animate-spin" />
              <p className="text-[var(--text\_secondary)] font-medium">Scanning threat data…</p>
            </div>
          )}

          {huntMutation.isError && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-6 text-sm">
              Hunt failed: {huntMutation.error?.response?.data?.detail || huntMutation.error?.message}
            </div>
          )}

          {huntResult && !huntMutation.isPending && (
            <>
              {/* Summary Bar */}
              <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold">
                    Found <span className="text-purple-400">{huntResult.results_count.toLocaleString()}</span> matches
                    {huntResult.top_findings?.length > 0 && (
                      <span className="text-[var(--text\_secondary)] font-normal"> across {huntResult.top_findings.length} entities</span>
                    )}
                  </h2>
                  <p className="text-xs text-[var(--text\_secondary)] mt-0.5 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Completed in {huntResult.query_time_ms}ms
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => exportAlertsToCSV(huntResult.results)}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg\_tertiary)] transition-colors"
                  >
                    <Download className="w-4 h-4" /> Export CSV
                  </button>
                  <button
                    onClick={() => setShowSaveModal(true)}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-400 rounded-lg transition-colors"
                  >
                    <Save className="w-4 h-4" /> Save Hunt
                  </button>
                </div>
              </div>

              {/* Top Findings */}
              {huntResult.top_findings?.length > 0 && (
                <div className="bg-[var(--bg\_secondary)] border border-purple-500/30 rounded-xl p-4">
                  <h3 className="font-bold text-sm text-purple-300 mb-3 flex items-center gap-2">
                    <Target className="w-4 h-4" /> Top Findings by Entity
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {huntResult.top_findings.map((f, i) => (
                      <div key={i} className="flex items-center gap-2 bg-[var(--bg\_primary)] border border-[var(--border)] px-3 py-2 rounded-lg text-sm">
                        <span className="font-mono text-purple-300">{f.entity_key}</span>
                        <span className="text-xs text-[var(--text\_secondary)]">
                          {(f.max_threat_score * 100).toFixed(0)}%
                        </span>
                        <div className="w-2 h-2 rounded-full" style={{ background: `hsl(${(1 - f.max_threat_score) * 120}, 70%, 50%)` }} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Results Table */}
              <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-[var(--border)] bg-black/20 text-sm font-bold text-[var(--text\_secondary)]">
                  Results ({huntResult.results?.length} shown of {huntResult.results_count})
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] bg-[var(--bg\_primary)]/50">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider whitespace-nowrap">Entity</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider whitespace-nowrap">Threat Level</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider whitespace-nowrap">Score</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider whitespace-nowrap">Log Type</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider whitespace-nowrap">Timestamp</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider whitespace-nowrap">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]/60">
                      {huntResult.results?.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-12 text-center text-[var(--text\_secondary)]">
                            No results found. Try adjusting your hunt parameters.
                          </td>
                        </tr>
                      ) : (
                        huntResult.results?.map((r, i) => (
                          <tr key={i} className="hover:bg-[var(--bg\_tertiary)]/50 transition-colors">
                            <td className="px-4 py-3 font-mono font-medium text-purple-300 whitespace-nowrap">
                              {highlightText(r.entity_key || r.host_id || '-', highlight)}
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant={r.threat_level}>{r.threat_level || '-'}</Badge>
                            </td>
                            <td className="px-4 py-3 font-mono text-xs whitespace-nowrap">
                              {r.threat_score != null ? (
                                <span className={`font-bold ${r.threat_score > 0.8 ? 'text-red-400' : r.threat_score > 0.5 ? 'text-amber-400' : 'text-green-400'}`}>
                                  {(r.threat_score * 100).toFixed(1)}%
                                </span>
                              ) : '-'}
                            </td>
                            <td className="px-4 py-3 text-xs text-[var(--text\_secondary)] whitespace-nowrap">
                              {highlightText(r.log_type || '-', highlight)}
                            </td>
                            <td className="px-4 py-3 text-xs text-[var(--text\_secondary)] whitespace-nowrap font-mono">
                              {formatDate(r.timestamp)}
                            </td>
                            <td className="px-4 py-3">
                              <span className={`text-xs px-2 py-0.5 rounded-full border ${r.alert_status === 'closed' ? 'border-green-500/30 bg-green-500/10 text-green-400' : 'border-amber-500/30 bg-amber-500/10 text-amber-400'}`}>
                                {r.alert_status || 'open'}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {!huntResult && !huntMutation.isPending && (
            <div className="bg-[var(--bg\_secondary)] border border-dashed border-[var(--border)] rounded-xl p-16 flex flex-col items-center gap-4 text-center">
              <Search className="w-12 h-12 text-purple-400/40" />
              <div>
                <p className="text-[var(--text\_secondary)] font-medium">No hunt active</p>
                <p className="text-xs text-[var(--text\_secondary)] mt-1">Configure a hunt on the left and click <strong>Run Hunt</strong></p>
              </div>
            </div>
          )}
        </div>
      </div>

      {showSaveModal && (
        <SaveModal
          huntRequest={buildPayload()}
          onClose={() => setShowSaveModal(false)}
          onSaved={() => { refetchSaved(); queryClient.invalidateQueries(['savedHunts']) }}
        />
      )}
    </div>
  )
}
