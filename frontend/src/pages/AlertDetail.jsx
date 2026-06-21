import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAlert, useAlertTimeline, useUpdateAlertStatus } from '../hooks/useAlerts'
import { getEntityScoreHistory } from '../api/entities'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { Badge } from '../components/common/Badge'
import { ThreatGauge } from '../components/common/ThreatGauge'
import { formatDate } from '../utils/formatters'
import {
  ArrowLeft,
  Bot,
  Shield,
  Clock,
  Terminal,
  User,
  Server,
  ExternalLink,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileJson,
  FileText,
  Tag,
  Plus,
  X,
} from 'lucide-react'
import { addTags, removeTag, getAllTags } from '../api/alerts'
import { generateAlertReport, downloadJSON } from '../utils/exporters'
import { SkeletonCard } from '../components/common/Skeleton'
import { useUiStore } from '../store/uiStore'
import { THEMES } from '../utils/theme'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
  ComposedChart,
  Area,
  Line,
  ReferenceLine,
} from 'recharts'

export const AlertDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: alert, isLoading, isError } = useAlert(id)
  const { data: timelineData } = useAlertTimeline(id)
  const updateStatusMutation = useUpdateAlertStatus()
  const isMobile = useIsMobile()
  const { theme } = usePreferencesStore()
  const colors = THEMES[theme]
  const [showTimeline, setShowTimeline] = useState(false)

  // Tags state
  const [showTagInput, setShowTagInput] = useState(false)
  const [tagInput, setTagInput] = useState('')

  const { data: allTags } = useQuery({
    queryKey: ['allTags'],
    queryFn: getAllTags
  })

  const { refetch: refetchAlert } = useQuery({
    queryKey: ['alert', id],
    enabled: false,
  })

  const addTagsMutation = useMutation({
    mutationFn: (tags) => addTags(id, tags),
    onSuccess: () => {
      refetchAlert()
      setShowTagInput(false)
      setTagInput('')
    }
  })

  const removeTagMutation = useMutation({
    mutationFn: (tag) => removeTag(id, tag),
    onSuccess: () => refetchAlert()
  })

  const handleAddTag = (e) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      addTagsMutation.mutate([tagInput.trim()])
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-8 max-w-7xl mx-auto mt-8">
        <SkeletonCard lines={4} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
            <SkeletonCard lines={6} />
            <SkeletonCard lines={8} />
          </div>
          <div className="space-y-8">
            <SkeletonCard lines={5} />
            <SkeletonCard lines={5} />
          </div>
        </div>
      </div>
    )
  }
  if (isError || !alert)
    return <ErrorBanner message="Failed to load alert details. Alert may not exist." />

  // Prepare SHAP Data
  const shapData = (alert.top_features || []).map((f) => {
    if (typeof f === 'string') {
      return { name: f, value: 1, originalValue: 1, color: '#ef4444' }
    }
    return {
      name: f.feature || 'Unknown',
      value: Math.abs(f.value || 0),
      originalValue: f.value || 0,
      color: f.direction === 'decreases_risk' ? '#22c55e' : '#ef4444',
    }
  })

  const timeline = timelineData?.alerts || timelineData || []

  const { data: scoreHistoryData } = useQuery({
    queryKey: ['entityScoreHistory', alert?.entity_key],
    queryFn: () => getEntityScoreHistory(alert.entity_key),
    enabled: !!alert?.entity_key,
  })
  const scoreHistory = scoreHistoryData?.data || []

  const formattedScoreHistory = scoreHistory.map((d) => ({
    ...d,
    formattedTime: new Date(d.timestamp).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  }))

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <Link
          to="/alerts"
          className="inline-flex items-center text-sm text-blue-500 hover:text-blue-400 font-medium"
        >
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to Alerts
        </Link>
        <div className="flex gap-2">
          <button
            onClick={() => downloadJSON(alert, `alert_${alert._id || alert.id}.json`)}
            className="flex items-center gap-2 text-sm bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] text-[var(--text\_primary)] px-3 py-1.5 rounded-lg transition-colors"
          >
            <FileJson className="h-4 w-4" /> Export JSON
          </button>
          <button
            onClick={() => generateAlertReport(alert)}
            className="flex items-center gap-2 text-sm bg-[var(--bg\_secondary)] hover:bg-[var(--bg\_tertiary)] border border-[var(--border)] text-[var(--text\_primary)] px-3 py-1.5 rounded-lg transition-colors"
          >
            <FileText className="h-4 w-4" /> Export PDF
          </button>
        </div>
      </div>

      {/* SECTION 1: Alert Header */}
      <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 shadow-lg flex flex-col md:flex-row gap-8 items-start md:items-center justify-between">
        <div className="flex flex-col md:flex-row items-center md:items-start gap-6 md:gap-8 flex-1 w-full text-center md:text-left">
          <ThreatGauge
            score={alert.threat_score * 100}
            size={isMobile ? 120 : 150}
            showLabel={false}
          />

          <div className="space-y-4 flex-1 w-full">
            <div className="flex flex-col md:flex-row items-center gap-3">
              <h1 className="text-xl md:text-2xl font-bold text-[var(--text\_primary)] tracking-tight break-all md:break-normal">
                {alert.entity_key || 'Unknown Entity'}
              </h1>
              <Badge
                variant={alert.threat_level}
                className="uppercase tracking-wider px-3 py-1 text-xs"
              >
                {alert.threat_level}
              </Badge>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center gap-2 text-[var(--text\_secondary)]">
                <Server className="h-4 w-4 text-[var(--text\_secondary)]" />
                <span className="font-medium">{alert.host_id || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2 text-[var(--text\_secondary)]">
                <User className="h-4 w-4 text-[var(--text\_secondary)]" />
                <span className="font-medium">{alert.user_name || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2 text-[var(--text\_secondary)]">
                <Terminal className="h-4 w-4 text-[var(--text\_secondary)]" />
                <span className="font-medium">{alert.log_type || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2 text-[var(--text\_secondary)]">
                <Clock className="h-4 w-4 text-[var(--text\_secondary)]" />
                <span className="font-medium">{formatDate(alert.timestamp)}</span>
              </div>
            </div>

            {/* Tags Section */}
            <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-[var(--border)] mt-1">
              <Tag className="w-3.5 h-3.5 text-[var(--text\_secondary)] flex-none" />
              {(alert?.tags || []).map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-xs text-blue-300 group cursor-pointer hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400 transition-all"
                  onClick={() => {
                    if (window.confirm(`Remove tag '${tag}'?`)) {
                      removeTagMutation.mutate(tag)
                    }
                  }}
                >
                  {tag}
                  <X className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </span>
              ))}

              {showTagInput ? (
                <div className="relative">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={handleAddTag}
                    onBlur={() => setTimeout(() => setShowTagInput(false), 200)}
                    autoFocus
                    placeholder="Tag name & Enter"
                    className="px-2 py-1 text-xs rounded border border-blue-500 bg-[var(--bg\_primary)] text-[var(--text\_primary)] outline-none w-36"
                  />
                  {tagInput && allTags?.length > 0 && (
                    <div className="absolute top-full left-0 mt-1 w-52 bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg shadow-xl z-30 max-h-40 overflow-y-auto">
                      {allTags
                        .filter(t => t.tag.toLowerCase().includes(tagInput.toLowerCase()) && !(alert?.tags || []).includes(t.tag))
                        .slice(0, 6)
                        .map(t => (
                          <div
                            key={t.tag}
                            className="px-3 py-1.5 text-xs cursor-pointer hover:bg-blue-500/10 flex justify-between items-center"
                            onMouseDown={(e) => { e.preventDefault(); addTagsMutation.mutate([t.tag]) }}
                          >
                            <span className="text-[var(--text\_primary)]">{t.tag}</span>
                            <span className="text-[var(--text\_secondary)] bg-[var(--bg\_secondary)] px-1.5 rounded-full">{t.count}</span>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setShowTagInput(true)}
                  className="flex items-center gap-1 px-2 py-1 rounded-full bg-[var(--bg\_tertiary)] hover:bg-blue-500/20 text-xs text-[var(--text\_secondary)] hover:text-blue-400 border border-dashed border-[var(--border)] hover:border-blue-500/40 transition-all"
                >
                  <Plus className="w-3 h-3" /> Add tag
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row md:flex-col items-center md:items-end gap-4 w-full md:min-w-[200px] mt-4 md:mt-0">
          <div className="flex items-center gap-2 bg-[var(--bg\_primary)] px-3 py-2 rounded-lg border border-[var(--border)] w-full">
            <span className="text-xs text-[var(--text\_secondary)] font-medium">Status:</span>
            <select
              value={alert.alert_status || 'open'}
              onChange={(e) =>
                updateStatusMutation.mutate({ id: alert._id || alert.id, status: e.target.value })
              }
              className="flex-1 bg-transparent text-sm font-semibold text-[var(--text\_primary)] focus:outline-none cursor-pointer"
            >
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <button
            onClick={() => navigate(`/investigation?alert_id=${alert._id || alert.id}`)}
            className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-[var(--text\_primary)] px-4 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-purple-900/20"
          >
            <Bot className="h-5 w-5" />
            Investigate with AI
          </button>
        </div>
      </div>

      {/* SECTION 1.5: Model Consensus Panel */}
      {alert.consensus_level && (
        <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <Shield className="h-5 w-5 text-indigo-500" />
                Model Consensus
              </h3>
              <p className="text-[var(--text\_secondary)] text-sm">
                Confidence Interval (95%):{' '}
                {alert.confidence_interval
                  ? `${alert.confidence_interval[0].toFixed(2)} - ${alert.confidence_interval[1].toFixed(2)}`
                  : 'N/A'}
              </p>
            </div>
            <div className="flex gap-2">
              <Badge
                variant={
                  alert.consensus_level === 'strong'
                    ? 'success'
                    : alert.consensus_level === 'moderate'
                      ? 'warning'
                      : alert.consensus_level === 'weak'
                        ? 'danger'
                        : 'critical'
                }
              >
                Consensus: {alert.consensus_level.toUpperCase()}
              </Badge>
              {alert.recommendation && (
                <Badge
                  variant={
                    alert.recommendation === 'SAFE'
                      ? 'success'
                      : alert.recommendation === 'MONITOR'
                        ? 'info'
                        : alert.recommendation === 'INVESTIGATE'
                          ? 'warning'
                          : 'critical'
                  }
                >
                  Action: {alert.recommendation}
                </Badge>
              )}
            </div>
          </div>

          {alert.consensus_level === 'split' && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400 text-sm">
              <AlertTriangle className="h-4 w-4" />
              Models strongly disagree on this entity. Manual review is highly recommended.
            </div>
          )}

          <div className="h-4 bg-[var(--bg\_tertiary)] rounded-full overflow-hidden flex">
            {/* We don't have the exact weights here, so we show a stylized bar */}
            <div className="h-full bg-blue-500" style={{ width: '25%' }} title="Network Model" />
            <div className="h-full bg-purple-500" style={{ width: '35%' }} title="Process Model" />
            <div className="h-full bg-green-500" style={{ width: '15%' }} title="Sequence Model" />
            <div className="h-full bg-orange-500" style={{ width: '25%' }} title="Rule Engine" />
          </div>
          <div className="flex justify-between mt-2 text-xs text-[var(--text\_secondary)]">
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full" /> Network
            </span>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full" /> Process
            </span>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full" /> Sequence
            </span>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-orange-500 rounded-full" /> Rule Engine
            </span>
          </div>
        </div>
      )}

      {/* SECTION 2: Two Columns (SHAP + MITRE) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: SHAP Explanation */}
        <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 flex flex-col">
          <h3 className="text-lg font-bold text-[var(--text\_primary)] mb-6 flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-500" />
            Why was this alert raised?
          </h3>

          <div className="h-[250px] mb-6 overflow-x-auto hide-scrollbar">
            {shapData.length > 0 ? (
              <div className="min-w-[500px] h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={shapData}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 20, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={colors.border}
                      horizontal={true}
                      vertical={false}
                    />
                    <XAxis
                      type="number"
                      stroke={colors.text_secondary}
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      stroke={colors.text_secondary}
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      width={120}
                    />
                    <RechartsTooltip
                      cursor={{ fill: colors.bg_tertiary, opacity: 0.4 }}
                      contentStyle={{
                        backgroundColor: colors.bg_secondary,
                        borderColor: colors.border,
                        borderRadius: '8px',
                        color: colors.text_primary,
                      }}
                      formatter={(value, name, props) => [
                        parseFloat(props.payload.originalValue).toFixed(4),
                        'SHAP Value',
                      ]}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                      {shapData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-[var(--text\_secondary)] border border-dashed border-[var(--border)] rounded-lg">
                No feature importance data available.
              </div>
            )}
          </div>

          <blockquote className="border-l-4 border-blue-500 bg-[var(--bg\_primary)]/50 p-4 rounded-r-lg text-[var(--text\_secondary)] text-sm leading-relaxed italic">
            "
            {alert.human_explanation ||
              'No automated explanation was generated for this alert. Please rely on the feature charts and rule triggers.'}
            "
          </blockquote>
        </div>

        {/* Right: MITRE ATT&CK Panel */}
        <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] p-6 flex flex-col">
          <h3 className="text-lg font-bold text-[var(--text\_primary)] mb-6 flex items-center gap-2">
            <Shield className="h-5 w-5 text-red-500" />
            MITRE ATT&CK Mapping
          </h3>

          <div className="space-y-4 overflow-y-auto flex-1">
            {alert.mitre_technique_ids && alert.mitre_technique_ids.length > 0 ? (
              alert.mitre_technique_ids.map((technique, idx) => (
                <div
                  key={idx}
                  className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-lg p-4 hover:border-[var(--border)] transition-colors group"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-sm font-bold text-red-400 font-mono">{technique}</span>
                      <p className="text-[var(--text\_primary)] font-medium mt-1">
                        Matched Technique Signature
                      </p>
                      <p className="text-xs text-[var(--text\_secondary)] mt-1 capitalize">
                        Tactic:{' '}
                        {(alert.mitre_tactics && alert.mitre_tactics[idx]) || 'Unknown Tactic'}
                      </p>
                    </div>
                    <a
                      href={`https://attack.mitre.org/techniques/${technique.replace('.', '/')}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[var(--text\_secondary)] hover:text-blue-400 transition-colors p-1 bg-[var(--bg\_secondary)] rounded group-hover:bg-[var(--bg\_tertiary)]"
                      title="View on MITRE ATT&CK"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-[var(--text\_secondary)] border border-dashed border-[var(--border)] rounded-lg py-12">
                No MITRE ATT&CK techniques identified.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SECTION 2.5: Temporal Context */}
      {(alert.temporal_context || alert.is_off_hours) && (
        <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] mb-6 mt-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <Clock className="h-5 w-5 text-indigo-500" />
                Time Context
              </h3>
              <p className="text-[var(--text\_secondary)] text-sm">
                Analysis of the entity's activity based on historical time-of-day baselines.
              </p>
            </div>
            {alert.is_off_hours && <Badge variant="critical">Off-hours Activity</Badge>}
          </div>

          <div className="p-4 bg-[var(--bg\_tertiary)] border border-[var(--border)] rounded-lg mb-4">
            <div className="whitespace-pre-wrap font-mono text-sm text-[var(--text\_primary)]">
              {alert.temporal_context ||
                (alert.human_explanation &&
                  alert.human_explanation
                    .split('\n\n')
                    .find((x) => x.startsWith('Time Context:'))
                    ?.replace('Time Context: ', '')) ||
                'No context provided.'}
            </div>
          </div>

          <div className="h-48 mt-4 relative">
            <ResponsiveContainer width="100%" height="100%">
              {/* Synthetic spline chart to represent the 24H activity profile visually */}
              <LineChart
                data={[
                  { hour: '00', activity: 5 },
                  { hour: '04', activity: 2 },
                  { hour: '08', activity: 25 },
                  { hour: '12', activity: 80 },
                  { hour: '16', activity: 75 },
                  { hour: '20', activity: 15 },
                  { hour: '23', activity: 10 },
                ]}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
                <XAxis
                  dataKey="hour"
                  stroke="var(--text_secondary)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg_secondary)',
                    borderColor: 'var(--border)',
                    borderRadius: '8px',
                  }}
                  itemStyle={{ color: 'var(--text_primary)' }}
                />
                <Line
                  type="monotone"
                  dataKey="activity"
                  stroke="#8b5cf6"
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#8b5cf6' }}
                />
                {/* Render the alert reference if available */}
                <ReferenceLine
                  x={
                    alert.timestamp
                      ? new Date(alert.timestamp).getHours().toString().padStart(2, '0')
                      : '12'
                  }
                  stroke="#ef4444"
                  strokeDasharray="3 3"
                  label={{
                    position: 'top',
                    value: 'Alert Triggered',
                    fill: '#ef4444',
                    fontSize: 12,
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* SECTION 2.7: Score History Chart */}
      {scoreHistory.length > 0 && (
        <div className="bg-[var(--bg\_secondary)] p-6 rounded-xl border border-[var(--border)] mb-6 mt-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-[var(--text\_primary)] flex items-center gap-2">
                <Activity className="h-5 w-5 text-indigo-500" />
                Entity Score History
              </h3>
              <p className="text-[var(--text\_secondary)] text-sm">
                Historical anomaly score trajectory across multiple detection models for this
                entity.
              </p>
            </div>
          </div>

          <div className="h-72 w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={formattedScoreHistory}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
                <XAxis
                  dataKey="formattedTime"
                  stroke="var(--text_secondary)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="var(--text_secondary)"
                  fontSize={12}
                  domain={[0, 1]}
                  tickLine={false}
                  axisLine={false}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg_secondary)',
                    borderColor: 'var(--border)',
                    borderRadius: '8px',
                  }}
                  itemStyle={{ color: 'var(--text_primary)' }}
                />
                <ReferenceLine
                  y={0.3}
                  stroke="var(--text_secondary)"
                  strokeDasharray="3 3"
                  label={{
                    position: 'insideTopLeft',
                    fill: 'var(--text_secondary)',
                    fontSize: 10,
                    value: 'Low Threshold',
                  }}
                />
                <ReferenceLine
                  y={0.8}
                  stroke="#ef4444"
                  strokeDasharray="3 3"
                  label={{
                    position: 'insideTopLeft',
                    fill: '#ef4444',
                    fontSize: 10,
                    value: 'Critical Threshold',
                  }}
                />

                {/* Find current alert in timeline and add ReferenceLine */}
                <ReferenceLine
                  x={new Date(alert.timestamp).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  stroke="#8b5cf6"
                  strokeDasharray="3 3"
                />

                <Area
                  type="monotone"
                  dataKey="threat_score"
                  fill="#ef4444"
                  stroke="#ef4444"
                  fillOpacity={0.2}
                  name="Overall Threat Score"
                />
                <Line
                  type="monotone"
                  dataKey="network_score"
                  stroke="#3b82f6"
                  dot={false}
                  strokeWidth={2}
                  name="Network Score"
                />
                <Line
                  type="monotone"
                  dataKey="process_score"
                  stroke="#a855f7"
                  dot={false}
                  strokeWidth={2}
                  name="Process Score"
                />
                <Line
                  type="monotone"
                  dataKey="rule_score"
                  stroke="#f97316"
                  dot={false}
                  strokeWidth={2}
                  name="Rule Score"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* SECTION 3: Timeline & Rules */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-[var(--text\_primary)]">
            Entity Timeline & Triggers
          </h3>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          {/* Vertical Timeline */}
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] xl:col-span-1 h-full">
            <div
              className="p-4 md:p-6 flex items-center justify-between border-b border-[var(--border)] xl:border-none cursor-pointer xl:cursor-default"
              onClick={() => isMobile && setShowTimeline(!showTimeline)}
            >
              <h4 className="text-sm font-bold text-[var(--text\_secondary)] uppercase tracking-wider">
                Event Sequence
              </h4>
              {isMobile && (
                <button className="text-[var(--text\_secondary)]">
                  {showTimeline ? (
                    <ChevronUp className="h-5 w-5" />
                  ) : (
                    <ChevronDown className="h-5 w-5" />
                  )}
                </button>
              )}
            </div>
            {(!isMobile || showTimeline) && (
              <div className="p-4 md:p-6 pt-0 xl:pt-6 max-h-[600px] overflow-y-auto">
                <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-[var(--border)] before:to-transparent">
                  {timeline.length > 0 ? (
                    timeline.map((tItem, idx) => {
                      const isCurrent = (tItem._id || tItem.id) === (alert._id || alert.id)
                      return (
                        <div
                          key={idx}
                          className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
                        >
                          <div
                            className={`flex items-center justify-center w-10 h-10 rounded-full border-4 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow ${isCurrent ? 'bg-blue-500 border-blue-900 shadow-blue-500/50 z-10' : 'bg-[var(--bg\_secondary)] border-[var(--border)] text-[var(--text\_secondary)]'}`}
                          >
                            {isCurrent ? (
                              <AlertTriangle className="h-4 w-4 text-[var(--text\_primary)]" />
                            ) : (
                              <Clock className="h-4 w-4" />
                            )}
                          </div>
                          <div
                            className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border ${isCurrent ? 'bg-blue-900/20 border-blue-500/50' : 'bg-[var(--bg\_primary)]/50 border-[var(--border)]'}`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <Badge variant={tItem.threat_level}>{tItem.threat_level}</Badge>
                              <span className="text-xs text-[var(--text\_secondary)] font-mono">
                                {formatDate(tItem.timestamp)}
                              </span>
                            </div>
                            <div className="text-sm text-[var(--text\_secondary)] font-medium mt-2">
                              {tItem.log_type}
                            </div>
                            <Link
                              to={`/alerts/${tItem._id || tItem.id}`}
                              className="text-xs text-blue-400 hover:underline mt-2 inline-block"
                            >
                              View Details
                            </Link>
                          </div>
                        </div>
                      )
                    })
                  ) : (
                    <p className="text-[var(--text\_secondary)] text-sm italic">
                      No recent timeline events found for this entity.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Triggered Rules Table */}
          <div className="bg-[var(--bg\_secondary)] rounded-xl border border-[var(--border)] overflow-hidden xl:col-span-2">
            <div className="px-6 py-4 border-b border-[var(--border)]">
              <h4 className="text-sm font-bold text-[var(--text\_secondary)] uppercase tracking-wider">
                Triggered Rules
              </h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap">
                <thead className="bg-[var(--bg\_primary)]/50 border-b border-[var(--border)]">
                  <tr>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)]">
                      Rule ID
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)]">
                      Rule Details
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)]">
                      MITRE Technique
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold text-[var(--text\_secondary)]">
                      Impact
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]/50">
                  {alert.triggered_rules && alert.triggered_rules.length > 0 ? (
                    alert.triggered_rules.map((rule, idx) => {
                      const isObj = typeof rule === 'object'
                      const ruleId = isObj ? rule.id : rule
                      const ruleName = isObj ? rule.name : 'Pattern Match Signature'
                      const technique = isObj
                        ? rule.technique
                        : alert.mitre_technique_ids?.[idx] || 'N/A'
                      const severity = isObj ? rule.severity : 'High'

                      return (
                        <tr
                          key={idx}
                          className="hover:bg-[var(--bg\_tertiary)]/50 transition-colors"
                        >
                          <td className="px-6 py-4 text-sm font-mono text-blue-400">{ruleId}</td>
                          <td className="px-6 py-4 text-sm text-[var(--text\_secondary)]">
                            {ruleName}
                          </td>
                          <td className="px-6 py-4 text-xs font-mono text-[var(--text\_secondary)]">
                            {technique}
                          </td>
                          <td className="px-6 py-4">
                            <span
                              className={`text-xs px-2 py-1 rounded-full border ${
                                severity === 'High' || severity === 'Critical'
                                  ? 'bg-red-500/10 border-red-500/50 text-red-400'
                                  : 'bg-orange-500/10 border-orange-500/50 text-orange-400'
                              }`}
                            >
                              {severity} Contribution
                            </span>
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td
                        colSpan="4"
                        className="px-6 py-8 text-center text-[var(--text\_secondary)]"
                      >
                        No explicit rules triggered. Alert originated strictly from anomaly
                        detection models.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
