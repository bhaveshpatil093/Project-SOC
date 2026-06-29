import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { 
  Activity, 
  BrainCircuit, 
  MessageSquare, 
  Clock, 
  AlertTriangle,
  Target,
  BarChart2,
  PieChart,
  Lightbulb,
  PlusCircle
} from 'lucide-react'
import { LoadingSpinner } from '../common/LoadingSpinner'

// Standard Recharts components for data visualization
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart as RechartsPieChart, Pie, Cell, Legend
} from 'recharts'

export const SLMAnalyticsPanel = () => {
  const [activeTab, setActiveTab] = useState('performance')

  const { data, isLoading } = useQuery({
    queryKey: ['slmAnalytics'],
    queryFn: async () => {
      const res = await apiClient.get('/api/slm/analytics')
      return res.data
    },
    refetchInterval: 60000
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  if (!data) return null

  const { trends, top_questions, knowledge_gaps, most_investigated } = data

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

  const pieData = Object.entries(trends.query_type_distribution || {}).map(([name, value]) => ({
    name,
    value
  }))

  const renderPerformanceTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)]">
          <div className="flex items-center gap-2 mb-2 text-[var(--text-secondary)]">
            <MessageSquare className="w-4 h-4" />
            <span className="font-semibold text-sm">Total Queries (30d)</span>
          </div>
          <p className="text-2xl font-bold text-[var(--text-primary)]">
            {trends.daily_queries?.reduce((acc, curr) => acc + curr.count, 0) || 0}
          </p>
        </div>
        <div className="bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)]">
          <div className="flex items-center gap-2 mb-2 text-[var(--text-secondary)]">
            <Clock className="w-4 h-4" />
            <span className="font-semibold text-sm">Peak Usage Hour</span>
          </div>
          <p className="text-2xl font-bold text-[var(--text-primary)]">
            {trends.peak_hour}:00
          </p>
        </div>
        <div className="bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)]">
          <div className="flex items-center gap-2 mb-2 text-[var(--text-secondary)]">
            <Activity className="w-4 h-4" />
            <span className="font-semibold text-sm">Avg Quality Score</span>
          </div>
          <p className="text-2xl font-bold text-[var(--text-primary)]">
            {(trends.quality_score_trend?.reduce((acc, curr) => acc + curr.avg_quality, 0) / (trends.quality_score_trend?.length || 1) || 0).toFixed(2)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Daily Query Volume</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends.daily_queries}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={12} tickFormatter={(val) => new Date(val).toLocaleDateString()} />
                <YAxis stroke="var(--text-secondary)" fontSize={12} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Query Type Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }} />
                <Legend />
              </RechartsPieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)] col-span-2">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Avg Response Time (ms)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends.avg_response_time_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={12} tickFormatter={(val) => new Date(val).toLocaleDateString()} />
                <YAxis stroke="var(--text-secondary)" fontSize={12} />
                <RechartsTooltip contentStyle={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }} />
                <Line type="monotone" dataKey="avg_ms" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )

  const renderKnowledgeGapsTab = () => (
    <div className="space-y-4">
      <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4 flex gap-3 text-orange-500">
        <Lightbulb className="w-5 h-5 flex-shrink-0" />
        <p className="text-sm">These topics represent areas where the SLM produced responses with a quality score below 0.5. Consider adding related examples to the training dataset to improve model accuracy.</p>
      </div>

      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--bg-tertiary)] border-b border-[var(--border)]">
            <tr>
              <th className="px-6 py-4 font-semibold text-[var(--text-secondary)]">Topic / Question</th>
              <th className="px-6 py-4 font-semibold text-[var(--text-secondary)] text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {knowledge_gaps?.length === 0 ? (
              <tr><td colSpan="2" className="p-8 text-center text-[var(--text-secondary)]">No significant knowledge gaps detected.</td></tr>
            ) : (
              knowledge_gaps?.map((gap, i) => (
                <tr key={i} className="hover:bg-[var(--bg-tertiary)]/50 transition-colors">
                  <td className="px-6 py-4 text-[var(--text-primary)]">{gap}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 transition-colors">
                      <PlusCircle className="w-3.5 h-3.5" /> Add to Training Data
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderTopQuestionsTab = () => (
    <div className="grid grid-cols-2 gap-6">
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm flex flex-col h-[500px]">
        <div className="p-4 border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
          <h3 className="font-semibold flex items-center gap-2 text-[var(--text-primary)]">
            <MessageSquare className="w-4 h-4 text-blue-500" />
            Most Common Questions
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto">
          <ul className="divide-y divide-[var(--border)]">
            {top_questions?.map((q, i) => (
              <li key={i} className="p-4 hover:bg-[var(--bg-tertiary)]/50 transition-colors flex justify-between items-center gap-4">
                <span className="text-sm font-medium text-[var(--text-primary)] line-clamp-2">{q.cluster}</span>
                <span className="px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-500 text-xs font-bold whitespace-nowrap">
                  {q.count} queries
                </span>
              </li>
            ))}
            {(!top_questions || top_questions.length === 0) && (
              <li className="p-8 text-center text-[var(--text-secondary)] text-sm">Not enough data to cluster questions yet.</li>
            )}
          </ul>
        </div>
      </div>

      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm flex flex-col h-[500px]">
        <div className="p-4 border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
          <h3 className="font-semibold flex items-center gap-2 text-[var(--text-primary)]">
            <Target className="w-4 h-4 text-purple-500" />
            Most Investigated Entities
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto">
          <ul className="divide-y divide-[var(--border)]">
            {most_investigated?.map((entity, i) => (
              <li key={i} className="p-4 hover:bg-[var(--bg-tertiary)]/50 transition-colors flex justify-between items-center">
                <div className="flex flex-col">
                  <span className="text-xs text-[var(--text-secondary)] uppercase font-bold tracking-wider mb-1">Alert ID</span>
                  <span className="text-sm font-mono text-[var(--text-primary)]">{entity.alert_id}</span>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-purple-500/10 text-purple-500 text-xs font-bold whitespace-nowrap">
                  {entity.queries} queries
                </span>
              </li>
            ))}
            {(!most_investigated || most_investigated.length === 0) && (
              <li className="p-8 text-center text-[var(--text-secondary)] text-sm">No entity investigations recorded.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex gap-2 p-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('performance')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'performance' ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <BarChart2 className="w-4 h-4" /> Performance Trends
        </button>
        <button
          onClick={() => setActiveTab('gaps')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'gaps' ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <AlertTriangle className="w-4 h-4" /> Knowledge Gaps
        </button>
        <button
          onClick={() => setActiveTab('questions')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'questions' ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <PieChart className="w-4 h-4" /> Top Questions
        </button>
      </div>

      <div className="min-h-[400px]">
        {activeTab === 'performance' && renderPerformanceTab()}
        {activeTab === 'gaps' && renderKnowledgeGapsTab()}
        {activeTab === 'questions' && renderTopQuestionsTab()}
      </div>
    </div>
  )
}
