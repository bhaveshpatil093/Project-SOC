import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  startInitialTraining,
  startRetraining,
  getTrainingStatus,
  getMlflowExperiments,
  getMlflowRuns,
  getMlflowRunDetail,
  compareMlflowRuns,
  getDriftStatus,
  getCalibrationStats,
  getInterpretabilityReport,
  getAccuracyReport,
  updateThreatThreshold,
} from '../api/training'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { Badge } from '../components/common/Badge'
import { formatDate } from '../utils/formatters'
import {
  Brain,
  Play,
  RotateCw,
  Activity,
  Calendar,
  Server,
  CheckCircle,
  Database,
  Network,
  Clock,
  Loader2,
  GitCommit,
  GitCompare,
  AlertTriangle,
  Eye,
  Target,
} from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useUiStore } from '../store/uiStore'
import { THEMES } from '../utils/theme'

const useJobStatus = (jobId) => {
  return useQuery({
    queryKey: ['trainingStatus', jobId],
    queryFn: () => getTrainingStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (data) => {
      if (data && data.data) {
        const status = data.data.status?.toLowerCase()
        if (status === 'completed' || status === 'failed' || status === 'error') return false
      } else if (data) {
        const status = data.status?.toLowerCase()
        if (status === 'completed' || status === 'failed' || status === 'error') return false
      }
      return 3000
    },
  })
}

const useCalibration = () =>
  useQuery({
    queryKey: ['calibrationStatus'],
    queryFn: () => getCalibrationStats(),
    refetchInterval: 10000,
  })

const TabButton = ({ active, onClick, children }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
      active
        ? 'border-blue-500 text-blue-400'
        : 'border-transparent text-[var(--text\_secondary)] hover:text-[var(--text\_primary)] hover:border-[var(--border)]'
    }`}
  >
    {children}
  </button>
)

import { ShieldAlert } from 'lucide-react'
export const Training = () => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('status') // status, runs, compare, schedule
  const [jobId, setJobId] = useState(null)

  const { theme } = usePreferencesStore()
  const colors = THEMES[theme]

  // For MLflow
  const [selectedExperiment, setSelectedExperiment] = useState(null)
  const [selectedRuns, setSelectedRuns] = useState([])
  const [expandedRun, setExpandedRun] = useState(null)

  // Queries
  const { data: experimentsData, isLoading: expsLoading } = useQuery({
    queryKey: ['mlflowExperiments'],
    queryFn: () => getMlflowExperiments(),
  })

  const experiments = experimentsData?.data || experimentsData || []

  // Auto-select first experiment if none selected
  if (experiments.length > 0 && !selectedExperiment) {
    setSelectedExperiment(experiments[0].experiment_id)
  }

  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ['mlflowRuns', selectedExperiment],
    queryFn: () => getMlflowRuns(selectedExperiment),
    enabled: !!selectedExperiment,
    refetchInterval: 15000,
  })

  const runs = runsData?.data || runsData || []

  const { data: compareData, isLoading: compareLoading } = useQuery({
    queryKey: ['mlflowCompare', selectedRuns],
    queryFn: () => compareMlflowRuns(selectedRuns),
    enabled: selectedRuns.length > 1 && activeTab === 'compare',
  })

  const { data: expandedRunData, isLoading: expandedLoading } = useQuery({
    queryKey: ['mlflowRunDetail', expandedRun],
    queryFn: () => getMlflowRunDetail(expandedRun),
    enabled: !!expandedRun,
  })

  const { data: interpretabilityData, isLoading: interpretLoading } = useQuery({
    queryKey: ['interpretability'],
    queryFn: () => getInterpretabilityReport(),
    enabled: activeTab === 'interpretability',
    staleTime: 3600000, // Cache for 1 hour on frontend too
  })
  const interpretability = interpretabilityData?.data || interpretabilityData

  const { data: accuracyData, isLoading: accuracyLoading, error: accuracyError } = useQuery({
    queryKey: ['accuracyReport'],
    queryFn: () => getAccuracyReport(),
    enabled: activeTab === 'accuracy',
  })
  const accuracy = accuracyData?.data || accuracyData

  const applyThresholdMutation = useMutation({
    mutationFn: updateThreatThreshold,
    onSuccess: () => {
      alert('Threshold applied successfully!')
    }
  })


  const { data: statusResp } = useJobStatus(jobId)
  const statusData = statusResp?.data || statusResp

  const { data: driftResp, isLoading: driftLoading } = useQuery({
    queryKey: ['driftStatus'],
    queryFn: () => getDriftStatus(),
    refetchInterval: 60000,
  })
  const driftData = driftResp?.data ||
    driftResp || { status: 'Unknown', overall_drift_score: 0, top_drifted_features: [] }

  const initialMutation = useMutation({
    mutationFn: startInitialTraining,
    onSuccess: (res) => {
      const data = res.data || res
      if (data.job_id) setJobId(data.job_id)
    },
  })

  const retrainMutation = useMutation({
    mutationFn: startRetraining,
    onSuccess: (res) => {
      const data = res.data || res
      if (data.job_id) setJobId(data.job_id)
    },
  })

  const handleInitial = () => {
    setJobId(null)
    initialMutation.mutate()
  }

  const handleRetrain = () => {
    setJobId(null)
    retrainMutation.mutate()
  }

  const toggleRunSelection = (runId) => {
    if (selectedRuns.includes(runId)) {
      setSelectedRuns(selectedRuns.filter((id) => id !== runId))
    } else {
      if (selectedRuns.length >= 4) {
        alert('You can compare up to 4 runs at a time.')
        return
      }
      setSelectedRuns([...selectedRuns, runId])
    }
  }

  // Process data for Model Status tab
  const if_runs = runs.filter(
    (r) =>
      r.tags?.['mlflow.runName']?.includes('Isolation Forest') ||
      r.params?.model_type === 'isolation_forest',
  )
  const ae_runs = runs.filter(
    (r) =>
      r.tags?.['mlflow.runName']?.includes('Autoencoder') || r.params?.model_type === 'autoencoder',
  )
  const lstm_runs = runs.filter(
    (r) => r.tags?.['mlflow.runName']?.includes('LSTM') || r.params?.model_type === 'lstm',
  )

  const latestIF = if_runs[0] || null
  const latestAE = ae_runs[0] || null
  const latestLSTM = lstm_runs[0] || null

  const drift = driftData?.data || { has_drift: false, features: {} }
  const calibration = calibrationData?.data?.data ||
    calibrationData?.data || { is_calibrated: false }

  // Process data for comparison chart
  const compareRuns = compareData?.data?.runs || compareData?.runs || []

  let chartData = []
  if (compareRuns.length > 0) {
    const maxLen = Math.max(...compareRuns.map((r) => r.loss_history?.length || 0))
    for (let i = 0; i < maxLen; i++) {
      const point = { epoch: i }
      compareRuns.forEach((r) => {
        if (r.loss_history && i < r.loss_history.length) {
          point[r.name] = r.loss_history[i].value
        }
      })
      chartData.push(point)
    }
  }

  const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b']

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-3xl font-bold text-[var(--text\_primary)] tracking-tight flex items-center gap-3">
          <Activity className="h-8 w-8 text-blue-500" /> MLflow Model Dashboard
        </h1>
        <p className="text-[var(--text\_secondary)] mt-1">
          Track ML experiments, compare runs, and orchestrate training cycles natively.
        </p>
      </div>

      <div className="flex border-b border-[var(--border)] mt-6">
        <TabButton active={activeTab === 'status'} onClick={() => setActiveTab('status')}>
          Model Status
        </TabButton>
        <TabButton active={activeTab === 'runs'} onClick={() => setActiveTab('runs')}>
          Experiment Runs
        </TabButton>
        <TabButton active={activeTab === 'compare'} onClick={() => setActiveTab('compare')}>
          Compare ({selectedRuns.length})
        </TabButton>
        <TabButton active={activeTab === 'schedule'} onClick={() => setActiveTab('schedule')}>
          Training Schedule
        </TabButton>
        <TabButton
          active={activeTab === 'interpretability'}
          onClick={() => setActiveTab('interpretability')}
        >
          Interpretability
        </TabButton>
      </div>

      {/* TAB 1: Model Status */}
      {activeTab === 'status' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 animate-in fade-in slide-in-from-bottom-2">
          {/* Isolation Forest Card */}
          <div
            className={`rounded-xl border p-6 flex flex-col justify-between ${latestIF ? 'bg-[var(--bg\_secondary)] border-[var(--border)]' : 'bg-[var(--bg\_primary)] border-[var(--border)] opacity-80'}`}
          >
            <div>
              <div className="flex justify-between items-start mb-4">
                <div
                  className={`p-2 rounded-lg ${latestIF ? 'bg-blue-500/20 text-blue-500' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)]'}`}
                >
                  <Network className="h-6 w-6" />
                </div>
                <Badge variant={latestIF ? 'tp' : 'fp'}>
                  {latestIF ? 'Loaded' : 'Not Trained'}
                </Badge>
              </div>
              <h3
                className={`text-lg font-bold ${latestIF ? 'text-[var(--text\_primary)]' : 'text-[var(--text\_secondary)]'}`}
              >
                Isolation Forest
              </h3>
              <p className="text-xs text-[var(--text\_secondary)] mt-1">
                Unsupervised Outlier Detection
              </p>
            </div>
            <div className="mt-6 space-y-2 border-t border-[var(--border)]/50 pt-4">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text\_secondary)]">N Samples:</span>
                <span className="text-[var(--text\_primary)] font-medium">
                  {latestIF?.metrics?.n_samples || '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text\_secondary)]">Contamination:</span>
                <span className="text-[var(--text\_primary)] font-medium">
                  {latestIF?.metrics?.contamination || '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm mt-2 pt-2 border-t border-[var(--border)]">
                <span className="text-[var(--text\_secondary)]">Active Run:</span>
                <span className="text-blue-400 font-mono text-xs">
                  {latestIF?.run_id?.substring(0, 8) || '—'}
                </span>
              </div>
            </div>
            <button
              onClick={handleInitial}
              disabled={initialMutation.isPending}
              className="w-full mt-4 bg-[var(--bg\_tertiary)] hover:bg-[var(--bg\_tertiary)] text-[var(--text\_primary)] text-sm py-2 rounded-lg transition-colors"
            >
              Retrain Baseline
            </button>
          </div>

          {/* Autoencoder Card */}
          <div
            className={`rounded-xl border p-6 flex flex-col justify-between ${latestAE ? 'bg-[var(--bg\_secondary)] border-[var(--border)]' : 'bg-[var(--bg\_primary)] border-[var(--border)] opacity-80'}`}
          >
            <div>
              <div className="flex justify-between items-start mb-4">
                <div
                  className={`p-2 rounded-lg ${latestAE ? 'bg-purple-500/20 text-purple-500' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)]'}`}
                >
                  <Brain className="h-6 w-6" />
                </div>
                <Badge variant={latestAE ? 'tp' : 'fp'}>
                  {latestAE ? 'Loaded' : 'Not Trained'}
                </Badge>
              </div>
              <h3
                className={`text-lg font-bold ${latestAE ? 'text-[var(--text\_primary)]' : 'text-[var(--text\_secondary)]'}`}
              >
                Autoencoder
              </h3>
              <p className="text-xs text-[var(--text\_secondary)] mt-1">
                Deep Feature Reconstruction
              </p>
            </div>
            <div className="mt-6 space-y-2 border-t border-[var(--border)]/50 pt-4">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text\_secondary)]">Final Loss:</span>
                <span className="text-[var(--text\_primary)] font-medium">
                  {latestAE?.metrics?.final_loss?.toFixed(4) || '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text\_secondary)]">Threshold:</span>
                <span className="text-[var(--text\_primary)] font-medium">
                  {latestAE?.metrics?.threshold?.toFixed(4) || '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm mt-2 pt-2 border-t border-[var(--border)]">
                <span className="text-[var(--text\_secondary)]">Active Run:</span>
                <span className="text-purple-400 font-mono text-xs">
                  {latestAE?.run_id?.substring(0, 8) || '—'}
                </span>
              </div>
            </div>
            <button
              onClick={handleRetrain}
              disabled={retrainMutation.isPending}
              className="w-full mt-4 bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 border border-purple-500/30 text-sm py-2 rounded-lg transition-colors"
            >
              Incremental Fine-Tune
            </button>
          </div>

          {/* LSTM Card */}
          <div
            className={`rounded-xl border p-6 flex flex-col justify-between ${latestLSTM ? 'bg-[var(--bg\_secondary)] border-[var(--border)]' : 'bg-[var(--bg\_primary)] border-[var(--border)] opacity-80'}`}
          >
            <div>
              <div className="flex justify-between items-start mb-4">
                <div
                  className={`p-2 rounded-lg ${latestLSTM ? 'bg-green-500/20 text-green-500' : 'bg-[var(--bg\_secondary)] text-[var(--text\_secondary)]'}`}
                >
                  <Activity className="h-6 w-6" />
                </div>
                <Badge variant={latestLSTM ? 'tp' : 'fp'}>
                  {latestLSTM ? 'Loaded' : 'Not Trained'}
                </Badge>
              </div>
              <h3
                className={`text-lg font-bold ${latestLSTM ? 'text-[var(--text\_primary)]' : 'text-[var(--text\_secondary)]'}`}
              >
                LSTM Sequence
              </h3>
              <p className="text-xs text-[var(--text\_secondary)] mt-1">
                Temporal Sequence Forecasting
              </p>
            </div>
            <div className="mt-6 space-y-2 border-t border-[var(--border)]/50 pt-4">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text\_secondary)]">Vocab Size:</span>
                <span className="text-[var(--text\_primary)] font-medium">
                  {latestLSTM?.metrics?.vocab_size || '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text\_secondary)]">Seq Length:</span>
                <span className="text-[var(--text\_primary)] font-medium">
                  {latestLSTM?.params?.sequence_length || '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm mt-2 pt-2 border-t border-[var(--border)]">
                <span className="text-[var(--text\_secondary)]">Active Run:</span>
                <span className="text-green-400 font-mono text-xs">
                  {latestLSTM?.run_id?.substring(0, 8) || '—'}
                </span>
              </div>
            </div>
            <button
              onClick={handleInitial}
              disabled={initialMutation.isPending}
              className="w-full mt-4 bg-[var(--bg\_tertiary)] hover:bg-[var(--bg\_tertiary)] text-[var(--text\_primary)] text-sm py-2 rounded-lg transition-colors"
            >
              Retrain Baseline
            </button>
          </div>

          {/* Drift Status Card */}
          <div className="md:col-span-3 bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg flex flex-col md:flex-row gap-6 justify-between items-start md:items-center mt-2">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <AlertTriangle
                  className={`h-6 w-6 ${driftData.overall_drift_score > 0.2 ? 'text-red-500' : driftData.overall_drift_score > 0.1 ? 'text-yellow-500' : 'text-green-500'}`}
                />
                <h3 className="text-xl font-bold text-[var(--text\_primary)]">Feature Data Drift</h3>
                <Badge
                  variant={
                    driftData.overall_drift_score > 0.2
                      ? 'critical'
                      : driftData.overall_drift_score > 0.1
                        ? 'medium'
                        : 'low'
                  }
                >
                  {driftData.status || 'No Drift'}
                </Badge>
              </div>
              <p className="text-sm text-[var(--text\_secondary)]">
                Overall Population Stability Index (PSI):{' '}
                <span className="font-mono font-bold text-[var(--text\_primary)]">
                  {driftData.overall_drift_score?.toFixed(4)}
                </span>
              </p>
            </div>

            <div className="flex-1 w-full md:w-auto">
              <h4 className="text-xs font-bold text-[var(--text\_secondary)] uppercase tracking-wider mb-2">
                Top Drifted Features
              </h4>
              {driftData.top_drifted_features && driftData.top_drifted_features.length > 0 ? (
                <div className="flex gap-4">
                  {driftData.top_drifted_features.map((f, i) => (
                    <div
                      key={i}
                      className="bg-[var(--bg\_primary)] px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs"
                    >
                      <span className="text-[var(--text\_secondary)]">{f.name}:</span>{' '}
                      <span className="font-mono text-red-400">{f.psi?.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-sm text-[var(--text\_secondary)]">
                  No significant drift detected.
                </span>
              )}
            </div>

            <div className="flex-none">
              {driftData.overall_drift_score > 0.2 ? (
                <button
                  onClick={handleRetrain}
                  disabled={retrainMutation.isPending}
                  className="bg-red-600 hover:bg-red-700 text-[var(--text\_primary)] px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-red-900/20 whitespace-nowrap"
                >
                  Recommend Retraining
                </button>
              ) : (
                <button
                  disabled
                  className="bg-[var(--bg\_tertiary)] text-[var(--text\_secondary)] px-4 py-2 rounded-lg text-sm font-medium opacity-50 cursor-not-allowed whitespace-nowrap border border-[var(--border)]"
                >
                  Retraining Not Required
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Experiment Runs */}
      {activeTab === 'runs' && (
        <div className="pt-4 animate-in fade-in slide-in-from-bottom-2 space-y-4">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <span className="text-[var(--text\_secondary)] text-sm">Experiment:</span>
              <select
                value={selectedExperiment || ''}
                onChange={(e) => setSelectedExperiment(e.target.value)}
                className="bg-[var(--bg\_secondary)] border border-[var(--border)] text-[var(--text\_primary)] text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
              >
                {experiments.map((exp) => (
                  <option key={exp.experiment_id} value={exp.experiment_id}>
                    {exp.name} (ID: {exp.experiment_id})
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => setActiveTab('compare')}
              disabled={selectedRuns.length < 2}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-[var(--text\_primary)] px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              <GitCompare className="w-4 h-4" /> Compare Selected
            </button>
          </div>

          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap">
                <thead className="bg-[var(--bg\_primary)]/80 border-b border-[var(--border)]">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                      Compare
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                      Run ID
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                      Timestamp
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                      Status
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                      Samples
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                      Final Loss / Cont
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]/30">
                  {runsLoading ? (
                    <tr>
                      <td colSpan="6" className="px-6 py-8">
                        <LoadingSpinner />
                      </td>
                    </tr>
                  ) : runs.length === 0 ? (
                    <tr>
                      <td
                        colSpan="6"
                        className="px-6 py-8 text-center text-[var(--text\_secondary)]"
                      >
                        No runs in this experiment.
                      </td>
                    </tr>
                  ) : (
                    runs.map((run) => (
                      <React.Fragment key={run.run_id}>
                        <tr className="hover:bg-[var(--bg\_tertiary)]/50 transition-colors">
                          <td className="px-4 py-4 text-center">
                            <input
                              type="checkbox"
                              checked={selectedRuns.includes(run.run_id)}
                              onChange={() => toggleRunSelection(run.run_id)}
                              className="w-4 h-4 rounded border-[var(--border)] bg-[var(--bg\_primary)] text-blue-500 focus:ring-blue-500 focus:ring-offset-[var(--bg\_secondary)]"
                            />
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() =>
                                setExpandedRun(expandedRun === run.run_id ? null : run.run_id)
                              }
                              className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-2"
                            >
                              <GitCommit className="w-4 h-4" />
                              {run.run_id.substring(0, 8)}
                            </button>
                            <div className="text-[10px] text-[var(--text\_secondary)] mt-0.5">
                              {run.tags?.['mlflow.runName'] || 'unnamed'}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-xs text-[var(--text\_secondary)]">
                            {new Date(parseInt(run.start_time)).toLocaleString()}
                          </td>
                          <td className="px-6 py-4">
                            <span
                              className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                                run.status === 'FINISHED'
                                  ? 'bg-green-500/20 text-green-500'
                                  : run.status === 'FAILED'
                                    ? 'bg-red-500/20 text-red-500'
                                    : 'bg-blue-500/20 text-blue-500'
                              }`}
                            >
                              {run.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-[var(--text\_secondary)]">
                            {run.metrics?.n_samples || '-'}
                          </td>
                          <td className="px-6 py-4 text-sm font-mono text-[var(--text\_secondary)]">
                            {run.metrics?.final_loss
                              ? run.metrics.final_loss.toFixed(4)
                              : run.metrics?.contamination || '-'}
                          </td>
                        </tr>
                        {expandedRun === run.run_id && (
                          <tr className="bg-[var(--bg\_primary)]/50 border-b border-[var(--border)]/50">
                            <td colSpan="6" className="px-8 py-6">
                              {expandedLoading ? (
                                <LoadingSpinner />
                              ) : (
                                <div className="grid grid-cols-2 gap-8">
                                  <div>
                                    <h4 className="text-sm font-bold text-[var(--text\_secondary)] mb-3 uppercase tracking-wider">
                                      Parameters
                                    </h4>
                                    <div className="bg-[var(--bg\_primary)] p-4 rounded-lg border border-[var(--border)]">
                                      {Object.entries(
                                        expandedRunData?.data?.params ||
                                          expandedRunData?.params ||
                                          {},
                                      ).map(([k, v]) => (
                                        <div
                                          key={k}
                                          className="flex justify-between py-1 border-b border-[var(--border)] last:border-0 text-sm"
                                        >
                                          <span className="text-[var(--text\_secondary)]">{k}</span>
                                          <span className="text-[var(--text\_secondary)] font-mono">
                                            {v}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                  <div>
                                    <h4 className="text-sm font-bold text-[var(--text\_secondary)] mb-3 uppercase tracking-wider">
                                      Metrics
                                    </h4>
                                    <div className="bg-[var(--bg\_primary)] p-4 rounded-lg border border-[var(--border)]">
                                      {Object.entries(
                                        expandedRunData?.data?.metrics ||
                                          expandedRunData?.metrics ||
                                          {},
                                      ).map(([k, v]) => (
                                        <div
                                          key={k}
                                          className="flex justify-between py-1 border-b border-[var(--border)] last:border-0 text-sm"
                                        >
                                          <span className="text-[var(--text\_secondary)]">{k}</span>
                                          <span className="text-[var(--text\_secondary)] font-mono">
                                            {typeof v === 'number' ? v.toFixed(4) : v}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Compare Runs */}
      {activeTab === 'compare' && (
        <div className="pt-4 animate-in fade-in slide-in-from-bottom-2 space-y-6">
          {selectedRuns.length < 2 ? (
            <div className="bg-[var(--bg\_secondary)] rounded-xl p-8 border border-[var(--border)] text-center text-[var(--text\_secondary)]">
              <GitCompare className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>
                Select at least 2 runs from the Experiment Runs tab to compare them side-by-side.
              </p>
            </div>
          ) : compareLoading ? (
            <div className="p-10 flex justify-center">
              <LoadingSpinner />
            </div>
          ) : (
            <>
              {/* Metrics Comparison Table */}
              <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden shadow-lg">
                <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--bg\_primary)]/50">
                  <h3 className="text-lg font-bold text-[var(--text\_primary)] flex items-center gap-2">
                    <Database className="w-5 h-5 text-blue-500" /> Metric & Parameter Comparison
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left whitespace-nowrap">
                    <thead className="bg-[var(--bg\_primary)]/80 border-b border-[var(--border)]">
                      <tr>
                        <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase">
                          Field
                        </th>
                        {compareRuns.map((r, i) => (
                          <th
                            key={r.run_id}
                            className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)] uppercase"
                          >
                            <div className="flex items-center gap-2">
                              <div
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: COLORS[i % COLORS.length] }}
                              ></div>
                              {r.name}
                            </div>
                            <div className="text-[10px] text-[var(--text\_secondary)] font-mono lowercase mt-1">
                              {r.run_id.substring(0, 8)}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]/30">
                      {/* Collect all metric keys */}
                      {Array.from(
                        new Set(compareRuns.flatMap((r) => Object.keys(r.metrics || {}))),
                      ).map((metricKey) => (
                        <tr key={`m_${metricKey}`} className="hover:bg-[var(--bg\_tertiary)]/50">
                          <td className="px-6 py-3 text-sm font-bold text-[var(--text\_secondary)]">
                            metric: {metricKey}
                          </td>
                          {compareRuns.map((r) => {
                            const val = r.metrics?.[metricKey]
                            return (
                              <td
                                key={r.run_id}
                                className="px-6 py-3 text-sm font-mono text-[var(--text\_primary)]"
                              >
                                {val !== undefined
                                  ? typeof val === 'number'
                                    ? val.toFixed(4)
                                    : val
                                  : '—'}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                      {/* Collect all param keys */}
                      {Array.from(
                        new Set(compareRuns.flatMap((r) => Object.keys(r.params || {}))),
                      ).map((paramKey) => (
                        <tr
                          key={`p_${paramKey}`}
                          className="hover:bg-[var(--bg\_tertiary)]/50 bg-[var(--bg\_primary)]/20"
                        >
                          <td className="px-6 py-3 text-sm font-bold text-[var(--text\_secondary)]">
                            param: {paramKey}
                          </td>
                          {compareRuns.map((r) => {
                            const val = r.params?.[paramKey]
                            return (
                              <td
                                key={r.run_id}
                                className="px-6 py-3 text-sm font-mono text-[var(--text\_secondary)]"
                              >
                                {val !== undefined ? val : '—'}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Loss Curve Chart */}
              {chartData.length > 0 && (
                <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg">
                  <h3 className="text-lg font-bold text-[var(--text\_primary)] mb-6">
                    Loss Curves per Epoch
                  </h3>
                  <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={chartData}
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                        <XAxis dataKey="epoch" stroke={colors.text_secondary} />
                        <YAxis stroke={colors.text_secondary} />
                        <RechartsTooltip
                          contentStyle={{
                            backgroundColor: colors.bg_secondary,
                            borderColor: colors.border,
                            color: colors.text_primary,
                          }}
                          itemStyle={{ color: colors.text_primary }}
                        />
                        <Legend />
                        {compareRuns.map((r, i) => (
                          <Line
                            key={r.run_id}
                            type="monotone"
                            dataKey={r.name}
                            stroke={COLORS[i % COLORS.length]}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 6 }}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* TAB 4: Training Schedule */}
      {activeTab === 'schedule' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 animate-in fade-in slide-in-from-bottom-2">
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg h-fit">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-[var(--bg\_primary)] rounded-lg text-blue-500 border border-[var(--border)]">
                <Calendar className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-[var(--text\_primary)]">Cron Scheduler</h3>
            </div>

            <div className="bg-[var(--bg\_primary)] rounded-lg border border-[var(--border)] p-5 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
              <h4 className="text-base font-bold text-[var(--text\_primary)] mb-2">
                Weekly Baseline Sync
              </h4>
              <p className="text-sm text-[var(--text\_secondary)] leading-relaxed mb-6">
                Automated background tasks trigger the `run_incremental_retraining` pipeline
                natively evaluating active vectors overriding historical entropy shifts.
              </p>

              <div className="bg-[var(--bg\_secondary)] rounded px-4 py-3 text-sm font-mono text-[var(--text\_secondary)] flex items-center justify-between border border-[var(--border)]">
                <span>Every Sunday</span>
                <span className="text-blue-400 font-bold">02:00 AM UTC</span>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-[var(--border)] flex flex-col gap-3">
              <button
                onClick={handleInitial}
                disabled={
                  initialMutation.isPending ||
                  (jobId && statusData?.status !== 'completed' && statusData?.status !== 'failed')
                }
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-[var(--text\_primary)] font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                {initialMutation.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Play className="h-5 w-5" />
                )}
                Trigger Manual Full Training
              </button>

              <button
                onClick={handleRetrain}
                disabled={
                  retrainMutation.isPending ||
                  (jobId && statusData?.status !== 'completed' && statusData?.status !== 'failed')
                }
                className="w-full bg-[var(--bg\_tertiary)] hover:bg-[var(--bg\_tertiary)] disabled:opacity-50 text-[var(--text\_primary)] font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                {retrainMutation.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <RotateCw className="h-5 w-5" />
                )}
                Trigger Manual Incremental Sync
              </button>
            </div>
          </div>

          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg flex flex-col">
            <h3 className="text-lg font-bold text-[var(--text\_primary)] flex items-center gap-2 mb-4">
              <Activity className="h-5 w-5 text-green-500" /> Active Job Status
            </h3>

            {jobId ? (
              <div className="flex-1 bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg p-5">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-sm font-mono text-[var(--text\_secondary)]">
                    Job: {jobId.substring(0, 12)}...
                  </span>
                  <span
                    className={`text-xs px-2 py-1 rounded font-bold uppercase ${
                      statusData?.status === 'completed'
                        ? 'bg-green-500/20 text-green-500'
                        : statusData?.status === 'failed'
                          ? 'bg-red-500/20 text-red-500'
                          : 'bg-blue-500/20 text-blue-500 animate-pulse'
                    }`}
                  >
                    {statusData?.status || 'starting'}
                  </span>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center gap-3 text-sm">
                    <Loader2
                      className={`h-4 w-4 ${statusData?.status !== 'completed' && statusData?.status !== 'failed' ? 'text-blue-500 animate-spin' : 'text-[var(--text\_secondary)]'}`}
                    />
                    <span className="text-[var(--text\_secondary)]">
                      Step:{' '}
                      {statusData?.current_step || statusData?.step || 'Initializing environment'}
                    </span>
                  </div>

                  {statusData?.error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-400 mt-4">
                      {statusData.error}
                    </div>
                  )}

                  {statusData?.status === 'completed' && (
                    <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                      <h4 className="text-green-400 text-sm font-bold mb-2">Job Successful</h4>
                      <p className="text-xs text-[var(--text\_secondary)]">
                        Check Model Status or Experiment Runs to view new artifacts.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg p-8 flex flex-col items-center justify-center text-center">
                <Clock className="w-12 h-12 text-[var(--text\_secondary)] mb-4" />
                <p className="text-[var(--text\_secondary)]">
                  No active training jobs executing natively right now.
                </p>
                <p className="text-xs text-[var(--text\_secondary)] mt-2">
                  Trigger a manual job or wait for scheduler.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 6: Accuracy */}
      {activeTab === 'accuracy' && (
        <div className="pt-4 animate-in fade-in slide-in-from-bottom-2 space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-[var(--text_primary)] flex items-center gap-2">
              <Target className="w-6 h-6 text-indigo-500" />
              Model Accuracy Evaluation
            </h2>
            {accuracy && !accuracyError && (
              <button
                onClick={() => applyThresholdMutation.mutate(accuracy.optimal_threshold)}
                disabled={applyThresholdMutation.isPending}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-900/20"
              >
                {applyThresholdMutation.isPending ? 'Applying...' : `Apply Optimal Threshold (${accuracy.optimal_threshold.toFixed(2)})`}
              </button>
            )}
          </div>

          {accuracyLoading ? (
            <div className="p-10 flex justify-center"><LoadingSpinner /></div>
          ) : accuracyError && accuracyError.response?.data?.error === 'insufficient data' ? (
            <div className="bg-[var(--bg_secondary)] border border-[var(--border)] rounded-xl p-8 text-center text-[var(--text_secondary)] shadow-lg">
              <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Insufficient labeled data</p>
              <p className="mt-2 text-sm">The accuracy evaluator requires a minimum of 30 analyst-labeled samples. Please label more alerts in the triage queue.</p>
            </div>
          ) : accuracyError ? (
            <ErrorBanner error={accuracyError.message} />
          ) : accuracy ? (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Precision", value: accuracy.precision, format: "pct" },
                  { label: "Recall", value: accuracy.recall, format: "pct" },
                  { label: "F1 Score", value: accuracy.f1_score, format: "pct" },
                  { label: "Accuracy", value: accuracy.accuracy, format: "pct" }
                ].map((stat, i) => (
                  <div key={i} className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-4 shadow-sm">
                    <div className="text-sm text-[var(--text_secondary)]">{stat.label}</div>
                    <div className="text-2xl font-bold text-[var(--text_primary)] mt-1">
                      {(stat.value * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Confusion Matrix */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm flex flex-col items-center">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-6 self-start">Confusion Matrix (Threshold: {accuracy.optimal_threshold.toFixed(2)})</h3>
                  <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                    <div className="bg-green-500/20 border border-green-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-green-400 mb-1">True Positive (TP)</div>
                      <div className="text-2xl font-bold text-green-500">{accuracy.true_positives}</div>
                    </div>
                    <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-red-400 mb-1">False Positive (FP)</div>
                      <div className="text-2xl font-bold text-red-500">{accuracy.false_positives}</div>
                    </div>
                    <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-yellow-400 mb-1">False Negative (FN)</div>
                      <div className="text-2xl font-bold text-yellow-500">{accuracy.false_negatives}</div>
                    </div>
                    <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4 text-center">
                      <div className="text-xs text-blue-400 mb-1">True Negative (TN)</div>
                      <div className="text-2xl font-bold text-blue-500">{accuracy.true_negatives}</div>
                    </div>
                  </div>
                </div>

                {/* PR Curve */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-2 flex justify-between">
                    <span>Precision-Recall Curve</span>
                    <span className="text-sm font-mono text-[var(--text_secondary)]">AUC: {accuracy.pr_auc?.toFixed(3)}</span>
                  </h3>
                  <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={accuracy.threshold_curve || []}
                        margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
                        <XAxis dataKey="recall" type="number" domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <YAxis domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <RechartsTooltip
                          contentStyle={{ backgroundColor: 'var(--bg_secondary)', borderColor: 'var(--border)', color: 'var(--text_primary)' }}
                        />
                        <Line type="monotone" dataKey="precision" stroke="#8b5cf6" strokeWidth={2} dot={false} name="PR Curve" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Threshold Sweep */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm lg:col-span-2">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-4">Threshold Sweep (F1 Maximization)</h3>
                  <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={accuracy.threshold_curve || []}
                        margin={{ top: 5, right: 20, left: -20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
                        <XAxis dataKey="threshold" type="number" domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <YAxis domain={[0, 1]} tick={{ fill: 'var(--text_secondary)', fontSize: 12 }} />
                        <RechartsTooltip
                          contentStyle={{ backgroundColor: 'var(--bg_secondary)', borderColor: 'var(--border)', color: 'var(--text_primary)' }}
                        />
                        <Legend wrapperStyle={{ fontSize: '12px', color: 'var(--text_secondary)' }} />
                        <Line type="monotone" dataKey="precision" stroke="#3b82f6" strokeWidth={2} dot={false} name="Precision" />
                        <Line type="monotone" dataKey="recall" stroke="#ef4444" strokeWidth={2} dot={false} name="Recall" />
                        <Line type="monotone" dataKey="f1" stroke="#10b981" strokeWidth={3} dot={false} name="F1 Score" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Per Model AUC & Calibration */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-4">Model Contributions (AUC-ROC)</h3>
                  <div className="space-y-4">
                    {Object.entries(accuracy.per_model_auc || {}).map(([model, aucScore]) => (
                      <div key={model}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-[var(--text_secondary)] font-mono">{model}</span>
                          <span className="text-[var(--text_primary)]">{aucScore.toFixed(3)}</span>
                        </div>
                        <div className="w-full bg-[var(--bg_primary)] rounded-full h-2">
                          <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${Math.max(0, aucScore) * 100}%` }}></div>
                        </div>
                      </div>
                    ))}
                    <div className="mt-6 pt-4 border-t border-[var(--border)]">
                      <div className="flex justify-between text-sm">
                        <span className="text-[var(--text_secondary)]">Expected Calibration Error (ECE):</span>
                        <span className="text-yellow-400 font-mono">{(accuracy.calibration_error * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Per Rule Precision */}
                <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-sm">
                  <h3 className="text-md font-bold text-[var(--text_primary)] mb-4">Rule Precision Breakdown</h3>
                  <div className="overflow-y-auto max-h-[200px] border border-[var(--border)] rounded-lg">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-[var(--bg_primary)] sticky top-0">
                        <tr>
                          <th className="px-4 py-2 font-semibold text-[var(--text_secondary)]">Rule ID</th>
                          <th className="px-4 py-2 font-semibold text-[var(--text_secondary)]">Precision</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {Object.entries(accuracy.per_rule_precision || {}).sort((a, b) => b[1] - a[1]).map(([rule, prec]) => (
                          <tr key={rule} className="hover:bg-[var(--bg_tertiary)]">
                            <td className="px-4 py-2 font-mono text-[var(--text_primary)]">{rule}</td>
                            <td className="px-4 py-2 text-[var(--text_primary)]">{(prec * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                        {Object.keys(accuracy.per_rule_precision || {}).length === 0 && (
                          <tr><td colSpan="2" className="px-4 py-4 text-center text-xs text-[var(--text_secondary)]">No rule triggers in feedback.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  )
}
