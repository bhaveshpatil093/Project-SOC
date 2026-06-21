import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import {
  Activity,
  Server,
  Database,
  Cpu,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  PlayCircle,
  Clock,
  Terminal,
  Copy,
  LineChart
} from 'lucide-react'

// Recharts for timeline
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

export const SystemMonitor = () => {
  // Live System Metrics
  const { data: metrics } = useQuery({
    queryKey: ['systemMetrics'],
    queryFn: async () => {
      const res = await apiClient.get('/health/metrics')
      return res.data
    },
    refetchInterval: 10000
  })

  const { data: deepHealth } = useQuery({
    queryKey: ['deepHealthMonitor'],
    queryFn: async () => {
      const res = await apiClient.get('/health/deep')
      return res.data
    },
    refetchInterval: 10000
  })

  // WebSocket for active platform alerts
  const { connected } = useWebSocket()
  const { data: activeAlertsData } = useQuery({
    queryKey: ['platformAlertsActive'],
    queryFn: async () => {
      // In a real system, we'd fetch active alerts from an API.
      // Mocking for now as per instructions or fetching from an endpoint if available.
      try {
        const res = await apiClient.get('/api/admin/platform-alerts')
        return res.data
      } catch (e) {
        return []
      }
    },
    refetchInterval: 10000
  })

  // Mocking timeline and errors as per request
  const timelineData = Array.from({ length: 24 }).map((_, i) => ({
    hour: `${i}:00`,
    Ingestion: Math.random() > 0.1 ? 1 : 0,
    Features: Math.random() > 0.05 ? 1 : 0,
    Scoring: Math.random() > 0.05 ? 1 : 0,
    SLM: Math.random() > 0.02 ? 1 : 0,
  }))

  const mockErrors = Array.from({ length: 20 }).map((_, i) => ({
    id: i,
    timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString(),
    component: ['ingestion', 'elasticsearch', 'slm', 'scoring'][Math.floor(Math.random() * 4)],
    message: ['Connection timeout', 'Memory limit exceeded', 'Model load failed', 'Mapping parsing exception'][Math.floor(Math.random() * 4)],
    correlation_id: `corr-${Math.random().toString(36).substring(2, 10)}`
  })).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

  const renderProgressBar = (percent, colorClass) => (
    <div className="w-full bg-[var(--bg\_primary)] rounded-full h-2.5 border border-[var(--border)] overflow-hidden">
      <div className={`h-2.5 rounded-full ${colorClass}`} style={{ width: `${percent}%` }}></div>
    </div>
  )

  const getStatusIcon = (status) => {
    if (status === 'ok' || status === 'healthy') return <CheckCircle2 className="w-5 h-5 text-green-500" />
    if (status === 'degraded') return <AlertTriangle className="w-5 h-5 text-amber-500" />
    return <XCircle className="w-5 h-5 text-red-500" />
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[var(--text\_primary)] flex items-center gap-3">
          <Server className="w-8 h-8 text-blue-500 p-1.5 bg-blue-500/10 rounded-lg border border-blue-500/20" />
          System Operations Monitor
        </h1>
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${connected ? 'bg-green-400' : 'bg-red-400'}`}></span>
            <span className={`relative inline-flex rounded-full h-3 w-3 ${connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          </span>
          <span className="text-sm font-medium text-[var(--text\_secondary)]">Live Telemetry</span>
        </div>
      </div>

      {/* Section 1: Live System Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Hardware */}
        <div className="bg-[var(--bg\_secondary)] p-5 rounded-xl border border-[var(--border)] shadow-sm flex flex-col justify-between h-32">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold text-sm">
              <Cpu className="w-4 h-4" /> CPU Usage
            </div>
            <span className="font-mono font-bold text-[var(--text\_primary)]">{metrics?.cpu_percent || 0}%</span>
          </div>
          {renderProgressBar(metrics?.cpu_percent || 0, 'bg-blue-500')}
        </div>

        <div className="bg-[var(--bg\_secondary)] p-5 rounded-xl border border-[var(--border)] shadow-sm flex flex-col justify-between h-32">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold text-sm">
              <Activity className="w-4 h-4" /> Memory Usage
            </div>
            <span className="font-mono font-bold text-[var(--text\_primary)]">{metrics?.memory_percent || 0}%</span>
          </div>
          {renderProgressBar(metrics?.memory_percent || 0, 'bg-purple-500')}
        </div>

        <div className="bg-[var(--bg\_secondary)] p-5 rounded-xl border border-[var(--border)] shadow-sm flex flex-col justify-between h-32">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold text-sm">
              <HardDrive className="w-4 h-4" /> Disk Usage
            </div>
            <span className="font-mono font-bold text-[var(--text\_primary)]">{metrics?.disk_percent || 0}%</span>
          </div>
          {renderProgressBar(metrics?.disk_percent || 0, 'bg-orange-500')}
        </div>

        {/* Services */}
        <div className="bg-[var(--bg\_secondary)] p-5 rounded-xl border border-[var(--border)] shadow-sm flex justify-between items-center h-24">
          <div>
            <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold text-sm mb-1">
              <PlayCircle className="w-4 h-4" /> Pipeline Status
            </div>
            <div className="text-xs text-[var(--text\_secondary)] font-mono">Last run: {deepHealth?.ingestion?.last_run || 'Unknown'}</div>
          </div>
          <div className="flex flex-col items-end">
            {getStatusIcon(deepHealth?.ingestion?.status || 'ok')}
            <span className="text-sm font-bold uppercase mt-1 text-[var(--text\_primary)]">{deepHealth?.ingestion?.status || 'RUNNING'}</span>
          </div>
        </div>

        <div className="bg-[var(--bg\_secondary)] p-5 rounded-xl border border-[var(--border)] shadow-sm flex justify-between items-center h-24">
          <div>
            <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold text-sm mb-1">
              <Database className="w-4 h-4" /> ES Health
            </div>
            <div className="text-xs text-[var(--text\_secondary)] font-mono">Nodes: {deepHealth?.elasticsearch?.number_of_nodes || 1}</div>
          </div>
          <div className="flex flex-col items-end">
            {getStatusIcon(deepHealth?.elasticsearch?.status === 'green' ? 'healthy' : deepHealth?.elasticsearch?.status === 'yellow' ? 'degraded' : 'error')}
            <span className="text-sm font-bold uppercase mt-1 text-[var(--text\_primary)]">{deepHealth?.elasticsearch?.status || 'HEALTHY'}</span>
          </div>
        </div>

        <div className="bg-[var(--bg\_secondary)] p-5 rounded-xl border border-[var(--border)] shadow-sm flex justify-between items-center h-24">
          <div>
            <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold text-sm mb-1">
              <Server className="w-4 h-4" /> SLM Status
            </div>
            <div className="text-xs text-[var(--text\_secondary)] font-mono">Models: {deepHealth?.models?.loaded_models?.join(', ') || 'Phi-3-mini'}</div>
          </div>
          <div className="flex flex-col items-end">
            {getStatusIcon(deepHealth?.models?.status || 'ok')}
            <span className="text-sm font-bold uppercase mt-1 text-[var(--text\_primary)]">LOADED</span>
          </div>
        </div>
      </div>

      {/* Section 2: Active Platform Alerts */}
      <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-[var(--border)] bg-[var(--bg\_tertiary)] flex justify-between items-center">
          <h2 className="font-bold text-[var(--text\_primary)] flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" /> Active Platform Alerts
          </h2>
          <span className="px-2.5 py-1 rounded-full bg-red-500/10 text-red-500 text-xs font-bold">
            {activeAlertsData?.length || 0} Alerts
          </span>
        </div>
        <div className="p-4 space-y-3">
          {(!activeAlertsData || activeAlertsData.length === 0) ? (
            <div className="flex flex-col items-center justify-center py-8 text-[var(--text\_secondary)]">
              <CheckCircle2 className="w-12 h-12 text-green-500/50 mb-3" />
              <p className="font-medium text-sm">No active platform alerts.</p>
              <p className="text-xs">All systems nominal.</p>
            </div>
          ) : (
            activeAlertsData.map((alert, i) => (
              <div key={i} className="flex items-start justify-between p-4 rounded-lg border border-red-500/30 bg-red-500/5">
                <div className="flex gap-4">
                  <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-[var(--text\_primary)]">{alert.title}</h4>
                    <p className="text-sm text-[var(--text\_secondary)] mt-1">{alert.description}</p>
                    <div className="flex gap-3 mt-3 text-xs font-mono text-[var(--text\_secondary)]">
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Triggered {new Date(alert.triggered_at).toLocaleTimeString()}</span>
                      <span className="uppercase px-2 py-0.5 rounded bg-[var(--bg\_primary)] border border-[var(--border)] text-[var(--text\_primary)]">{alert.component}</span>
                    </div>
                  </div>
                </div>
                <button className="px-3 py-1.5 text-xs font-bold rounded-lg bg-[var(--bg\_primary)] border border-[var(--border)] hover:bg-[var(--bg\_tertiary)] text-[var(--text\_primary)] transition-colors">
                  Acknowledge
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Section 3: Pipeline Timeline */}
      <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-[var(--border)] bg-[var(--bg\_tertiary)]">
          <h2 className="font-bold text-[var(--text\_primary)] flex items-center gap-2">
            <LineChart className="w-5 h-5 text-blue-500" /> Pipeline Timeline (24h)
          </h2>
        </div>
        <div className="p-6 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={timelineData} layout="vertical" barSize={20}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis dataKey="hour" type="category" stroke="var(--text_secondary)" fontSize={12} width={60} />
              <Tooltip 
                cursor={{fill: 'var(--bg_tertiary)'}}
                contentStyle={{ backgroundColor: 'var(--bg_primary)', borderColor: 'var(--border)', color: 'var(--text_primary)' }}
              />
              <Bar dataKey="Ingestion" stackId="a" fill="#10b981" />
              <Bar dataKey="Features" stackId="a" fill="#3b82f6" />
              <Bar dataKey="Scoring" stackId="a" fill="#8b5cf6" />
              <Bar dataKey="SLM" stackId="a" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Section 4: Recent Errors Log */}
        <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm flex flex-col h-[500px]">
          <div className="p-4 border-b border-[var(--border)] bg-[var(--bg\_tertiary)] flex justify-between items-center shrink-0">
            <h2 className="font-bold text-[var(--text\_primary)] flex items-center gap-2">
              <Terminal className="w-5 h-5 text-purple-500" /> Recent Errors Log
            </h2>
            <span className="text-xs font-mono text-[var(--text\_secondary)]">structlog tail -n 20</span>
          </div>
          <div className="flex-1 overflow-y-auto bg-[var(--bg\_primary)]/50 p-4 space-y-2">
            {mockErrors.map((err) => (
              <div key={err.id} className="flex flex-col p-3 rounded-lg border border-[var(--border)] bg-[var(--bg\_secondary)] font-mono text-xs">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[var(--text\_secondary)]">{new Date(err.timestamp).toLocaleString()}</span>
                  <span className="uppercase px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 font-bold border border-purple-500/20">{err.component}</span>
                </div>
                <p className="text-red-400 font-semibold mb-2">{err.message}</p>
                <div className="flex items-center justify-between text-[var(--text\_secondary)] border-t border-[var(--border)] pt-2 mt-1">
                  <span>corr_id: {err.correlation_id}</span>
                  <button onClick={() => copyToClipboard(err.correlation_id)} className="hover:text-[var(--text\_primary)] transition-colors p-1" title="Copy Correlation ID">
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 5: Prometheus / Grafana Embedded */}
        <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm flex flex-col h-[500px]">
          <div className="p-4 border-b border-[var(--border)] bg-[var(--bg\_tertiary)] shrink-0">
            <h2 className="font-bold text-[var(--text\_primary)] flex items-center gap-2">
              <Activity className="w-5 h-5 text-orange-500" /> Prometheus Metrics View
            </h2>
          </div>
          <div className="flex-1 bg-[var(--bg\_primary)] relative">
            {/* Embedded Grafana iframe or placeholder */}
            <iframe 
              src="http://localhost:3001/d-solo/soc-dashboard/soc-platform-metrics?orgId=1&theme=dark&panelId=2" 
              width="100%" 
              height="100%" 
              frameBorder="0"
              title="Grafana Dashboard"
              className="absolute inset-0"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            ></iframe>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-[var(--text\_secondary)] -z-10 bg-[var(--bg\_primary)]">
              <Activity className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-sm font-medium">Grafana Dashboard Not Reachable</p>
              <p className="text-xs mt-1">Ensure localhost:3001 is running</p>
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}
