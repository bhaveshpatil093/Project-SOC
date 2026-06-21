import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { Users, UserPlus, Clock, Target, AlertTriangle, Shield, CheckCircle } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const TeamCard = ({ team, onClick, isSelected }) => {
  return (
    <div 
      onClick={onClick}
      className={`p-4 rounded-xl border transition-all cursor-pointer ${
        isSelected 
          ? 'border-blue-500 bg-blue-500/10' 
          : 'border-[var(--border)] bg-[var(--bg\_secondary)] hover:border-blue-400/50 hover:bg-[var(--bg\_tertiary)]'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-lg flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-400" />
          {team.name}
        </h3>
        <span className="text-xs font-mono px-2 py-1 rounded bg-[var(--bg\_primary)] text-[var(--text\_secondary)]">
          {team.team_id}
        </span>
      </div>
      <p className="text-sm text-[var(--text\_secondary)] mb-4">{team.description}</p>
      
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1.5 text-[var(--text\_secondary)]">
          <Users className="w-4 h-4" />
          {team.members.length} Members
        </div>
        <div className="flex items-center gap-1.5 text-amber-400">
          <AlertTriangle className="w-4 h-4" />
          {team.alert_filters?.max_threat_level || 'All'} Max Level
        </div>
      </div>
    </div>
  )
}

const TeamDetail = ({ team }) => {
  const [newMember, setNewMember] = useState('')
  const queryClient = useQueryClient()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['teamStats', team.team_id],
    queryFn: async () => {
      const res = await apiClient.get(`/api/admin/teams/${team.team_id}/stats`)
      return res.data.stats
    }
  })

  const addMemberMutation = useMutation({
    mutationFn: (username) => apiClient.post(`/api/admin/teams/${team.team_id}/members`, { username }),
    onSuccess: () => {
      queryClient.invalidateQueries(['teams'])
      setNewMember('')
    }
  })

  if (isLoading) return <div className="h-64 flex items-center justify-center"><LoadingSpinner /></div>

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[var(--bg\_secondary)] p-4 rounded-xl border border-[var(--border)]">
          <div className="text-[var(--text\_secondary)] text-sm mb-1 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" /> Alerts Triaged (7d)
          </div>
          <div className="text-3xl font-bold">{stats?.alerts_triaged || 0}</div>
        </div>
        <div className="bg-[var(--bg\_secondary)] p-4 rounded-xl border border-[var(--border)]">
          <div className="text-[var(--text\_secondary)] text-sm mb-1 flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" /> Avg Response
          </div>
          <div className="text-3xl font-bold">{stats?.avg_response_time || 0} <span className="text-lg text-[var(--text\_secondary)] font-normal">min</span></div>
        </div>
        <div className="bg-[var(--bg\_secondary)] p-4 rounded-xl border border-[var(--border)]">
          <div className="text-[var(--text\_secondary)] text-sm mb-1 flex items-center gap-2">
            <Target className="w-4 h-4 text-purple-400" /> FP Rate
          </div>
          <div className="text-3xl font-bold">{stats?.fp_rate || 0}%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Members List */}
        <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
          <div className="p-4 border-b border-[var(--border)] flex justify-between items-center bg-black/20">
            <h3 className="font-bold flex items-center gap-2">
              <Users className="w-4 h-4" /> Team Members
            </h3>
            <div className="flex items-center gap-2">
              <input 
                type="text" 
                placeholder="Username" 
                value={newMember}
                onChange={(e) => setNewMember(e.target.value)}
                className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded px-2 py-1 text-sm w-32"
              />
              <button 
                onClick={() => newMember && addMemberMutation.mutate(newMember)}
                disabled={addMemberMutation.isPending}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-2 py-1 rounded text-sm flex items-center gap-1 transition-colors"
              >
                <UserPlus className="w-4 h-4" /> Add
              </button>
            </div>
          </div>
          <div className="p-2">
            {team.members.map((m, i) => (
              <div key={i} className="px-3 py-2 border-b border-[var(--border)] last:border-0 flex justify-between items-center hover:bg-[var(--bg\_tertiary)] rounded-md transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs uppercase">
                    {m.substring(0,2)}
                  </div>
                  <span className="font-medium">{m}</span>
                </div>
              </div>
            ))}
            {team.members.length === 0 && <div className="p-4 text-center text-gray-500 text-sm">No members assigned</div>}
          </div>
        </div>

        {/* Top Analysts Chart */}
        <div className="bg-[var(--bg\_secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
          <div className="p-4 border-b border-[var(--border)] bg-black/20">
            <h3 className="font-bold flex items-center gap-2">
              <Target className="w-4 h-4" /> Analyst Performance
            </h3>
          </div>
          <div className="p-4 h-64">
            {stats?.top_analysts?.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.top_analysts} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" horizontal={true} vertical={false} />
                  <XAxis type="number" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis dataKey="username" type="category" stroke="#ccc" fontSize={12} tickLine={false} axisLine={false} width={80} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                    contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }}
                  />
                  <Bar dataKey="triaged" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">Not enough data</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export const TeamsPanel = () => {
  const [selectedTeamId, setSelectedTeamId] = useState(null)

  const { data: teams, isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: async () => {
      const res = await apiClient.get('/api/admin/teams')
      return res.data.teams
    }
  })

  if (isLoading) return <div className="p-8 flex justify-center"><LoadingSpinner /></div>

  const selectedTeam = teams?.find(t => t.team_id === selectedTeamId) || teams?.[0]

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-500" /> Analyst Teams
          </h2>
          <p className="text-[var(--text\_secondary)] text-sm mt-1">Manage SOC shifts, access, and performance tracking.</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20">
          Create New Team
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams?.map(team => (
          <TeamCard 
            key={team.team_id} 
            team={team} 
            isSelected={selectedTeam?.team_id === team.team_id}
            onClick={() => setSelectedTeamId(team.team_id)} 
          />
        ))}
      </div>

      {selectedTeam && (
        <div className="mt-8 pt-8 border-t border-[var(--border)]">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
            {selectedTeam.name} Dashboard
          </h3>
          <TeamDetail team={selectedTeam} />
        </div>
      )}
    </div>
  )
}
