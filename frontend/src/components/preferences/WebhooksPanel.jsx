import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { LoadingSpinner } from '../common/LoadingSpinner'
import {
  Webhook,
  Plus,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Copy,
  ExternalLink,
  X,
  RefreshCw,
} from 'lucide-react'

const EVENT_OPTIONS = ['new_alert', 'new_incident', 'platform_alert']
const LEVEL_OPTIONS = ['', 'low', 'medium', 'high', 'critical']

const STATUS_DOT = ({ active }) => (
  <span className={`inline-block w-2.5 h-2.5 rounded-full ${active ? 'bg-green-400 shadow-[0_0_6px_#4ade80]' : 'bg-gray-500'}`} />
)

const TestResultBanner = ({ result, onClose }) => {
  if (!result) return null
  const success = result.success
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border text-sm mt-3 ${success ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
      {success ? <CheckCircle2 className="w-4 h-4 mt-0.5 flex-none" /> : <XCircle className="w-4 h-4 mt-0.5 flex-none" />}
      <div className="flex-1 min-w-0">
        {success
          ? <><span className="font-bold">Success</span> — HTTP {result.http_status}, {result.latency_ms}ms</>
          : <><span className="font-bold">Failed</span> — {result.error || `HTTP ${result.http_status}`}</>}
        {result.response_body && (
          <pre className="text-xs mt-1 opacity-70 truncate">{result.response_body.slice(0, 200)}</pre>
        )}
      </div>
      <button onClick={onClose} className="flex-none"><X className="w-3.5 h-3.5" /></button>
    </div>
  )
}

const AddWebhookModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({
    name: '',
    url: '',
    secret: '',
    events: ['new_alert'],
    filters: { min_threat_level: 'high', min_score: 0.6 },
    is_active: true,
  })

  const mutation = useMutation({
    mutationFn: () => apiClient.post('/api/webhooks', form),
    onSuccess: () => { onCreated(); onClose() },
  })

  const toggleEvent = (ev) => {
    setForm(f => ({
      ...f,
      events: f.events.includes(ev) ? f.events.filter(e => e !== ev) : [...f.events, ev],
    }))
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[var(--bg\_primary)] w-full max-w-lg rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[var(--border)] bg-black/20">
          <h3 className="font-bold text-lg flex items-center gap-2">
            <Webhook className="w-5 h-5 text-blue-400" /> Add Webhook
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-[var(--bg\_secondary)] rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1.5">Webhook Name</label>
            <input
              autoFocus
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g., Slack Critical Alerts"
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* URL */}
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1.5">Endpoint URL</label>
            <input
              value={form.url}
              onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
              placeholder="https://hooks.slack.com/services/T…"
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Secret */}
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1.5">
              HMAC Secret <span className="text-xs text-[var(--text\_secondary)]">(auto-generated if empty)</span>
            </label>
            <input
              value={form.secret}
              onChange={e => setForm(f => ({ ...f, secret: e.target.value }))}
              placeholder="my-webhook-secret"
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Events */}
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-2">Subscribe to Events</label>
            <div className="flex flex-wrap gap-2">
              {EVENT_OPTIONS.map(ev => (
                <button
                  key={ev}
                  onClick={() => toggleEvent(ev)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${form.events.includes(ev) ? 'bg-blue-500/20 border-blue-500/50 text-blue-300' : 'border-[var(--border)] text-[var(--text\_secondary)] hover:bg-[var(--bg\_secondary)]'}`}
                >
                  {ev}
                </button>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1.5">Min Threat Level</label>
              <select
                value={form.filters.min_threat_level}
                onChange={e => setForm(f => ({ ...f, filters: { ...f.filters, min_threat_level: e.target.value } }))}
                className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                {LEVEL_OPTIONS.map(l => <option key={l} value={l}>{l || 'All'}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1.5">Min Score</label>
              <input
                type="number"
                min="0" max="1" step="0.05"
                value={form.filters.min_score}
                onChange={e => setForm(f => ({ ...f, filters: { ...f.filters, min_score: parseFloat(e.target.value) } }))}
                className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 px-5 pb-5">
          <button onClick={onClose} className="flex-1 py-2.5 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg\_secondary)] transition-colors">Cancel</button>
          <button
            onClick={() => form.name && form.url && mutation.mutate()}
            disabled={!form.name || !form.url || mutation.isPending}
            className="flex-1 py-2.5 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <><RefreshCw className="w-4 h-4 animate-spin" /> Creating…</> : <><Webhook className="w-4 h-4" /> Create Webhook</>}
          </button>
        </div>

        {mutation.isError && (
          <div className="mx-5 mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs">
            Failed to create webhook: {mutation.error?.response?.data?.detail || mutation.error?.message}
          </div>
        )}
      </div>
    </div>
  )
}

export const WebhooksPanel = () => {
  const queryClient = useQueryClient()
  const [showAddModal, setShowAddModal] = useState(false)
  const [testResults, setTestResults] = useState({})

  const { data, isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: async () => { const r = await apiClient.get('/api/webhooks'); return r.data.webhooks },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => apiClient.delete(`/api/webhooks/${id}`),
    onSuccess: () => queryClient.invalidateQueries(['webhooks']),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }) => apiClient.put(`/api/webhooks/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries(['webhooks']),
  })

  const testMutation = useMutation({
    mutationFn: (id) => apiClient.post(`/api/webhooks/${id}/test`),
    onSuccess: (res, id) => setTestResults(prev => ({ ...prev, [id]: res.data })),
    onError: (err, id) => setTestResults(prev => ({ ...prev, [id]: { success: false, error: err.message } })),
  })

  const copySecret = (secret) => {
    navigator.clipboard.writeText(secret)
  }

  if (isLoading) return <div className="py-8 flex justify-center"><LoadingSpinner /></div>

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Webhook className="w-6 h-6 text-blue-500" /> API Webhooks
          </h2>
          <p className="text-[var(--text\_secondary)] text-sm mt-1">Push alerts to Slack, Teams, JIRA, and external systems.</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
        >
          <Plus className="w-4 h-4" /> Add Webhook
        </button>
      </div>

      {/* Payload format hint */}
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 text-xs text-[var(--text\_secondary)] font-mono">
        <div className="text-blue-400 font-bold mb-1.5">Outgoing payload format (HMAC-SHA256 signed):</div>
        {`{ "event_type": "new_alert", "timestamp": "ISO", "data": { "alert": { ... } } }`}
        <div className="mt-2 text-[var(--text\_secondary)]">Verify with header: <span className="text-blue-400">X-SOC-Signature: sha256=...</span></div>
      </div>

      {/* Webhooks Table */}
      {data?.length === 0 ? (
        <div className="bg-[var(--bg\_secondary)] border border-dashed border-[var(--border)] rounded-xl p-12 text-center">
          <Webhook className="w-10 h-10 text-[var(--text\_secondary)] mx-auto mb-3 opacity-40" />
          <p className="text-[var(--text\_secondary)] font-medium">No webhooks configured</p>
          <p className="text-xs text-[var(--text\_secondary)] mt-1">Add a webhook to start receiving alerts in Slack, Teams, or any HTTP endpoint.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data?.map(wh => (
            <div key={wh.webhook_id} className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden hover:border-blue-500/30 transition-colors">
              <div className="p-4 flex items-center gap-4">
                {/* Status */}
                <div className="flex-none">
                  <button
                    onClick={() => toggleMutation.mutate({ id: wh.webhook_id, is_active: !wh.is_active })}
                    title={wh.is_active ? 'Click to disable' : 'Click to enable'}
                    className="flex flex-col items-center gap-1"
                  >
                    <STATUS_DOT active={wh.is_active} />
                    <span className="text-[9px] text-[var(--text\_secondary)]">{wh.is_active ? 'ON' : 'OFF'}</span>
                  </button>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[var(--text\_primary)]">{wh.name}</span>
                    <div className="flex gap-1 flex-wrap">
                      {wh.events?.map(ev => (
                        <span key={ev} className="text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full">{ev}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <a
                      href={wh.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-[var(--text\_secondary)] font-mono hover:text-blue-400 flex items-center gap-1 truncate max-w-xs"
                    >
                      {wh.url} <ExternalLink className="w-3 h-3 flex-none" />
                    </a>
                  </div>
                  {wh.filters && Object.keys(wh.filters).length > 0 && (
                    <div className="text-[10px] text-[var(--text\_secondary)] mt-1">
                      Filters: {Object.entries(wh.filters).map(([k,v]) => `${k}: ${v}`).join(', ')}
                    </div>
                  )}
                </div>

                {/* Stats */}
                <div className="flex-none text-right text-xs text-[var(--text\_secondary)] hidden md:block">
                  <div className="text-green-400 font-mono">{wh.success_count} ✓</div>
                  <div className="text-red-400 font-mono">{wh.failure_count} ✗</div>
                </div>

                {/* Secret */}
                <div className="flex-none hidden lg:block">
                  <button
                    onClick={() => copySecret(wh.secret)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] bg-[var(--bg\_tertiary)] hover:bg-[var(--bg\_primary)] rounded border border-[var(--border)] transition-colors"
                    title="Copy HMAC Secret"
                  >
                    <Copy className="w-3 h-3" /> Secret
                  </button>
                </div>

                {/* Actions */}
                <div className="flex gap-2 flex-none">
                  <button
                    onClick={() => testMutation.mutate(wh.webhook_id)}
                    disabled={testMutation.isPending && testMutation.variables === wh.webhook_id}
                    title="Send test payload"
                    className="p-2 rounded-lg bg-green-500/10 hover:bg-green-500/20 text-green-400 transition-colors disabled:opacity-50"
                  >
                    {testMutation.isPending && testMutation.variables === wh.webhook_id
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => window.confirm(`Delete webhook "${wh.name}"?`) && deleteMutation.mutate(wh.webhook_id)}
                    title="Delete webhook"
                    className="p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Test Result */}
              {testResults[wh.webhook_id] && (
                <div className="px-4 pb-4">
                  <TestResultBanner
                    result={testResults[wh.webhook_id]}
                    onClose={() => setTestResults(prev => { const n = {...prev}; delete n[wh.webhook_id]; return n })}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <AddWebhookModal
          onClose={() => setShowAddModal(false)}
          onCreated={() => queryClient.invalidateQueries(['webhooks'])}
        />
      )}
    </div>
  )
}
