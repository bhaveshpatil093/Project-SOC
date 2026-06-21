import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { ShieldAlert, Clock, Activity, Target } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

export const SLADashboard = () => {
  const { data: slaData, isLoading } = useQuery({
    queryKey: ['slaDashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/api/sla/dashboard')
      return res.data
    },
    refetchInterval: 30000
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>
  }

  if (!slaData) return null

  const complianceData = [
    {
      level: 'Critical',
      Met: slaData.by_level.critical.met,
      Breached: slaData.by_level.critical.breached,
      Pending: slaData.by_level.critical.pending
    },
    {
      level: 'High',
      Met: slaData.by_level.high.met,
      Breached: slaData.by_level.high.breached,
      Pending: slaData.by_level.high.pending
    },
    {
      level: 'Medium',
      Met: slaData.by_level.medium.met,
      Breached: slaData.by_level.medium.breached,
      Pending: slaData.by_level.medium.pending
    },
    {
      level: 'Low',
      Met: slaData.by_level.low.met,
      Breached: slaData.by_level.low.breached,
      Pending: slaData.by_level.low.pending
    }
  ]

  const avgTimeData = [
    { level: 'Critical', Ack: slaData.avg_acknowledge_time_minutes.critical || 0, Triage: slaData.avg_triage_time_minutes.critical || 0 },
    { level: 'High', Ack: slaData.avg_acknowledge_time_minutes.high || 0, Triage: slaData.avg_triage_time_minutes.high || 0 },
    { level: 'Medium', Ack: slaData.avg_acknowledge_time_minutes.medium || 0, Triage: slaData.avg_triage_time_minutes.medium || 0 },
    { level: 'Low', Ack: slaData.avg_acknowledge_time_minutes.low || 0, Triage: slaData.avg_triage_time_minutes.low || 0 },
  ]

  const isBreachRateCritical = slaData.sla_breach_rate_24h > 5

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm flex flex-col justify-center items-center">
          <div className="flex items-center gap-2 text-[var(--text\_secondary)] font-semibold mb-4 uppercase tracking-wider text-sm">
            <Target className="w-5 h-5 text-blue-500" />
            SLA Breach Rate (24h)
          </div>
          <div className={`text-5xl font-black ${isBreachRateCritical ? 'text-red-500' : 'text-green-500'}`}>
            {slaData.sla_breach_rate_24h}%
          </div>
          <div className="mt-3 text-xs text-[var(--text\_secondary)] font-medium">
            Target: &lt; 5.0%
          </div>
        </div>

        <div className="md:col-span-2 bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--text\_secondary)] mb-4 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-500" />
            Per-Level SLA Compliance
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={complianceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="level" stroke="var(--text_secondary)" fontSize={12} />
                <YAxis stroke="var(--text_secondary)" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg_primary)', borderColor: 'var(--border)' }} />
                <Legend />
                <Bar dataKey="Met" stackId="a" fill="#10b981" />
                <Bar dataKey="Pending" stackId="a" fill="#f59e0b" />
                <Bar dataKey="Breached" stackId="a" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--text\_secondary)] mb-4 uppercase tracking-wider flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-500" />
            Avg Response Times (Minutes)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={avgTimeData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" stroke="var(--text_secondary)" fontSize={12} />
                <YAxis dataKey="level" type="category" stroke="var(--text_secondary)" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg_primary)', borderColor: 'var(--border)' }} />
                <Legend />
                <Bar dataKey="Ack" fill="#3b82f6" name="Acknowledge" />
                <Bar dataKey="Triage" fill="#8b5cf6" name="Triage" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm flex flex-col h-[340px]">
          <div className="p-4 border-b border-[var(--border)] bg-[var(--bg\_tertiary)] flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            <h3 className="font-semibold text-[var(--text\_primary)]">Top Breached Alerts</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {slaData.breached_alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-[var(--text\_secondary)]">
                <Target className="w-10 h-10 mb-2 opacity-50" />
                <p>No SLA breaches found.</p>
              </div>
            ) : (
              <ul className="space-y-3">
                {slaData.breached_alerts.map((alert, i) => (
                  <li key={i} className="p-3 bg-[var(--bg\_primary)] border border-red-500/30 rounded-lg flex justify-between items-center">
                    <div>
                      <p className="font-mono text-sm font-bold text-[var(--text\_primary)]">{alert.alert_id}</p>
                      <p className="text-xs text-[var(--text\_secondary)] mt-1">Level: <span className="uppercase font-semibold text-red-400">{alert.threat_level}</span></p>
                    </div>
                    <div className="text-right text-xs">
                      <p className="text-red-500 font-bold uppercase mb-1">Breached</p>
                      <p className="text-[var(--text\_secondary)] font-mono">{new Date(alert.created_at).toLocaleString()}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
