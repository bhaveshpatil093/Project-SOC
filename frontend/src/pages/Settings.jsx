import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { triggerScoring } from "../api/alerts";
import { getModelInfo, reloadModel, getRagStats, reindexRag, clearRagIndex, getSlmMetrics } from "../api/slm";
import { useWebSocket } from "../hooks/useWebSocket";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { Server, Database, Activity, GitCommit, RefreshCw, CheckCircle, Play, XCircle, Bot, MonitorDot, Cpu, Network, LineChart, Zap } from "lucide-react";
import { formatDate } from "../utils/formatters";

export const Settings = () => {
  const queryClient = useQueryClient();
  const { connected: wsConnected, reconnecting: wsReconnecting } = useWebSocket();
  const [actionResult, setActionResult] = useState(null);

  // Health Queries
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get("/health"),
    refetchInterval: 30000,
  });

  const { data: ingestion, isLoading: ingestionLoading } = useQuery({
    queryKey: ["ingestionStatus"],
    queryFn: () => apiClient.get("/api/ingestion/status"),
    refetchInterval: 30000,
  });

  const { data: slmModelInfo, isLoading: slmLoading, refetch: refetchSlm } = useQuery({
    queryKey: ["slmModelInfo"],
    queryFn: getModelInfo,
    refetchInterval: 30000,
  });

  const { data: ragStats, isLoading: ragLoading, refetch: refetchRag } = useQuery({
    queryKey: ["ragStats"],
    queryFn: getRagStats,
    refetchInterval: 30000,
  });

  const { data: slmMetrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ["slmMetrics"],
    queryFn: () => getSlmMetrics(24),
    refetchInterval: 30000,
  });

  const isHealthy = health?.status === "ok";

  const refreshStatus = () => {
    queryClient.invalidateQueries({ queryKey: ["health"] });
    queryClient.invalidateQueries({ queryKey: ["ingestionStatus"] });
    refetchSlm();
    refetchRag();
    refetchMetrics();
  };

  // Mutations
  const ingestionMutation = useMutation({
    mutationFn: () => apiClient.post("/api/ingestion/run"),
    onSuccess: (res) => {
      setActionResult({ type: "ingestion", msg: `Ingested ${res.docs_ingested || 0} documents successfully.` });
      refreshStatus();
    },
    onError: (err) => setActionResult({ type: "ingestion", err: err.message })
  });

  const featureMutation = useMutation({
    mutationFn: () => apiClient.get("/api/features/run"),
    onSuccess: (res) => {
      setActionResult({ type: "feature", msg: `Extracted ${res.total_features || 'new'} feature vectors successfully.` });
    },
    onError: (err) => setActionResult({ type: "feature", err: err.message })
  });

  const scoringMutation = useMutation({
    mutationFn: triggerScoring,
    onSuccess: (res) => {
      setActionResult({ type: "scoring", msg: `Scored ${res.scored || 0} entities, triggered ${res.alerts_above_threshold || 0} alerts.` });
    },
    onError: (err) => setActionResult({ type: "scoring", err: err.message })
  });

  const reloadModelMutation = useMutation({
    mutationFn: (model) => reloadModel(model),
    onSuccess: (res) => {
      setActionResult({ type: "slm", msg: `Successfully reloaded SLM Engine onto ${res.model_name}` });
      refetchSlm();
    },
    onError: (err) => setActionResult({ type: "slm", err: err.message })
  });

  const reindexRagMutation = useMutation({
    mutationFn: reindexRag,
    onSuccess: (res) => {
      setActionResult({ type: "rag", msg: `RAG re-index job started globally. Job ID: ${res.job_id}` });
      setTimeout(refetchRag, 5000);
    },
    onError: (err) => setActionResult({ type: "rag", err: err.message })
  });

  const clearRagMutation = useMutation({
    mutationFn: clearRagIndex,
    onSuccess: (res) => {
      setActionResult({ type: "rag", msg: res.message });
      refetchRag();
    },
    onError: (err) => setActionResult({ type: "rag", err: err.message })
  });

  const handleAction = (mutationObj, type) => {
    setActionResult(null);
    mutationObj.mutate();
  };

  const ActionBox = ({ title, icon: Icon, description, mutation, type }) => (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 flex flex-col items-start transition-all hover:border-slate-500">
      <div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg mb-4">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 mb-6 flex-1">{description}</p>
      
      <button 
        onClick={() => handleAction(mutation, type)}
        disabled={mutation.isPending}
        className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-600 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors mb-4"
      >
        {mutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
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
  );

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">System Settings & Health</h1>
          <p className="text-slate-400 mt-1">Monitor ingestion schedulers, verify database connections, and run manual orchestrations.</p>
        </div>
        <button 
          onClick={refreshStatus}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium border border-slate-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" /> Refresh Status
        </button>
      </div>

      {/* SECTION 1: System Health Panel */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-slate-900 rounded text-slate-400 border border-slate-700"><Database className="h-5 w-5"/></div>
            {healthLoading ? <LoadingSpinner size={4}/> : isHealthy ? (
              <span className="flex items-center gap-1.5 text-xs font-bold text-green-500 bg-green-500/10 px-2 py-1 rounded-full"><div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"/> Connected</span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-bold text-red-500 bg-red-500/10 px-2 py-1 rounded-full"><div className="w-1.5 h-1.5 bg-red-500 rounded-full"/> Disconnected</span>
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">Elasticsearch Node</h3>
            <p className="text-lg font-medium text-white">Main Cluster</p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-slate-900 rounded text-slate-400 border border-slate-700"><Server className="h-5 w-5"/></div>
            {ingestionLoading ? <LoadingSpinner size={4}/> : ingestion?.status === "running" ? (
              <span className="flex items-center gap-1.5 text-xs font-bold text-blue-400 bg-blue-500/10 px-2 py-1 rounded-full"><div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"/> Running</span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-bold text-slate-400 bg-slate-500/10 px-2 py-1 rounded-full">Stopped</span>
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">Ingestion Scheduler</h3>
            <p className="text-xs text-slate-300">
              {ingestion?.last_run ? `Last run: ${formatDate(ingestion.last_run)}` : 'Waiting for initial tick...'}
              <br/><span className="text-slate-500 font-mono mt-1 block">Docs: {ingestion?.docs_last_cycle || 0}</span>
            </p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-slate-900 rounded text-slate-400 border border-slate-700"><MonitorDot className="h-5 w-5"/></div>
            {wsConnected ? (
              <span className="flex items-center gap-1.5 text-xs font-bold text-green-500 bg-green-500/10 px-2 py-1 rounded-full"><div className="w-1.5 h-1.5 bg-green-500 rounded-full"/> Connected</span>
            ) : wsReconnecting ? (
              <span className="flex items-center gap-1.5 text-xs font-bold text-orange-500 bg-orange-500/10 px-2 py-1 rounded-full"><div className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-ping"/> Reconnecting</span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-bold text-red-500 bg-red-500/10 px-2 py-1 rounded-full">Offline</span>
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">WebSocket Live Feed</h3>
            <p className="text-xs text-slate-300">Real-time alert streaming channel</p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-slate-900 rounded text-slate-400 border border-slate-700"><Activity className="h-5 w-5"/></div>
            {isHealthy ? (
              <span className="flex items-center gap-1.5 text-xs font-bold text-green-500 bg-green-500/10 px-2 py-1 rounded-full">Healthy</span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-bold text-red-500 bg-red-500/10 px-2 py-1 rounded-full">Degraded</span>
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">Scoring & AI Engine</h3>
            <p className="text-xs text-slate-300">FastAPI ML Dependency Runtime</p>
          </div>
        </div>
      </div>

      {/* SECTION SLM MODEL PANEL */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Cpu className="h-5 w-5 text-blue-400" />
            SLM Engine Configuration
          </h2>
          {slmLoading || reloadModelMutation.isPending ? (
            <span className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="w-4 h-4 animate-spin text-blue-500" /> Hot-reloading tensors...
            </span>
          ) : (
            <span className={`text-xs font-bold px-2 py-1 rounded-full border ${slmModelInfo?.is_finetuned ? 'bg-purple-500/10 text-purple-400 border-purple-500/30' : 'bg-slate-700/50 text-slate-400 border-slate-600'}`}>
              {slmModelInfo?.is_finetuned ? 'Fine-Tuned Adapter Active' : 'Base Model Active'}
            </span>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">Current Model</h4>
            <p className="text-sm text-slate-200 truncate" title={slmModelInfo?.model_name || 'Loading...'}>{slmModelInfo?.model_name || 'Loading...'}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">Hardware Device</h4>
            <p className="text-sm text-slate-200 uppercase font-mono">{slmModelInfo?.device || 'N/A'}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">VRAM Footprint</h4>
            <p className="text-sm text-slate-200">{slmModelInfo?.estimated_memory_mb ? `${Math.round(slmModelInfo.estimated_memory_mb)} MB` : 'N/A'}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">Load Latency</h4>
            <p className="text-sm text-slate-200">{slmModelInfo?.load_time_seconds ? `${slmModelInfo.load_time_seconds.toFixed(2)}s` : 'N/A'}</p>
          </div>
        </div>

        <div className="flex gap-4">
          <button 
            onClick={() => {
              setActionResult(null);
              reloadModelMutation.mutate("base");
            }}
            disabled={reloadModelMutation.isPending || slmLoading}
            className="flex-1 bg-slate-900 hover:bg-slate-700 border border-slate-600 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            Switch to Base Model
          </button>
          <button 
            onClick={() => {
              setActionResult(null);
              reloadModelMutation.mutate("finetuned");
            }}
            disabled={reloadModelMutation.isPending || slmLoading}
            className="flex-1 bg-blue-600 hover:bg-blue-500 border border-blue-500 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-[0_0_15px_rgba(59,130,246,0.3)] disabled:opacity-50"
          >
            Switch to Fine-tuned Model
          </button>
        </div>
        
        {actionResult?.type === "slm" && actionResult?.msg && (
          <div className="w-full mt-4 bg-green-500/10 border border-green-500/30 text-green-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
            <CheckCircle className="h-5 w-5 shrink-0" />
            <span>{actionResult.msg}</span>
          </div>
        )}
        {actionResult?.type === "slm" && actionResult?.err && (
          <div className="w-full mt-4 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
            <XCircle className="h-5 w-5 shrink-0" />
            <span>{actionResult.err}</span>
          </div>
        )}
      </div>

      {/* SECTION RAG PIPELINE PANEL */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Network className="h-5 w-5 text-purple-400" />
            RAG Vector Database
          </h2>
          {ragLoading || reindexRagMutation.isPending ? (
            <span className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="w-4 h-4 animate-spin text-purple-500" /> Syncing blocks...
            </span>
          ) : (
            <span className="text-xs font-bold px-2 py-1 rounded-full border bg-purple-500/10 text-purple-400 border-purple-500/30">
              ChromaDB Active
            </span>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">Total Indexed Alerts</h4>
            <p className="text-lg text-slate-200 font-mono font-bold text-purple-400">{ragStats?.total_indexed ?? 'Loading...'}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">Embedding Model</h4>
            <p className="text-sm text-slate-200">{ragStats?.embedding_model || 'Loading...'}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <h4 className="text-xs text-slate-500 uppercase font-semibold mb-1">Persist Directory</h4>
            <p className="text-xs text-slate-200 font-mono break-all">{ragStats?.persist_dir || 'Loading...'}</p>
          </div>
        </div>

        <div className="flex gap-4">
          <button 
            onClick={() => {
              if (window.confirm("Are you sure you want to completely destroy the RAG index? This cannot be undone.")) {
                setActionResult(null);
                clearRagMutation.mutate();
              }
            }}
            disabled={clearRagMutation.isPending || ragLoading}
            className="flex-1 bg-slate-900 hover:bg-red-900/40 border border-red-500/30 text-red-400 font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            Clear Index
          </button>
          <button 
            onClick={() => {
              setActionResult(null);
              reindexRagMutation.mutate();
            }}
            disabled={reindexRagMutation.isPending || ragLoading}
            className="flex-1 bg-purple-600 hover:bg-purple-500 border border-purple-500 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-[0_0_15px_rgba(168,85,247,0.3)] disabled:opacity-50"
          >
            <Database className="w-4 h-4" /> Re-index All Alerts
          </button>
        </div>
        
        {actionResult?.type === "rag" && actionResult?.msg && (
          <div className="w-full mt-4 bg-green-500/10 border border-green-500/30 text-green-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
            <CheckCircle className="h-5 w-5 shrink-0" />
            <span>{actionResult.msg}</span>
          </div>
        )}
        {actionResult?.type === "rag" && actionResult?.err && (
          <div className="w-full mt-4 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg flex items-start gap-2">
            <XCircle className="h-5 w-5 shrink-0" />
            <span>{actionResult.err}</span>
          </div>
        )}
      </div>

      {/* SECTION SLM PERFORMANCE METRICS */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <LineChart className="h-5 w-5 text-green-400" />
            SLM Quality & Performance Analytics
          </h2>
          <span className="text-xs font-bold text-slate-400 border border-slate-700 bg-slate-900 px-2 py-1 rounded-full">
            Last 24 Hours
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center text-center">
            <h4 className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Total Queries</h4>
            <div className="text-3xl font-black text-white">{slmMetrics?.total_queries ?? '-'}</div>
            <p className="text-xs text-slate-400 mt-2">Investigative Traces</p>
          </div>

          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center text-center">
            <h4 className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Avg Latency</h4>
            <div className="text-3xl font-black text-blue-400">
              {slmMetrics?.avg_response_time ? `${Math.round(slmMetrics.avg_response_time)}` : '-'}
              <span className="text-sm text-slate-500 ml-1">ms</span>
            </div>
            <p className="text-xs text-slate-400 mt-2">Time to First Token Target</p>
          </div>

          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center text-center">
            <h4 className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Throughput</h4>
            <div className="text-3xl font-black text-orange-400 flex items-center justify-center gap-1">
              <Zap className="h-5 w-5" />
              {slmMetrics?.avg_tokens_per_sec ? `${slmMetrics.avg_tokens_per_sec.toFixed(1)}` : '-'}
            </div>
            <p className="text-xs text-slate-400 mt-2">Tokens Per Second (TPS)</p>
          </div>

          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center text-center">
            <h4 className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Avg Quality Score</h4>
            <div className="text-3xl font-black text-green-400">
              {slmMetrics?.avg_quality_score ? `${(slmMetrics.avg_quality_score * 100).toFixed(0)}` : '-'}
              <span className="text-sm text-slate-500 ml-1">%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-3">
              <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${(slmMetrics?.avg_quality_score || 0) * 100}%` }}></div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* SECTION 2: Ingestion Configuration */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg lg:col-span-2">
          <div className="px-6 py-5 border-b border-slate-700 bg-slate-900/50">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <GitCommit className="h-5 w-5 text-purple-500" />
              Runtime Configuration Matrix
            </h3>
          </div>
          <table className="w-full text-left whitespace-nowrap">
            <tbody className="divide-y divide-slate-700/30 text-sm">
              <tr className="hover:bg-slate-750/30">
                <td className="px-6 py-4 font-medium text-slate-300">Window Size (minutes)</td>
                <td className="px-6 py-4 font-mono text-blue-400">5</td>
              </tr>
              <tr className="hover:bg-slate-750/30">
                <td className="px-6 py-4 font-medium text-slate-300">Index: Syslog</td>
                <td className="px-6 py-4 font-mono text-purple-400">logs-system.syslog-*</td>
              </tr>
              <tr className="hover:bg-slate-750/30">
                <td className="px-6 py-4 font-medium text-slate-300">Index: Process</td>
                <td className="px-6 py-4 font-mono text-purple-400">logs-endpoint.events.process-*</td>
              </tr>
              <tr className="hover:bg-slate-750/30">
                <td className="px-6 py-4 font-medium text-slate-300">Index: Security</td>
                <td className="px-6 py-4 font-mono text-purple-400">logs-windows.powershell_operational-*</td>
              </tr>
              <tr className="hover:bg-slate-750/30">
                <td className="px-6 py-4 font-medium text-slate-300">Threat Score Threshold</td>
                <td className="px-6 py-4 font-mono text-orange-400">0.3</td>
              </tr>
              <tr className="hover:bg-slate-750/30">
                <td className="px-6 py-4 font-medium text-slate-300">False Positive Suppress</td>
                <td className="px-6 py-4 font-mono text-green-400">Enabled</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* SECTION 4: About ISRO SOC */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 flex flex-col justify-center items-center text-center shadow-lg lg:col-span-1 border-t-4 border-t-blue-500">
          <div className="w-20 h-20 bg-slate-900 rounded-full border-4 border-slate-700 flex items-center justify-center mb-6">
            <Bot className="h-10 w-10 text-blue-500" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">ISRO ISTRAC</h2>
          <h3 className="text-sm font-semibold text-blue-400 tracking-wider uppercase mb-4">SOC AI Platform v1.0.0</h3>
          <p className="text-sm text-slate-400 mb-6 leading-relaxed">
            Developed securely at the ISRO Satellite Tracking and Ranging Station, Bengaluru.
          </p>
          <div className="flex flex-wrap justify-center gap-2 mt-auto">
            <span className="text-[10px] uppercase tracking-wider font-bold bg-slate-900 border border-slate-700 text-slate-300 px-2 py-1 rounded">Python 3.11</span>
            <span className="text-[10px] uppercase tracking-wider font-bold bg-slate-900 border border-slate-700 text-slate-300 px-2 py-1 rounded">FastAPI</span>
            <span className="text-[10px] uppercase tracking-wider font-bold bg-slate-900 border border-slate-700 text-slate-300 px-2 py-1 rounded">Elasticsearch 8.x</span>
            <span className="text-[10px] uppercase tracking-wider font-bold bg-slate-900 border border-slate-700 text-slate-300 px-2 py-1 rounded">PyTorch</span>
            <span className="text-[10px] uppercase tracking-wider font-bold bg-blue-900/30 border border-blue-500/50 text-blue-400 px-2 py-1 rounded">Phi-3-mini</span>
          </div>
        </div>
      </div>

      {/* SECTION 3: Manual Controls */}
      <div>
        <h2 className="text-xl font-bold text-white mb-6 mt-4">Manual Diagnostics & Overrides</h2>
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
    </div>
  );
};
