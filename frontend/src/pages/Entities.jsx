import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEntities, addToWatchlist, removeFromWatchlist, getEntityScoreTrends } from '../api/entities';
import { Users, Star, TrendingUp, TrendingDown, Minus, Activity, ShieldAlert, X } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import Badge from '../components/common/Badge';

const Entities = () => {
  const queryClient = useQueryClient();
  const [selectedEntity, setSelectedEntity] = useState(null);

  const { data: entitiesData, isLoading } = useQuery({
    queryKey: ['entities'],
    queryFn: () => getEntities({ limit: 50 }),
    refetchInterval: 30000,
  });

  
  const { data: trendsData } = useQuery({
    queryKey: ['entityTrends', selectedEntity?.entity_key],
    queryFn: () => getEntityScoreTrends(selectedEntity.entity_key),
    enabled: !!selectedEntity
  });
  const trends = trendsData?.data || null;

  const watchMutation = useMutation({
    mutationFn: ({ entityKey, isWatched }) => 
      isWatched ? removeFromWatchlist(entityKey) : addToWatchlist(entityKey, "Analyst flagged"),
    onSuccess: () => {
      queryClient.invalidateQueries(['entities']);
    }
  });

  const entities = entitiesData?.data || [];

  const handleWatchToggle = (e, entity) => {
    e.stopPropagation();
    watchMutation.mutate({ entityKey: entity.entity_key, isWatched: entity.is_watchlisted });
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex overflow-hidden">
      <div className={`flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 transition-all duration-300 ${selectedEntity ? 'pr-96' : ''}`}>
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-[var(--text_primary)] mb-2 flex items-center gap-2">
                <Users className="h-6 w-6 text-indigo-500" />
                Entity Risk Profiles
              </h1>
              <p className="text-[var(--text_secondary)]">Persistent cumulative risk scoring mapped by host and user.</p>
            </div>
          </div>

          <div className="bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] shadow-lg overflow-hidden flex flex-col">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--bg_tertiary)]">
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider w-10"></th>
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Entity</th>
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Risk Level</th>
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Cumulative Score</th>
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Trend</th>
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Lifetime Alerts</th>
                    <th className="px-6 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Last Active</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {isLoading ? (
                    [...Array(5)].map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        <td className="px-6 py-4"><div className="h-4 bg-[var(--bg_tertiary)] rounded w-4"></div></td>
                        <td className="px-6 py-4"><div className="h-4 bg-[var(--bg_tertiary)] rounded w-32"></div></td>
                        <td className="px-6 py-4"><div className="h-6 bg-[var(--bg_tertiary)] rounded w-16"></div></td>
                        <td className="px-6 py-4"><div className="h-2 bg-[var(--bg_tertiary)] rounded w-full"></div></td>
                        <td className="px-6 py-4"><div className="h-4 bg-[var(--bg_tertiary)] rounded w-8"></div></td>
                        <td className="px-6 py-4"><div className="h-4 bg-[var(--bg_tertiary)] rounded w-12"></div></td>
                        <td className="px-6 py-4"><div className="h-4 bg-[var(--bg_tertiary)] rounded w-24"></div></td>
                      </tr>
                    ))
                  ) : entities.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="px-6 py-12 text-center text-[var(--text_secondary)]">
                        No active entities found.
                      </td>
                    </tr>
                  ) : (
                    entities.map((entity) => (
                      <tr 
                        key={entity.entity_key} 
                        onClick={() => setSelectedEntity(entity)}
                        className={`hover:bg-[var(--bg_tertiary)] transition-colors cursor-pointer ${selectedEntity?.entity_key === entity.entity_key ? 'bg-[var(--bg_tertiary)] border-l-2 border-l-indigo-500' : 'border-l-2 border-l-transparent'}`}
                      >
                        <td className="px-6 py-4">
                          <button onClick={(e) => handleWatchToggle(e, entity)} className="focus:outline-none">
                            <Star className={`h-5 w-5 ${entity.is_watchlisted ? 'text-yellow-400 fill-yellow-400' : 'text-[var(--text_secondary)] hover:text-yellow-400'}`} />
                          </button>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-mono text-sm font-semibold text-[var(--text_primary)]">{entity.entity_key}</div>
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={entity.risk_level}>{entity.risk_level}</Badge>
                        </td>
                        <td className="px-6 py-4 w-1/4">
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-mono font-medium min-w-[30px]">{entity.current_risk_score.toFixed(0)}</span>
                            <div className="h-2 flex-1 bg-[var(--bg_tertiary)] rounded-full overflow-hidden">
                              <div 
                                className={`h-full ${entity.risk_level === 'critical' ? 'bg-red-500' : entity.risk_level === 'high' ? 'bg-orange-500' : entity.risk_level === 'medium' ? 'bg-yellow-500' : 'bg-green-500'}`}
                                style={{ width: `${Math.min(100, entity.current_risk_score)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-1">
                            {entity.risk_trend === 'increasing' ? <TrendingUp className="h-4 w-4 text-red-500" /> :
                             entity.risk_trend === 'decreasing' ? <TrendingDown className="h-4 w-4 text-green-500" /> :
                             <Minus className="h-4 w-4 text-[var(--text_secondary)]" />}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-[var(--text_primary)]">
                          {entity.total_alerts}
                        </td>
                        <td className="px-6 py-4 text-sm text-[var(--text_secondary)] whitespace-nowrap">
                          {new Date(entity.last_alert_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Slide-out Panel */}
      <div className={`fixed inset-y-0 right-0 w-96 bg-[var(--bg_secondary)] border-l border-[var(--border)] shadow-2xl transform transition-transform duration-300 ease-in-out z-20 ${selectedEntity ? 'translate-x-0' : 'translate-x-full'}`}>
        {selectedEntity && (
          <div className="h-full flex flex-col pt-16"> {/* Offset for header */}
            <div className="p-4 border-b border-[var(--border)] flex justify-between items-center bg-[var(--bg_tertiary)]">
              <h2 className="text-lg font-bold font-mono truncate">{selectedEntity.entity_key}</h2>
              <button onClick={() => setSelectedEntity(null)} className="p-1 text-[var(--text_secondary)] hover:text-[var(--text_primary)] rounded">
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[var(--bg_primary)] p-4 rounded-lg border border-[var(--border)]">
                  <div className="text-xs text-[var(--text_secondary)] mb-1">Peak Risk Score</div>
                  <div className="text-2xl font-bold text-[var(--text_primary)]">{selectedEntity.peak_risk_score.toFixed(1)}</div>
                </div>
                <div className="bg-[var(--bg_primary)] p-4 rounded-lg border border-[var(--border)]">
                  <div className="text-xs text-[var(--text_secondary)] mb-1">Total Incidents</div>
                  <div className="text-2xl font-bold text-[var(--text_primary)]">{selectedEntity.total_incidents}</div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-[var(--text_secondary)] uppercase tracking-wider mb-3">Top MITRE Tactics</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedEntity.top_tactics?.map(t => (
                    <span key={t} className="px-2 py-1 text-xs bg-red-900/20 text-red-400 border border-red-900/50 rounded-md">{t}</span>
                  ))}
                  {!selectedEntity.top_tactics?.length && <span className="text-xs text-[var(--text_secondary)] italic">No specific tactics matched yet.</span>}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-[var(--text_secondary)] uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Activity className="h-4 w-4" /> Risk Trend
                </h3>
                {trends ? (
                  <div className="bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg p-4">
                    <div className="flex justify-between items-center mb-4">
                      <div>
                        <div className="text-xs text-[var(--text_secondary)]">7-Day Trend</div>
                        <div className="flex items-center gap-2 text-lg font-bold text-[var(--text_primary)]">
                          {trends.trend_7d === 'increasing' ? <><TrendingUp className="h-5 w-5 text-red-500" /> Increasing</> :
                           trends.trend_7d === 'decreasing' ? <><TrendingDown className="h-5 w-5 text-green-500" /> Decreasing</> :
                           <><Minus className="h-5 w-5 text-gray-500" /> Stable</>}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-[var(--text_secondary)]">Volatility</div>
                        <div className="text-lg font-bold text-[var(--text_primary)]">{trends.score_volatility.toFixed(3)}</div>
                      </div>
                    </div>
                    <div className="h-24 w-full">
                      {trends.recent_scores && trends.recent_scores.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={trends.recent_scores.map((s, i) => ({ val: s }))}>
                            <Line type="monotone" dataKey="val" stroke="#6366f1" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-xs text-[var(--text_secondary)]">No recent scores</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-24 bg-[var(--bg_primary)] rounded-lg border border-[var(--border)] flex items-center justify-center text-[var(--text_secondary)] text-sm">
                    Loading trends...
                  </div>
                )}
              </div>

            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Entities;
