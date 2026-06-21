import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { Badge } from '../components/common/Badge'
import { SLADashboard } from '../components/reports/SLADashboard'
import { formatDate } from '../utils/formatters'
import {
  FileText,
  Clock,
  Calendar,
  Play,
  Copy,
  Download,
  Plus,
  RefreshCw,
  X,
  FileCheck,
} from 'lucide-react'

// Render a clean markdown preview
const MarkdownViewer = ({ markdown }) => {
  return (
    <div
      className="prose prose-invert prose-sm max-w-none 
      prose-headings:text-gray-100 prose-headings:font-black prose-headings:tracking-tight 
      prose-h1:text-2xl prose-h1:border-b prose-h1:border-gray-800 prose-h1:pb-2
      prose-h2:text-lg prose-h2:text-blue-400 prose-h2:mt-6 prose-h2:mb-3
      prose-p:text-gray-300 prose-p:leading-relaxed
      prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
      prose-strong:text-gray-100
      prose-ul:list-disc prose-ul:pl-5 prose-li:text-gray-300 prose-li:mb-1
      prose-table:w-full prose-table:text-left prose-table:border-collapse
      prose-th:bg-gray-800/50 prose-th:p-2 prose-th:text-gray-300 prose-th:border prose-th:border-gray-700
      prose-td:p-2 prose-td:border prose-td:border-gray-800 prose-td:text-gray-300
      prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-500/10 prose-blockquote:p-3 prose-blockquote:text-gray-300 prose-blockquote:italic
      bg-[#0f1115] p-8 rounded-xl border border-gray-800"
      dangerouslySetInnerHTML={{
        __html: markdown
          .replace(/^# (.*$)/gim, '<h1>$1</h1>')
          .replace(/^## (.*$)/gim, '<h2>$1</h2>')
          .replace(/^### (.*$)/gim, '<h3>$1</h3>')
          .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
          .replace(/\*(.*)\*/gim, '<em>$1</em>')
          .replace(/!\[(.*?)\]\((.*?)\)/gim, "<img alt='$1' src='$2' />")
          .replace(/\[(.*?)\]\((.*?)\)/gim, "<a href='$2'>$1</a>")
          .replace(/\n$/gim, '<br />')
          .replace(/---/gim, '<hr className="border-gray-800 my-6"/>')
          .replace(/> (.*$)/gim, '<blockquote>$1</blockquote>')
          .replace(/`(.*?)`/gim, '<code className="bg-gray-800 px-1 py-0.5 rounded text-pink-400">$1</code>')
          // Basic table support hack for this specific format
          .replace(/\|(.+)\|/gim, (match) => {
            if (match.includes('---')) return '' // Skip separator
            const isHeader = match.includes('Metric') || match.includes('Level') || match.includes('Status') || match.includes('Entity') || match.includes('Attack Stage')
            const cols = match.split('|').filter(c => c.trim())
            const tag = isHeader ? 'th' : 'td'
            return `<tr>${cols.map(c => `<${tag}>${c.trim()}</${tag}>`).join('')}</tr>`
          })
          .replace(/(<tr>.*?<\/tr>)/g, '<table>$1</table>')
          .replace(/<\/table>\s*<table>/g, '') // Merge adjacent tables
      }}
    />
  )
}

const CreateScheduleModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({
    name: '',
    report_type: 'daily',
    frequency: 'daily',
    format: 'markdown',
  })
  
  const mutation = useMutation({
    mutationFn: () => apiClient.post('/api/reports/schedules', form),
    onSuccess: () => { onCreated(); onClose() },
  })

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[var(--bg\_primary)] w-full max-w-md rounded-2xl border border-[var(--border)] shadow-2xl p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-lg flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-400" /> Create Schedule
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-[var(--bg\_secondary)] rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1">Schedule Name</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g., Executive Weekly Summary"
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1">Report Type</label>
            <select
              value={form.report_type}
              onChange={e => setForm(f => ({ ...f, report_type: e.target.value }))}
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="shift">Shift Handover (8h)</option>
              <option value="daily">Daily Summary</option>
              <option value="weekly">Weekly Threat Digest</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text\_secondary)] mb-1">Frequency</label>
            <select
              value={form.frequency}
              onChange={e => setForm(f => ({ ...f, frequency: e.target.value }))}
              className="w-full bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="every_8h">Every 8 Hours</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 mt-8">
          <button onClick={onClose} className="flex-1 py-2 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg\_secondary)] transition-colors">Cancel</button>
          <button
            onClick={() => form.name && mutation.mutate()}
            disabled={!form.name || mutation.isPending}
            className="flex-1 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Create Schedule'}
          </button>
        </div>
      </div>
    </div>
  )
}

const SchedulesTab = () => {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [runningId, setRunningId] = useState(null)

  const { data: schedules, isLoading } = useQuery({
    queryKey: ['schedules'],
    queryFn: async () => { const r = await apiClient.get('/api/reports/schedules'); return r.data.schedules }
  })

  const runMutation = useMutation({
    mutationFn: (id) => apiClient.post(`/api/reports/schedules/${id}/run-now`),
    onMutate: (id) => setRunningId(id),
    onSettled: () => { setRunningId(null); queryClient.invalidateQueries(['schedules']); queryClient.invalidateQueries(['generatedReports']) }
  })

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
        >
          <Plus className="w-4 h-4" /> Create Schedule
        </button>
      </div>

      <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-black/20 text-xs uppercase text-[var(--text\_secondary)] border-b border-[var(--border)]">
            <tr>
              <th className="px-6 py-4 font-semibold">Schedule Name</th>
              <th className="px-6 py-4 font-semibold">Type</th>
              <th className="px-6 py-4 font-semibold">Frequency</th>
              <th className="px-6 py-4 font-semibold">Last Run</th>
              <th className="px-6 py-4 font-semibold">Next Run</th>
              <th className="px-6 py-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {schedules?.map(s => (
              <tr key={s.schedule_id} className="hover:bg-[var(--bg\_tertiary)]/50 transition-colors">
                <td className="px-6 py-4 font-bold text-[var(--text\_primary)]">{s.name}</td>
                <td className="px-6 py-4">
                  <Badge variant={s.report_type === 'shift' ? 'critical' : s.report_type === 'daily' ? 'high' : 'medium'}>{s.report_type}</Badge>
                </td>
                <td className="px-6 py-4 text-[var(--text\_secondary)] capitalize">{s.frequency.replace('_', ' ')}</td>
                <td className="px-6 py-4 text-[var(--text\_secondary)] font-mono text-xs">{s.last_run ? formatDate(s.last_run) : 'Never'}</td>
                <td className="px-6 py-4 text-[var(--text\_secondary)] font-mono text-xs">{formatDate(s.next_run)}</td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => runMutation.mutate(s.schedule_id)}
                    disabled={runningId === s.schedule_id}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/20 rounded text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    {runningId === s.schedule_id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    Run Now
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {schedules?.length === 0 && <div className="p-8 text-center text-[var(--text\_secondary)]">No schedules defined.</div>}
      </div>

      {showModal && <CreateScheduleModal onClose={() => setShowModal(false)} onCreated={() => queryClient.invalidateQueries(['schedules'])} />}
    </div>
  )
}

const GeneratedReportsTab = () => {
  const [selectedReportId, setSelectedReportId] = useState(null)
  
  const { data: reportsList, isLoading } = useQuery({
    queryKey: ['generatedReports'],
    queryFn: async () => { const r = await apiClient.get('/api/reports/generated'); return r.data.reports }
  })

  const { data: activeReport, isLoading: isReportLoading } = useQuery({
    queryKey: ['reportDetail', selectedReportId],
    queryFn: async () => { const r = await apiClient.get(`/api/reports/generated/${selectedReportId}`); return r.data.report },
    enabled: !!selectedReportId
  })

  const handleCopy = () => {
    if (activeReport?.content_markdown) {
      navigator.clipboard.writeText(activeReport.content_markdown)
      alert('Markdown copied to clipboard')
    }
  }

  const handlePrint = () => {
    window.print()
  }

  if (isLoading) return <LoadingSpinner />

  if (selectedReportId) {
    return (
      <div className="space-y-4">
        <button onClick={() => setSelectedReportId(null)} className="text-sm text-[var(--text\_secondary)] hover:text-blue-400 flex items-center gap-1">
          ← Back to Reports
        </button>
        {isReportLoading ? (
          <LoadingSpinner />
        ) : activeReport ? (
          <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-2xl print:shadow-none print:border-none">
            <div className="p-4 bg-black/20 border-b border-[var(--border)] flex justify-between items-center print:hidden">
              <div className="flex items-center gap-3">
                <FileCheck className="w-5 h-5 text-blue-400" />
                <span className="font-bold">{activeReport.schedule_name || 'Generated Report'}</span>
                <span className="text-xs text-[var(--text\_secondary)] font-mono">{formatDate(activeReport.generated_at)}</span>
              </div>
              <div className="flex gap-2">
                <button onClick={handleCopy} className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bg\_tertiary)] hover:bg-[var(--bg\_primary)] border border-[var(--border)] rounded text-xs transition-colors">
                  <Copy className="w-3.5 h-3.5" /> Copy Markdown
                </button>
                <button onClick={handlePrint} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition-colors">
                  <Download className="w-3.5 h-3.5" /> Export PDF
                </button>
              </div>
            </div>
            <div className="p-6 bg-[#0f1115]">
              <MarkdownViewer markdown={activeReport.content_markdown} />
            </div>
          </div>
        ) : (
          <div className="p-8 text-red-400 text-center">Failed to load report.</div>
        )}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
      {reportsList?.map(r => (
        <button
          key={r.report_id}
          onClick={() => setSelectedReportId(r.report_id)}
          className="bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] hover:border-blue-500/50 border border-[var(--border)] rounded-xl p-5 text-left transition-all group relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/50 group-hover:bg-blue-400 transition-colors" />
          <h4 className="font-bold text-[var(--text\_primary)] mb-1 truncate pr-6">{r.schedule_name || 'Manual Report'}</h4>
          <p className="text-xs text-[var(--text\_secondary)] flex items-center gap-1 mb-4">
            <Clock className="w-3 h-3" /> {formatDate(r.generated_at)}
          </p>
          <div className="grid grid-cols-2 gap-2 mt-auto">
            <div className="bg-[var(--bg\_primary)] p-2 rounded border border-[var(--border)]">
              <div className="text-[10px] text-[var(--text\_secondary)] uppercase font-bold">Alerts</div>
              <div className="font-mono text-sm">{r.stats?.total_alerts || 0}</div>
            </div>
            <div className="bg-red-500/10 p-2 rounded border border-red-500/20 text-red-400">
              <div className="text-[10px] uppercase font-bold">Critical</div>
              <div className="font-mono text-sm">{r.stats?.critical_alerts || 0}</div>
            </div>
          </div>
        </button>
      ))}
      {reportsList?.length === 0 && <div className="col-span-full p-12 text-center text-[var(--text\_secondary)]">No reports generated yet. Run a schedule to create one.</div>}
    </div>
  )
}

const Reports = () => {
  const [activeTab, setActiveTab] = useState('generated') // schedules, generated, sla

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text\_primary)] flex items-center gap-3">
            <span className="p-2 bg-blue-500/10 border border-blue-500/20 rounded-xl">
              <FileText className="w-6 h-6 text-blue-400" />
            </span>
            Automated Reports
          </h1>
          <p className="text-[var(--text\_secondary)] text-sm mt-1">
            Configure periodic shift handovers, daily summaries, and SLA compliance.
          </p>
        </div>

        <div className="flex bg-[var(--bg\_secondary)] p-1 rounded-xl border border-[var(--border)]">
          <button
            onClick={() => setActiveTab('generated')}
            className={`px-4 py-2 text-sm font-bold rounded-lg transition-colors ${activeTab === 'generated' ? 'bg-blue-600 text-white shadow-md' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            Generated Reports
          </button>
          <button
            onClick={() => setActiveTab('schedules')}
            className={`px-4 py-2 text-sm font-bold rounded-lg transition-colors ${activeTab === 'schedules' ? 'bg-blue-600 text-white shadow-md' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            Schedules
          </button>
          <button
            onClick={() => setActiveTab('sla')}
            className={`px-4 py-2 text-sm font-bold rounded-lg transition-colors ${activeTab === 'sla' ? 'bg-blue-600 text-white shadow-md' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            SLA Dashboard
          </button>
        </div>
      </div>

      <div className="print:block">
        {activeTab === 'schedules' && <SchedulesTab />}
        {activeTab === 'generated' && <GeneratedReportsTab />}
        {activeTab === 'sla' && <SLADashboard />}
      </div>
    </div>
  )
}

export default Reports
