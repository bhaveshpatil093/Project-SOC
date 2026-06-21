import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Terminal, Search, Filter, RefreshCw, X, ChevronDown, ChevronRight, Activity } from 'lucide-react'

const LogEntry = ({ log, onTraceClick }) => {
  const [expanded, setExpanded] = useState(false)
  
  const levelColors = {
    DEBUG: 'border-l-gray-400 text-gray-400',
    INFO: 'border-l-blue-500 text-blue-400',
    WARNING: 'border-l-amber-500 text-amber-400',
    ERROR: 'border-l-red-500 text-red-400',
    CRITICAL: 'border-l-purple-500 text-purple-400'
  }

  const baseColor = levelColors[log.level] || 'border-l-gray-500 text-gray-400'
  
  return (
    <div className={`font-mono text-xs border-l-4 ${baseColor} bg-[var(--bg\_secondary)] mb-1 rounded-r-md overflow-hidden hover:bg-[var(--bg\_tertiary)] transition-colors`}>
      <div 
        className="px-3 py-2 cursor-pointer flex items-start gap-3"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-none opacity-60 w-4 h-4 mt-0.5">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
        <div className="flex-none opacity-70 w-36">
          {new Date(log.timestamp).toISOString().replace('T', ' ').substring(0, 19)}
        </div>
        <div className="flex-none w-16 font-bold">{log.level}</div>
        <div className="flex-none w-48 truncate opacity-80" title={log.logger_name}>
          [{log.logger_name}]
        </div>
        <div className="flex-1 break-words text-[var(--text\_primary)]">{log.message}</div>
      </div>
      
      {expanded && (
        <div className="px-10 py-3 bg-black/20 border-t border-[var(--border)] text-[var(--text\_secondary)]">
          <div className="grid grid-cols-[120px_1fr] gap-2 mb-2">
            <span className="opacity-60">Module:</span><span>{log.module}.{log.funcName}:{log.lineno}</span>
            <span className="opacity-60">Correlation ID:</span>
            <span>
              {log.correlation_id ? (
                <button 
                  onClick={(e) => { e.stopPropagation(); onTraceClick(log.correlation_id) }}
                  className="text-blue-400 hover:underline flex items-center gap-1"
                >
                  <Activity className="w-3 h-3" /> {log.correlation_id}
                </button>
              ) : '-'}
            </span>
          </div>
          {/* Try to parse JSON message if it looks like one */}
          {log.message.startsWith('{') && log.message.endsWith('}') && (
            <pre className="mt-2 p-2 bg-black/30 rounded text-xs overflow-x-auto">
              {JSON.stringify(JSON.parse(log.message), null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

const TraceModal = ({ correlationId, onClose }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['logTrace', correlationId],
    queryFn: async () => {
      const res = await apiClient.get(`/api/admin/logs/trace/${correlationId}`)
      return res.data.trace
    }
  })

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[var(--bg\_primary)] w-full max-w-5xl h-[80vh] rounded-xl border border-[var(--border)] shadow-2xl flex flex-col">
        <div className="p-4 border-b border-[var(--border)] flex justify-between items-center bg-[var(--bg\_secondary)] rounded-t-xl">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-500" />
              Request Trace
            </h2>
            <p className="text-xs font-mono text-[var(--text\_secondary)] mt-1">ID: {correlationId}</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-[var(--bg\_tertiary)] rounded-md transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 bg-[#0a0a0a]">
          {isLoading ? (
            <div className="flex items-center justify-center h-full"><LoadingSpinner /></div>
          ) : (
            <div>
              {data?.map((log, i) => (
                <LogEntry key={i} log={log} onTraceClick={() => {}} />
              ))}
              {data?.length === 0 && <div className="text-center text-gray-500 mt-10">No trace entries found.</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export const LogViewer = () => {
  const [level, setLevel] = useState('')
  const [component, setComponent] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const [traceId, setTraceId] = useState(null)
  
  const bottomRef = useRef(null)

  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['logs', level, component, searchQuery],
    queryFn: async () => {
      if (searchQuery) {
        const res = await apiClient.get(`/api/admin/logs/search?q=${searchQuery}`)
        return res.data.logs
      } else {
        const params = new URLSearchParams()
        if (level) params.append('level', level)
        if (component) params.append('component', component)
        const res = await apiClient.get(`/api/admin/logs?${params.toString()}`)
        return res.data.logs
      }
    },
    refetchInterval: 5000
  })

  // We want to reverse logs so oldest is at top, newest at bottom
  const logs = (logsData || []).slice().reverse()

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm bg-[#0a0a0a]">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3 bg-[var(--bg\_secondary)] border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-green-500" />
          <span className="font-bold text-[var(--text\_primary)]">Log Console</span>
        </div>
        
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text\_secondary)]" />
            <input 
              type="text" 
              placeholder="Search logs..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--bg\_primary)] border border-[var(--border)] rounded-md pl-9 pr-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center bg-[var(--bg\_primary)] border border-[var(--border)] rounded-md overflow-hidden text-xs font-bold">
            <button onClick={() => setLevel('')} className={`px-3 py-1.5 ${level === '' ? 'bg-gray-700 text-white' : 'hover:bg-[var(--bg\_tertiary)]'}`}>ALL</button>
            <button onClick={() => setLevel('INFO')} className={`px-3 py-1.5 border-l border-[var(--border)] ${level === 'INFO' ? 'bg-blue-600 text-white' : 'hover:bg-[var(--bg\_tertiary)] text-blue-400'}`}>INFO</button>
            <button onClick={() => setLevel('WARNING')} className={`px-3 py-1.5 border-l border-[var(--border)] ${level === 'WARNING' ? 'bg-amber-600 text-white' : 'hover:bg-[var(--bg\_tertiary)] text-amber-400'}`}>WARN</button>
            <button onClick={() => setLevel('ERROR')} className={`px-3 py-1.5 border-l border-[var(--border)] ${level === 'ERROR' ? 'bg-red-600 text-white' : 'hover:bg-[var(--bg\_tertiary)] text-red-400'}`}>ERROR</button>
          </div>

          <label className="flex items-center gap-2 text-sm text-[var(--text\_secondary)] cursor-pointer">
            <input 
              type="checkbox" 
              checked={autoScroll} 
              onChange={() => setAutoScroll(!autoScroll)}
              className="rounded border-[var(--border)] bg-[var(--bg\_primary)] text-blue-500 focus:ring-blue-500/20"
            />
            Auto-scroll
          </label>
        </div>
      </div>

      {/* Log Output */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading && !logs.length ? (
          <div className="flex items-center justify-center h-full"><LoadingSpinner /></div>
        ) : (
          <div>
            {logs.map((log, i) => (
              <LogEntry key={i} log={log} onTraceClick={setTraceId} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {traceId && <TraceModal correlationId={traceId} onClose={() => setTraceId(null)} />}
    </div>
  )
}
