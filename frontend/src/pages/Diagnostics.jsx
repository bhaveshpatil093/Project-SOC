import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getKibanaHealth, getIndexStats, getDataFreshness, getLocalDbStats, testFetch } from '../api/diagnostics'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { Activity, Database, Clock, Server } from 'lucide-react'

// Simple Badge component fallback if not exported properly
const Badge = ({ variant, children }) => {
  const vClass = variant === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
  return <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${vClass}`}>{children}</span>
}

export const Diagnostics = () => {
  const [testIndex, setTestIndex] = useState('logs-system.syslog-*')
  const [testMinutes, setTestMinutes] = useState(5)
  const [testResult, setTestResult] = useState(null)
  const [testLoading, setTestLoading] = useState(false)
  const [testError, setTestError] = useState(null)

  const { data: kibanaHealth, isLoading: khLoading } = useQuery({
    queryKey: ['kibanaHealth'],
    queryFn: getKibanaHealth,
    refetchInterval: 30000,
  })

  const { data: indexStats, isLoading: isLoading } = useQuery({
    queryKey: ['indexStats'],
    queryFn: getIndexStats,
    refetchInterval: 30000,
  })

  const { data: dataFreshness, isLoading: dfLoading } = useQuery({
    queryKey: ['dataFreshness'],
    queryFn: getDataFreshness,
    refetchInterval: 30000,
  })

  const { data: localDbStats, isLoading: ldbLoading } = useQuery({
    queryKey: ['localDbStats'],
    queryFn: getLocalDbStats,
    refetchInterval: 30000,
  })

  const handleTestFetch = async (e) => {
    e.preventDefault()
    setTestLoading(true)
    setTestError(null)
    setTestResult(null)
    try {
      const res = await testFetch(testIndex, testMinutes)
      setTestResult(res)
    } catch (err) {
      setTestError(err.message || 'Test fetch failed')
    } finally {
      setTestLoading(false)
    }
  }

  const isLoadingData = khLoading || isLoading || dfLoading || ldbLoading

  return (
    <div className="flex flex-col min-h-screen bg-[var(--bg\_primary)] p-4 md:p-8">
      <h1 className="text-2xl font-bold mb-6">Platform Diagnostics</h1>
      
      {isLoadingData ? (
        <div className="flex justify-center my-12"><LoadingSpinner /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Kibana Health */}
          <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)]">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="h-5 w-5 text-blue-500" />
              <h2 className="text-lg font-semibold">Kibana Connection</h2>
            </div>
            <div className="flex flex-col space-y-2">
              <div className="flex justify-between items-center">
                <span>Status</span>
                <Badge variant={kibanaHealth?.connected ? 'success' : 'error'}>
                  {kibanaHealth?.connected ? 'CONNECTED' : 'DISCONNECTED'}
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>URL</span>
                <span className="font-mono text-sm text-[var(--text\_secondary)]">{kibanaHealth?.kibana_url}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Latency</span>
                <span className="font-mono text-sm">{kibanaHealth?.latency_ms} ms</span>
              </div>
            </div>
          </div>

          {/* Index Stats */}
          <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)]">
            <div className="flex items-center gap-3 mb-4">
              <Database className="h-5 w-5 text-purple-500" />
              <h2 className="text-lg font-semibold">Index Stats</h2>
            </div>
            <div className="space-y-3">
              {indexStats && Object.entries(indexStats).map(([idx, stats]) => (
                <div key={idx} className="flex justify-between items-center text-sm">
                  <span className="truncate w-40 text-[var(--text\_secondary)]" title={idx}>{idx.replace('logs-', '')}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono">{stats.doc_count.toLocaleString()} docs</span>
                    <Badge variant={stats.reachable ? 'success' : 'error'}>{stats.reachable ? 'OK' : 'ERR'}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Data Freshness */}
          <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)]">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="h-5 w-5 text-orange-500" />
              <h2 className="text-lg font-semibold">Data Freshness</h2>
            </div>
            <div className="space-y-3">
              {dataFreshness && Object.entries(dataFreshness).map(([key, timestamp]) => (
                <div key={key} className="flex justify-between items-center text-sm">
                  <span className="capitalize">{key}</span>
                  <span className="font-mono text-[var(--text\_secondary)]">{timestamp ? new Date(timestamp).toLocaleString() : 'N/A'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Local DB Stats */}
          <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)]">
            <div className="flex items-center gap-3 mb-4">
              <Server className="h-5 w-5 text-green-500" />
              <h2 className="text-lg font-semibold">Local SQLite Stats</h2>
            </div>
            <div className="flex flex-col space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span>Total Alerts</span>
                <span className="font-mono">{localDbStats?.alerts}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span>Open Alerts</span>
                <span className="font-mono">{localDbStats?.open_alerts}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span>Feedback Labels</span>
                <span className="font-mono">{localDbStats?.feedback}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span>Feature Vectors</span>
                <span className="font-mono">{localDbStats?.feature_vectors}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Test Fetch */}
      <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] max-w-4xl">
        <h2 className="text-lg font-semibold mb-4">Test Fetch (Kibana Proxy)</h2>
        <form onSubmit={handleTestFetch} className="flex gap-4 items-end mb-6">
          <div className="flex-1">
            <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">Index Pattern</label>
            <input 
              type="text" 
              value={testIndex} 
              onChange={e => setTestIndex(e.target.value)}
              className="w-full bg-[#1e1e1e] border border-[var(--border)] rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 text-white"
            />
          </div>
          <div className="w-24">
            <label className="block text-xs font-medium text-[var(--text\_secondary)] mb-1">Minutes</label>
            <input 
              type="number" 
              value={testMinutes} 
              onChange={e => setTestMinutes(e.target.value)}
              className="w-full bg-[#1e1e1e] border border-[var(--border)] rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 text-white"
            />
          </div>
          <button type="submit" disabled={testLoading} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50 transition-colors">
            {testLoading ? 'Running...' : 'Run Query'}
          </button>
        </form>

        {testError && <ErrorBanner message={testError} />}
        
        {testResult && (
          <div className="mt-4 animate-in fade-in duration-300">
            <p className="mb-2 text-sm"><span className="font-semibold text-green-400">Success:</span> Retrieved {testResult.doc_count} documents.</p>
            {testResult.sample && (
              <div className="bg-[#1e1e1e] p-4 rounded overflow-auto max-h-96 text-xs font-mono text-[#d4d4d4]">
                <pre>{JSON.stringify(testResult.sample, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
