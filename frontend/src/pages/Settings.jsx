import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { triggerScoring } from '../api/alerts'
import {
  getModelInfo,
  reloadModel,
  getRagStats,
  reindexRag,
  clearRagIndex,
  getSlmMetrics,
} from '../api/slm'
import { useWebSocket } from '../hooks/useWebSocket'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import {
  Server,
  Database,
  Activity,
  GitCommit,
  RefreshCw,
  CheckCircle,
  Play,
  XCircle,
  Bot,
  MonitorDot,
  Cpu,
  Network,
  LineChart,
  Zap,
  Webhook,
} from 'lucide-react'
import { formatDate } from '../utils/formatters'

import { PreferencesForm } from '../components/preferences/PreferencesForm'
import { BackupsPanel } from "../components/preferences/BackupsPanel"
import { AuditLogPanel } from "../components/preferences/AuditLogPanel"
import { SLMAnalyticsPanel } from "../components/preferences/SLMAnalyticsPanel"
import { WebhooksPanel } from '../components/preferences/WebhooksPanel'

export const Settings = () => {

  // Advanced ES Tool State
  const [esQuery, setEsQuery] = useState(
    '{\n  "query": {"match_all": {}},\n  "size": 10,\n  "sort": [{"@timestamp": {"order": "desc"}}]\n}',
  )
  const [selectedIdx, setSelectedIdx] = useState('soc-processed-alerts')
  const [queryResult, setQueryResult] = useState('')
  const [isQuerying, setIsQuerying] = useState(false)

  const { data: kibanaUrlData } = useQuery({ queryKey: ['kibanaUrl'], queryFn: getKibanaUrl })
  const { data: esIndicesData } = useQuery({
    queryKey: ['esIndices'],
    queryFn: getEsIndices,
    refetchInterval: 60000,
  })

  const handleRunQuery = async () => {
    setIsQuerying(true)
    try {
      const parsedQuery = JSON.parse(esQuery)
      const payload = {
        index: selectedIdx,
        query: parsedQuery.query || { match_all: {} },
        size: parsedQuery.size || 10,
        sort: parsedQuery.sort || [],
      }
      const result = await runEsQuery(payload)
      setQueryResult(JSON.stringify(result.data, null, 2))
    } catch (e) {
      setQueryResult(JSON.stringify({ error: e.message }, null, 2))
    } finally {
      setIsQuerying(false)
    }
  }

  const [activeTab, setActiveTab] = useState('health')
  const queryClient = useQueryClient()
  const { connected: wsConnected, reconnecting: wsReconnecting } = useWebSocket()
  const [actionResult, setActionResult] = useState(null)

  // Health Queries
  const { data: deepHealth, isLoading: healthLoading } = useQuery({
    queryKey: ['healthDeep'],
    queryFn: () => apiClient.get('/health/deep'),
    refetchInterval: 30000,
  })

  const { data: ingestion, isLoading: ingestionLoading } = useQuery({
    queryKey: ['ingestionStatus'],
    queryFn: () => apiClient.get('/api/ingestion/status'),
    refetchInterval: 30000,
  })

  const {
    data: slmModelInfo,
    isLoading: slmLoading,
    refetch: refetchSlm,
  } = useQuery({
    queryKey: ['slmModelInfo'],
    queryFn: getModelInfo,
    refetchInterval: 30000,
  })

  const {
    data: ragStats,
    isLoading: ragLoading,
    refetch: refetchRag,
  } = useQuery({
    queryKey: ['ragStats'],
    queryFn: getRagStats,
    refetchInterval: 30000,
  })

  const {
    data: slmMetrics,
    isLoading: metricsLoading,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ['slmMetrics'],
    queryFn: () => getSlmMetrics(24),
    refetchInterval: 30000,
  })

  const refreshStatus = () => {
    queryClient.invalidateQueries({ queryKey: ['healthDeep'] })
    queryClient.invalidateQueries({ queryKey: ['ingestionStatus'] })
    refetchSlm()
    refetchRag()
    refetchMetrics()
  }

  // Mutations
  const ingestionMutation = useMutation({
    mutationFn: () => apiClient.post('/api/ingestion/run'),
    onSuccess: (res) => {
      setActionResult({
        type: 'ingestion',
        msg: `Ingested ${res.docs_ingested || 0} documents successfully.`,
      })
      refreshStatus()
    },
    onError: (err) => setActionResult({ type: 'ingestion', err: err.message }),
  })

  const featureMutation = useMutation({
    mutationFn: () => apiClient.get('/api/features/run'),
    onSuccess: (res) => {
      setActionResult({
        type: 'feature',
        msg: `Extracted ${res.total_features || 'new'} feature vectors successfully.`,
      })
    },
    onError: (err) => setActionResult({ type: 'feature', err: err.message }),
  })

  const scoringMutation = useMutation({
    mutationFn: triggerScoring,
    onSuccess: (res) => {
      setActionResult({
        type: 'scoring',
        msg: `Scored ${res.scored || 0} entities, triggered ${res.alerts_above_threshold || 0} alerts.`,
      })
    },
    onError: (err) => setActionResult({ type: 'scoring', err: err.message }),
  })

  const reloadModelMutation = useMutation({
    mutationFn: (model) => reloadModel(model),
    onSuccess: (res) => {
      setActionResult({
        type: 'slm',
        msg: `Successfully reloaded SLM Engine onto ${res.model_name}`,
      })
      refetchSlm()
    },
    onError: (err) => setActionResult({ type: 'slm', err: err.message }),
  })

  const reindexRagMutation = useMutation({
    mutationFn: reindexRag,
    onSuccess: (res) => {
      setActionResult({
        type: 'rag',
        msg: `RAG re-index job started globally. Job ID: ${res.job_id}`,
      })
      setTimeout(refetchRag, 5000)
    },
    onError: (err) => setActionResult({ type: 'rag', err: err.message }),
  })

  const clearRagMutation = useMutation({
    mutationFn: clearRagIndex,
    onSuccess: (res) => {
      setActionResult({ type: 'rag', msg: res.message })
      refetchRag()
    },
    onError: (err) => setActionResult({ type: 'rag', err: err.message }),
  })

  const handleAction = (mutationObj, type) => {
    setActionResult(null)
    mutationObj.mutate()
  }

  const ActionBox = ({ title, icon: Icon, description, mutation, type }) => (
    <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl p-6 flex flex-col items-start transition-all hover:border-[var(--border)]">
      <div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg mb-4">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-lg font-bold text-[var(--text\_primary)] mb-2">{title}</h3>
      <p className="text-sm text-[var(--text\_secondary)] mb-6 flex-1">{description}</p>

      <button
        onClick={() => handleAction(mutation, type)}
        disabled={mutation.isPending}
        className="w-full bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] disabled:opacity-50 text-[var(--text\_primary)] font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors mb-4"
      >
        {mutation.isPending ? (
          <RefreshCw className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {title}
      </button>

      {actionResult?.type === type && actionResult?.msg && (
        <div className="w-full bg-green-500/10 border border-green-500/30 text-green-400 text-xs px-3 py-2 rounded-lg flex items-start gap-2">
          <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{actionResult.msg}</span>
        </div>
      )}
      {actionResult?.type === type && actionResult?.err && (
        <div className="w-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-3 py-2 rounded-lg flex items-start gap-2">
          <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{actionResult.err}</span>
        </div>
      )}
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-[var(--text\_primary)] tracking-tight">
            System Settings
          </h1>
          <p className="text-[var(--text\_secondary)] mt-1">
            Configure preferences, monitor health, and run manual orchestrations.
          </p>
        </div>
        <div className="flex items-center gap-4">
          {activeTab === 'health' && (
            <button
              onClick={refreshStatus}
              className="flex items-center gap-2 bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] text-[var(--text\_primary)] px-4 py-2 rounded-lg text-sm font-medium border border-[var(--border)] transition-colors"
            >
              <RefreshCw className="h-4 w-4" /> Refresh Status
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 border-b border-[var(--border)] mb-6">
        <button
          onClick={() => setActiveTab('health')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'health'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:border-[var(--border)]'
          }`}
        >
          System Health & Diagnostics
        </button>
        <button
          onClick={() => setActiveTab('preferences')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'preferences'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:border-[var(--border)]'
          }`}
        >
          Analyst Preferences
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'audit'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-[var(--text\\_secondary)] hover:text-[var(--text\\_primary)] hover:border-[var(--border)]'
          }`}
        >
          Audit Log
        </button>
        <button
          onClick={() => setActiveTab('slm_analytics')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'slm_analytics'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:border-[var(--border)]'
          }`}
        >
          SLM Analytics
        </button>
        <button
          onClick={() => setActiveTab('teams')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'teams'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:border-[var(--border)]'
          }`}
        >
          Analyst Teams
        </button>
        <button
          onClick={() => setActiveTab('webhooks')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'webhooks'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:border-[var(--border)]'
          }`}
        >
          Webhooks
        </button>
      </div>

      {activeTab === 'preferences' && <PreferencesForm />}
      {activeTab === "backups" && <BackupsPanel />}
      {activeTab === "audit" && <AuditLogPanel />}
      {activeTab === "slm_analytics" && <SLMAnalyticsPanel />}
      {activeTab === "teams" && <TeamsPanel />}
      {activeTab === "webhooks" && <WebhooksPanel />}



      {activeTab === 'health' && (
        <>
          {/* SECTION 1: Deep Health Panel */}
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg">
            <div className="flex justify-between items-center mb-6">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('general')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'general' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  General
                </button>
                <button
                  onClick={() => setActiveTab('advanced')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'advanced' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  Advanced
                </button>
              </div>
              <h2 className="text-xl font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <Activity className="h-5 w-5 text-blue-400" />
                Platform Deep Health
              </h2>
              {healthLoading ? (
                <LoadingSpinner size={4} />
              ) : (
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                    deepHealth?.status === 'healthy'
                      ? 'bg-green-500/10 text-green-500 border-green-500/30'
                      : deepHealth?.status === 'degraded'
                        ? 'bg-orange-500/10 text-orange-500 border-orange-500/30'
                        : 'bg-red-500/10 text-red-500 border-red-500/30'
                  }`}
                >
                  {deepHealth?.status || 'Unknown'}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {deepHealth?.components?.map((comp) => (
                <div
                  key={comp.name}
                  className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg p-4 flex flex-col justify-between"
                >
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="text-sm font-bold text-[var(--text\_primary)] capitalize">
                      {comp.name.replace('_', ' ')}
                    </h3>
                    <span
                      className={`flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        comp.status === 'healthy'
                          ? 'bg-green-500/10 text-green-500'
                          : comp.status === 'degraded'
                            ? 'bg-orange-500/10 text-orange-500'
                            : 'bg-red-500/10 text-red-500'
                      }`}
                    >
                      <div
                        className={`w-1.5 h-1.5 rounded-full ${
                          comp.status === 'healthy'
                            ? 'bg-green-500'
                            : comp.status === 'degraded'
                              ? 'bg-orange-500 animate-pulse'
                              : 'bg-red-500'
                        }`}
                      />
                      {comp.status}
                    </span>
                  </div>
                  <div className="space-y-1 mt-auto">
                    <p className="text-xs text-[var(--text\_secondary)] flex justify-between">
                      <span>Latency</span>
                      <span className="font-mono text-[var(--text\_secondary)]">
                        {comp.latency_ms?.toFixed(1) || 0} ms
                      </span>
                    </p>
                    {Object.entries(comp.details || {})
                      .slice(0, 2)
                      .map(([k, v]) => (
                        <p
                          key={k}
                          className="text-xs text-[var(--text\_secondary)] flex justify-between"
                        >
                          <span className="capitalize">{k.replace(/_/g, ' ')}</span>
                          <span
                            className="font-mono text-[var(--text\_secondary)] truncate max-w-[120px]"
                            title={String(v)}
                          >
                            {String(v)}
                          </span>
                        </p>
                      ))}
                  </div>
                </div>
              ))}
              {(!deepHealth?.components || deepHealth.components.length === 0) &&
                !healthLoading && (
                  <div className="col-span-full py-8 text-center text-[var(--text\_secondary)] text-sm">
                    No health data available. Server might be offline.
                  </div>
                )}
            </div>
          </div>

          {/* SECTION SLM MODEL PANEL */}
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('general')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'general' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  General
                </button>
                <button
                  onClick={() => setActiveTab('advanced')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'advanced' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  Advanced
                </button>
              </div>
              <h2 className="text-xl font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <Cpu className="h-5 w-5 text-blue-400" />
                SLM Engine Configuration
              </h2>
              {slmLoading || reloadModelMutation.isPending ? (
                <span className="flex items-center gap-2 text-sm text-[var(--text\_secondary)]">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-500" /> Hot-reloading
                  tensors...
                </span>
              ) : (
                <span
                  className={`text-xs font-bold px-2 py-1 rounded-full border ${slmModelInfo?.is_finetuned ? 'bg-purple-500/10 text-purple-400 border-purple-500/30' : 'bg-[var(--bg\_tertiary)]/50 text-[var(--text\_secondary)] border-[var(--border)]'}`}
                >
                  {slmModelInfo?.is_finetuned ? 'Fine-Tuned Adapter Active' : 'Base Model Active'}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  Current Model
                </h4>
                <p
                  className="text-sm text-[var(--text\_primary)] truncate"
                  title={slmModelInfo?.model_name || 'Loading...'}
                >
                  {slmModelInfo?.model_name || 'Loading...'}
                </p>
              </div>
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  Hardware Device
                </h4>
                <p className="text-sm text-[var(--text\_primary)] uppercase font-mono">
                  {slmModelInfo?.device || 'N/A'}
                </p>
              </div>
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  VRAM Footprint
                </h4>
                <p className="text-sm text-[var(--text\_primary)]">
                  {slmModelInfo?.estimated_memory_mb
                    ? `${Math.round(slmModelInfo.estimated_memory_mb)} MB`
                    : 'N/A'}
                </p>
              </div>
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  Load Latency
                </h4>
                <p className="text-sm text-[var(--text\_primary)]">
                  {slmModelInfo?.load_time_seconds
                    ? `${slmModelInfo.load_time_seconds.toFixed(2)}s`
                    : 'N/A'}
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => {
                  setActionResult(null)
                  reloadModelMutation.mutate('base')
                }}
                disabled={reloadModelMutation.isPending || slmLoading}
                className="flex-1 bg-[var(--bg\_primary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] text-[var(--text\_primary)] font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                Switch to Base Model
              </button>
              <button
                onClick={() => {
                  setActionResult(null)
                  reloadModelMutation.mutate('finetuned')
                }}
                disabled={reloadModelMutation.isPending || slmLoading}
                className="flex-1 bg-blue-600 hover:bg-blue-500 border border-blue-500 text-[var(--text\_primary)] font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-[0_0_15px_rgba(59,130,246,0.3)] disabled:opacity-50"
              >
                Switch to Fine-tuned Model
              </button>
            </div>

            {actionResult?.type === 'slm' && actionResult?.msg && (
              <div className="w-full mt-4 bg-green-500/10 border border-green-500/30 text-green-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
                <CheckCircle className="h-5 w-5 shrink-0" />
                <span>{actionResult.msg}</span>
              </div>
            )}
            {actionResult?.type === 'slm' && actionResult?.err && (
              <div className="w-full mt-4 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
                <XCircle className="h-5 w-5 shrink-0" />
                <span>{actionResult.err}</span>
              </div>
            )}
          </div>

          {/* SECTION RAG PIPELINE PANEL */}
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('general')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'general' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  General
                </button>
                <button
                  onClick={() => setActiveTab('advanced')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'advanced' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  Advanced
                </button>
              </div>
              <h2 className="text-xl font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <Network className="h-5 w-5 text-purple-400" />
                RAG Vector Database
              </h2>
              {ragLoading || reindexRagMutation.isPending ? (
                <span className="flex items-center gap-2 text-sm text-[var(--text\_secondary)]">
                  <RefreshCw className="w-4 h-4 animate-spin text-purple-500" /> Syncing blocks...
                </span>
              ) : (
                <span className="text-xs font-bold px-2 py-1 rounded-full border bg-purple-500/10 text-purple-400 border-purple-500/30">
                  ChromaDB Active
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  Total Indexed Alerts
                </h4>
                <p className="text-lg text-[var(--text\_primary)] font-mono font-bold text-purple-400">
                  {ragStats?.total_indexed ?? 'Loading...'}
                </p>
              </div>
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  Embedding Model
                </h4>
                <p className="text-sm text-[var(--text\_primary)]">
                  {ragStats?.embedding_model || 'Loading...'}
                </p>
              </div>
              <div className="bg-[var(--bg\_primary)] rounded-lg p-4 border border-[var(--border)]">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-semibold mb-1">
                  Persist Directory
                </h4>
                <p className="text-xs text-[var(--text\_primary)] font-mono break-all">
                  {ragStats?.persist_dir || 'Loading...'}
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => {
                  if (
                    window.confirm(
                      'Are you sure you want to completely destroy the RAG index? This cannot be undone.',
                    )
                  ) {
                    setActionResult(null)
                    clearRagMutation.mutate()
                  }
                }}
                disabled={clearRagMutation.isPending || ragLoading}
                className="flex-1 bg-[var(--bg\_primary)] hover:bg-red-900/40 border border-red-500/30 text-red-400 font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                Clear Index
              </button>
              <button
                onClick={() => {
                  setActionResult(null)
                  reindexRagMutation.mutate()
                }}
                disabled={reindexRagMutation.isPending || ragLoading}
                className="flex-1 bg-purple-600 hover:bg-purple-500 border border-purple-500 text-[var(--text\_primary)] font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-[0_0_15px_rgba(168,85,247,0.3)] disabled:opacity-50"
              >
                <Database className="w-4 h-4" /> Re-index All Alerts
              </button>
            </div>

            {actionResult?.type === 'rag' && actionResult?.msg && (
              <div className="w-full mt-4 bg-green-500/10 border border-green-500/30 text-green-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
                <CheckCircle className="h-5 w-5 shrink-0" />
                <span>{actionResult.msg}</span>
              </div>
            )}
            {actionResult?.type === 'rag' && actionResult?.err && (
              <div className="w-full mt-4 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
                <XCircle className="h-5 w-5 shrink-0" />
                <span>{actionResult.err}</span>
              </div>
            )}
          </div>

          {/* SECTION SLM PERFORMANCE METRICS */}
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('general')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'general' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  General
                </button>
                <button
                  onClick={() => setActiveTab('advanced')}
                  className={`px-4 py-2 font-bold rounded-md transition-colors ${activeTab === 'advanced' ? 'bg-blue-600 text-white' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
                >
                  Advanced
                </button>
              </div>
              <h2 className="text-xl font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <LineChart className="h-5 w-5 text-green-400" />
                SLM Quality & Performance Analytics
              </h2>
              <span className="text-xs font-bold text-[var(--text\_secondary)] border border-[var(--border)] bg-[var(--bg\_primary)] px-2 py-1 rounded-full">
                Last 24 Hours
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl p-5 flex flex-col items-center justify-center text-center">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-bold tracking-wider mb-2">
                  Total Queries
                </h4>
                <div className="text-3xl font-black text-[var(--text\_primary)]">
                  {slmMetrics?.total_queries ?? '-'}
                </div>
                <p className="text-xs text-[var(--text\_secondary)] mt-2">Investigative Traces</p>
              </div>

              <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl p-5 flex flex-col items-center justify-center text-center">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-bold tracking-wider mb-2">
                  Avg Latency
                </h4>
                <div className="text-3xl font-black text-blue-400">
                  {slmMetrics?.avg_response_time
                    ? `${Math.round(slmMetrics.avg_response_time)}`
                    : '-'}
                  <span className="text-sm text-[var(--text\_secondary)] ml-1">ms</span>
                </div>
                <p className="text-xs text-[var(--text\_secondary)] mt-2">
                  Time to First Token Target
                </p>
              </div>

              <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl p-5 flex flex-col items-center justify-center text-center">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-bold tracking-wider mb-2">
                  Throughput
                </h4>
                <div className="text-3xl font-black text-orange-400 flex items-center justify-center gap-1">
                  <Zap className="h-5 w-5" />
                  {slmMetrics?.avg_tokens_per_sec
                    ? `${slmMetrics.avg_tokens_per_sec.toFixed(1)}`
                    : '-'}
                </div>
                <p className="text-xs text-[var(--text\_secondary)] mt-2">Tokens Per Second (TPS)</p>
              </div>

              <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl p-5 flex flex-col items-center justify-center text-center">
                <h4 className="text-xs text-[var(--text\_secondary)] uppercase font-bold tracking-wider mb-2">
                  Avg Quality Score
                </h4>
                <div className="text-3xl font-black text-green-400">
                  {slmMetrics?.avg_quality_score
                    ? `${(slmMetrics.avg_quality_score * 100).toFixed(0)}`
                    : '-'}
                  <span className="text-sm text-[var(--text\_secondary)] ml-1">%</span>
                </div>
                <div className="w-full bg-[var(--bg\_secondary)] rounded-full h-1.5 mt-3">
                  <div
                    className="bg-green-500 h-1.5 rounded-full"
                    style={{ width: `${(slmMetrics?.avg_quality_score || 0) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* SECTION 2: Ingestion Configuration */}
            <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg lg:col-span-2">
              <div className="px-6 py-5 border-b border-[var(--border)] bg-[var(--bg\_primary)]/50">
                <h3 className="text-lg font-bold text-[var(--text\_primary)] flex items-center gap-2">
                  <GitCommit className="h-5 w-5 text-purple-500" />
                  Runtime Configuration Matrix
                </h3>
              </div>
              <table className="w-full text-left whitespace-nowrap">
                <tbody className="divide-y divide-[var(--border)]/30 text-sm">
                  <tr className="hover:bg-[var(--bg\_tertiary)]/30">
                    <td className="px-6 py-4 font-medium text-[var(--text\_secondary)]">
                      Window Size (minutes)
                    </td>
                    <td className="px-6 py-4 font-mono text-blue-400">5</td>
                  </tr>
                  <tr className="hover:bg-[var(--bg\_tertiary)]/30">
                    <td className="px-6 py-4 font-medium text-[var(--text\_secondary)]">
                      Index: Syslog
                    </td>
                    <td className="px-6 py-4 font-mono text-purple-400">logs-system.syslog-*</td>
                  </tr>
                  <tr className="hover:bg-[var(--bg\_tertiary)]/30">
                    <td className="px-6 py-4 font-medium text-[var(--text\_secondary)]">
                      Index: Process
                    </td>
                    <td className="px-6 py-4 font-mono text-purple-400">
                      logs-endpoint.events.process-*
                    </td>
                  </tr>
                  <tr className="hover:bg-[var(--bg\_tertiary)]/30">
                    <td className="px-6 py-4 font-medium text-[var(--text\_secondary)]">
                      Index: Security
                    </td>
                    <td className="px-6 py-4 font-mono text-purple-400">
                      logs-windows.powershell_operational-*
                    </td>
                  </tr>
                  <tr className="hover:bg-[var(--bg\_tertiary)]/30">
                    <td className="px-6 py-4 font-medium text-[var(--text\_secondary)]">
                      Threat Score Threshold
                    </td>
                    <td className="px-6 py-4 font-mono text-orange-400">0.3</td>
                  </tr>
                  <tr className="hover:bg-[var(--bg\_tertiary)]/30">
                    <td className="px-6 py-4 font-medium text-[var(--text\_secondary)]">
                      False Positive Suppress
                    </td>
                    <td className="px-6 py-4 font-mono text-green-400">Enabled</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* SECTION 4: About ISRO SOC */}
            <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 flex flex-col justify-center items-center text-center shadow-lg lg:col-span-1 border-t-4 border-t-blue-500">
              <div className="w-20 h-20 bg-[var(--bg\_primary)] rounded-full border-4 border-[var(--border)] flex items-center justify-center mb-6">
                <Bot className="h-10 w-10 text-blue-500" />
              </div>
              <h2 className="text-xl font-bold text-[var(--text\_primary)] mb-2">ISRO ISTRAC</h2>
              <h3 className="text-sm font-semibold text-blue-400 tracking-wider uppercase mb-4">
                SOC AI Platform v1.0.0
              </h3>
              <p className="text-sm text-[var(--text\_secondary)] mb-6 leading-relaxed">
                Developed securely at the ISRO Satellite Tracking and Ranging Station, Bengaluru.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-auto">
                <span className="text-[10px] uppercase tracking-wider font-bold bg-[var(--bg\_primary)] border border-[var(--border)] text-[var(--text\_secondary)] px-2 py-1 rounded">
                  Python 3.11
                </span>
                <span className="text-[10px] uppercase tracking-wider font-bold bg-[var(--bg\_primary)] border border-[var(--border)] text-[var(--text\_secondary)] px-2 py-1 rounded">
                  FastAPI
                </span>
                <span className="text-[10px] uppercase tracking-wider font-bold bg-[var(--bg\_primary)] border border-[var(--border)] text-[var(--text\_secondary)] px-2 py-1 rounded">
                  Elasticsearch 8.x
                </span>
                <span className="text-[10px] uppercase tracking-wider font-bold bg-[var(--bg\_primary)] border border-[var(--border)] text-[var(--text\_secondary)] px-2 py-1 rounded">
                  PyTorch
                </span>
                <span className="text-[10px] uppercase tracking-wider font-bold bg-blue-900/30 border border-blue-500/50 text-blue-400 px-2 py-1 rounded">
                  Phi-3-mini
                </span>
              </div>
            </div>
          </div>

          {/* SECTION 3: Manual Controls */}
          <div>
            <h2 className="text-xl font-bold text-[var(--text\_primary)] mb-6 mt-4">
              Manual Diagnostics & Overrides
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ActionBox
                title="Trigger Ingestion Cycle"
                icon={Database}
                description="Manually fetch the latest logs from standard index clusters simulating a background cron trigger."
                mutation={ingestionMutation}
                type="ingestion"
              />
              <ActionBox
                title="Trigger Feature Pipeline"
                icon={Activity}
                description="Run raw telemetry parsing, aggregation matrices, and normalizations creating ML-ready vectors."
                mutation={featureMutation}
                type="feature"
              />
              <ActionBox
                title="Trigger Scoring Cycle"
                icon={Bot}
                description="Push the extracted vectors against Isolation Forest, Autoencoder, and LSTM yielding threat score anomalies."
                mutation={scoringMutation}
                type="scoring"
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
