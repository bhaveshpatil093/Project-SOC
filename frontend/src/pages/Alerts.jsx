import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useAlerts, useTriggerScoring } from "../hooks/useAlerts";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { Badge } from "../components/common/Badge";
import { formatDate } from "../utils/formatters";
import { Eye, MessageSquare, FilterX, Play, ArrowUpDown, CheckCircle, RefreshCw, Filter, X, Download } from "lucide-react";
import { useIsMobile } from "../hooks/useMediaQuery";
import { exportAlertsToCSV } from "../utils/exporters";
import { usePreferencesStore } from "../store/preferencesStore";

const ProgressBar = ({ score }) => {
  const scoreNum = parseFloat(score || 0);
  const percentage = Math.min(Math.max(scoreNum * 100, 0), 100);
  
  let colorClass = "bg-green-500";
  if (percentage > 80) colorClass = "bg-red-500";
  else if (percentage > 60) colorClass = "bg-orange-500";
  else if (percentage > 30) colorClass = "bg-yellow-500";

  return (
    <div className="flex items-center gap-3 w-full max-w-[150px]">
      <div className="flex-1 h-2 bg-[var(--bg_tertiary)] rounded-full overflow-hidden">
        <div className={`h-full ${colorClass}`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-xs font-mono w-8 text-[var(--text_secondary)]">{percentage.toFixed(0)}%</span>
    </div>
  );
};

// Desktop Row Component
const AlertRow = React.memo(({ alert, index, page, pageSize, updateStatus, columns, style }) => {
  return (
    <div style={style} className="absolute top-0 left-0 w-full hover:bg-[var(--bg_tertiary)]/70 transition-colors border-b border-[var(--border)]/50 flex">
      <div className="w-16 flex-none px-5 py-3 text-xs text-[var(--text_secondary)] font-medium flex items-center">{(page * pageSize) + index + 1}</div>
      {columns.timestamp && <div className="w-40 flex-none px-5 py-3 text-sm text-[var(--text_secondary)] flex items-center">{formatDate(alert.timestamp)}</div>}
      {columns.host && <div className="w-32 flex-none px-5 py-3 text-sm font-medium text-[var(--text_primary)] flex items-center truncate">{alert.host_id}</div>}
      {columns.user && <div className="w-32 flex-none px-5 py-3 text-sm text-[var(--text_secondary)] flex items-center truncate">{alert.user_name}</div>}
      {columns.logType && <div className="w-32 flex-none px-5 py-3 text-xs text-[var(--text_secondary)] flex items-center truncate">{alert.log_type}</div>}
      {columns.score && <div className="w-48 flex-none px-5 py-3 flex items-center"><ProgressBar score={alert.threat_score} /></div>}
      {columns.level && <div className="w-32 flex-none px-5 py-3 flex items-center"><Badge variant={alert.threat_level}>{alert.threat_level}</Badge></div>}
      {columns.tactic && <div className="flex-1 px-5 py-3 text-xs text-[var(--text_secondary)] truncate flex items-center" title={alert.mitre_tactic}>{alert.mitre_tactic || "-"}</div>}
      {columns.status && <div className="w-36 flex-none px-5 py-3 flex items-center">
        <select 
          value={alert.alert_status || "open"} 
          onChange={(e) => updateStatus({ id: alert._id || alert.id, status: e.target.value })}
          className={`text-xs font-medium px-2 py-1.5 rounded border ${
            alert.alert_status === 'closed' ? 'border-[var(--border)] bg-[var(--bg_secondary)]/50 text-[var(--text_secondary)]' : 'border-[var(--border)] bg-[var(--bg_secondary)] text-[var(--text_primary)]'
          } focus:outline-none focus:border-blue-500 transition-colors w-full`}
        >
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="closed">Closed</option>
        </select>
      </div>}
      {columns.actions && <div className="w-24 flex-none px-5 py-3 flex items-center justify-center">
        <div className="flex items-center gap-4">
          <Link to={`/alerts/${alert._id || alert.id}`} title="View Details" className="text-[var(--text_secondary)] hover:text-blue-400 transition-colors">
            <Eye className="h-5 w-5" />
          </Link>
          <Link to={`/investigation?alert_id=${alert._id || alert.id}`} title="Investigate in SLM" className="text-[var(--text_secondary)] hover:text-purple-400 transition-colors">
            <MessageSquare className="h-5 w-5" />
          </Link>
        </div>
      </div>}
    </div>
  );
});

// Mobile Card Component with Swipe-to-Close
const AlertCard = React.memo(({ alert, updateStatus, style }) => {
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const [isSwiping, setIsSwiping] = useState(false);
  const swipeThreshold = 100;

  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
    setIsSwiping(true);
  };

  const onTouchMove = (e) => setTouchEnd(e.targetTouches[0].clientX);

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) {
      setIsSwiping(false);
      return;
    }
    const distance = touchEnd - touchStart;
    const isRightSwipe = distance > swipeThreshold;
    if (isRightSwipe) {
      updateStatus({ id: alert._id || alert.id, status: "closed" });
    }
    setIsSwiping(false);
  };

  const transform = isSwiping && touchEnd ? `translateX(${Math.max(0, touchEnd - touchStart)}px)` : 'none';
  const opacity = isSwiping && touchEnd ? Math.max(0, 1 - (touchEnd - touchStart) / 300) : 1;

  return (
    <div style={style} className="absolute top-0 left-0 w-full px-4 py-2 flex">
      <div 
        className="w-full bg-[var(--bg_secondary)] rounded-xl border border-[var(--border)] p-4 shadow-sm relative overflow-hidden transition-transform"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        style={{ transform, opacity, transition: isSwiping ? 'none' : 'all 0.3s ease' }}
      >
        {/* Color stripe based on threat level */}
        <div className={`absolute left-0 top-0 bottom-0 w-1 ${
          alert.threat_level === 'critical' ? 'bg-red-500' :
          alert.threat_level === 'high' ? 'bg-orange-500' :
          alert.threat_level === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
        }`} />
        
        <div className="flex justify-between items-start ml-2 mb-2">
          <div>
            <h3 className="font-bold text-[var(--text_primary)]">{alert.entity_key}</h3>
            <p className="text-xs text-[var(--text_secondary)] mt-0.5">{formatDate(alert.timestamp)}</p>
          </div>
          <Badge variant={alert.threat_level}>{alert.threat_level}</Badge>
        </div>

        <div className="ml-2 mt-3 space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-[var(--text_secondary)]">Log Type:</span>
            <span className="text-[var(--text_secondary)] truncate max-w-[150px]">{alert.log_type}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-[var(--text_secondary)]">Threat Score:</span>
            <ProgressBar score={alert.threat_score} />
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-[var(--text_secondary)]">Status:</span>
            <span className={`font-medium ${alert.alert_status === 'closed' ? 'text-[var(--text_secondary)]' : 'text-[var(--text_secondary)]'}`}>
              {alert.alert_status || 'open'}
            </span>
          </div>
        </div>

        <div className="ml-2 mt-4 flex gap-2 border-t border-[var(--border)]/50 pt-3">
          <Link to={`/alerts/${alert._id || alert.id}`} className="flex-1 py-1.5 bg-[var(--bg_tertiary)]/50 hover:bg-[var(--bg_tertiary)] text-[var(--text_secondary)] rounded text-xs font-medium text-center transition-colors">
            Details
          </Link>
          <Link to={`/investigation?alert_id=${alert._id || alert.id}`} className="flex-1 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded text-xs font-medium text-center transition-colors">
            Chat
          </Link>
        </div>
      </div>
    </div>
  );
});

export const Alerts = () => {
  const { 
    alerts, total, loading, error, filters, page, pageSize, sortBy, sortOrder, 
    setFilters, setPage, setSort, clearFilters, updateStatus 
  } = useAlerts();

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [toast, setToast] = useState(null);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const isMobile = useIsMobile();
  
  const parentRef = useRef(null);
  const { alertColumns } = usePreferencesStore();

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const triggerScoringMutation = useTriggerScoring();

  const handleTriggerScoring = useCallback(() => {
    triggerScoringMutation.mutate(undefined, {
      onSuccess: () => setToast("Scoring triggered successfully!")
    });
  }, [triggerScoringMutation]);

  const handleSort = useCallback((col) => {
    if (sortBy === col) {
      setSort(col, sortOrder === "desc" ? "asc" : "desc");
    } else {
      setSort(col, "desc");
    }
  }, [sortBy, sortOrder, setSort]);

  const handleFilterChange = useCallback((e) => {
    const { name, value } = e.target;
    setFilters({ [name]: value });
  }, [setFilters]);

  const memoizedAlerts = useMemo(() => alerts || [], [alerts]);

  const rowVirtualizer = useVirtualizer({
    count: memoizedAlerts.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => isMobile ? 180 : 64, // Cards are taller
    overscan: isMobile ? 5 : 10,
  });

  const renderFilters = () => (
    <>
      <div>
        <label className="block text-xs text-[var(--text_secondary)] mb-1 font-medium">Status</label>
        <select name="status" value={filters.status} onChange={handleFilterChange} className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors">
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <div>
        <label className="block text-xs text-[var(--text_secondary)] mb-1 font-medium">Threat Level</label>
        <select name="threat_level" value={filters.threat_level} onChange={handleFilterChange} className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors">
          <option value="">All</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>
      <div>
        <label className="block text-xs text-[var(--text_secondary)] mb-1 font-medium">From Date</label>
        <input type="date" name="from_time" value={filters.from_time} onChange={handleFilterChange} className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors" />
      </div>
      <div>
        <label className="block text-xs text-[var(--text_secondary)] mb-1 font-medium">To Date</label>
        <input type="date" name="to_time" value={filters.to_time} onChange={handleFilterChange} className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors" />
      </div>
      <div>
        <label className="block text-xs text-[var(--text_secondary)] mb-1 font-medium">Host Search</label>
        <input type="text" name="host_id" value={filters.host_id} onChange={handleFilterChange} placeholder="Enter hostname..." className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors" />
      </div>
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-[var(--text_secondary)] mb-1 font-medium">User Search</label>
          <input type="text" name="user_name" value={filters.user_name} onChange={handleFilterChange} placeholder="Enter username..." className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text_primary)] focus:outline-none focus:border-blue-500 transition-colors" />
        </div>
        <div className="flex items-end">
          <button onClick={clearFilters} className="bg-[var(--bg_tertiary)] hover:bg-[var(--bg_tertiary)] text-[var(--text_primary)] p-2 rounded-lg transition-colors h-[38px] w-[38px] flex items-center justify-center" title="Clear Filters">
            <FilterX className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="space-y-4 md:space-y-6 h-[calc(100vh-6rem)] md:h-[calc(100vh-8rem)] flex flex-col -m-4 md:m-0 p-4 md:p-0">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 flex-none">
        <h1 className="text-xl md:text-2xl font-bold">Alert Investigation</h1>
        <div className="flex items-center gap-2 md:gap-4 overflow-x-auto pb-1 sm:pb-0 hide-scrollbar shrink-0">
          {isMobile && (
            <button
              onClick={() => setShowMobileFilters(true)}
              className="flex items-center gap-2 bg-[var(--bg_secondary)] text-[var(--text_secondary)] border border-[var(--border)] px-3 py-1.5 rounded-lg text-sm font-medium shrink-0"
            >
              <Filter className="h-4 w-4" /> Filters
            </button>
          )}
          <button
            onClick={() => exportAlertsToCSV(memoizedAlerts)}
            className="flex items-center gap-2 bg-[var(--bg_secondary)] text-[var(--text_secondary)] hover:text-[var(--text_primary)] border border-[var(--border)] px-3 py-1.5 rounded-lg text-sm font-medium transition-colors shrink-0"
          >
            <Download className="h-4 w-4" /> Export CSV
          </button>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors shrink-0 ${autoRefresh ? 'bg-blue-500/20 text-blue-400 border-blue-500/50' : 'bg-[var(--bg_secondary)] text-[var(--text_secondary)] border-[var(--border)] hover:text-[var(--text_primary)]'}`}
          >
            <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            Auto-refresh
          </button>
          <button
            onClick={handleTriggerScoring}
            disabled={triggerScoringMutation.isPending}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-[var(--text_primary)] px-3 md:px-4 py-1.5 md:py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
          >
            {triggerScoringMutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Trigger Scoring
          </button>
        </div>
      </div>

      {toast && (
        <div className="bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-4 flex-none mx-4 md:mx-0">
          <CheckCircle className="h-5 w-5" />
          <p className="text-sm">{toast}</p>
        </div>
      )}

      {/* Desktop Filters */}
      {!isMobile && (
        <div className="hidden sm:grid bg-[var(--bg_secondary)] p-4 rounded-xl border border-[var(--border)] grid-cols-2 lg:grid-cols-6 gap-4 items-end flex-none">
          {renderFilters()}
        </div>
      )}

      {/* Mobile Filters Bottom Sheet */}
      {isMobile && showMobileFilters && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-end sm:hidden">
          <div className="bg-[var(--bg_primary)] w-full rounded-t-2xl p-4 border-t border-[var(--border)] max-h-[80vh] overflow-y-auto animate-in slide-in-from-bottom-full">
            <div className="flex justify-between items-center mb-4 pb-2 border-b border-[var(--border)]">
              <h3 className="font-bold text-[var(--text_primary)] flex items-center gap-2"><Filter className="h-4 w-4" /> Filter Alerts</h3>
              <button onClick={() => setShowMobileFilters(false)} className="p-1 rounded-lg text-[var(--text_secondary)] bg-[var(--bg_secondary)]"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex flex-col gap-4 pb-8">
              {renderFilters()}
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className={`bg-[var(--bg_secondary)] md:rounded-xl md:border border-[var(--border)] overflow-hidden shadow-lg flex-1 flex flex-col min-h-0 ${isMobile ? '-mx-4 border-y' : ''}`}>
        <div className="overflow-x-auto flex-1 flex flex-col min-h-0">
          <div className={`${isMobile ? 'w-full' : 'min-w-[1200px]'} flex-1 flex flex-col min-h-0`}>
            
            {/* Desktop Header */}
            {!isMobile && (
              <div className="bg-[var(--bg_primary)]/80 border-b border-[var(--border)] flex flex-none text-left">
                <div className="w-16 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">#</div>
                {alertColumns.timestamp && <div className="w-40 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider cursor-pointer hover:text-[var(--text_primary)] select-none flex items-center gap-1" onClick={() => handleSort("timestamp")}>
                  Timestamp <ArrowUpDown className="h-3 w-3"/>
                </div>}
                {alertColumns.host && <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Host</div>}
                {alertColumns.user && <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">User</div>}
                {alertColumns.logType && <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Log Type</div>}
                {alertColumns.score && <div className="w-48 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider cursor-pointer hover:text-[var(--text_primary)] select-none flex items-center gap-1" onClick={() => handleSort("threat_score")}>
                  Threat Score <ArrowUpDown className="h-3 w-3"/>
                </div>}
                {alertColumns.level && <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Threat Level</div>}
                {alertColumns.tactic && <div className="flex-1 px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">MITRE Tactic</div>}
                {alertColumns.status && <div className="w-36 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider">Status</div>}
                {alertColumns.actions && <div className="w-24 flex-none px-5 py-4 text-xs font-semibold text-[var(--text_secondary)] uppercase tracking-wider text-center">Actions</div>}
              </div>
            )}

            {/* Virtualized Body */}
            <div 
              ref={parentRef} 
              className="flex-1 overflow-y-auto w-full"
            >
              {loading ? (
                <div className="flex items-center justify-center p-16"><LoadingSpinner /></div>
              ) : error ? (
                <div className="p-8"><ErrorBanner message="Failed to load alerts. Please try again." /></div>
              ) : memoizedAlerts.length === 0 ? (
                <div className="p-12 text-center text-[var(--text_secondary)] font-medium">No alerts found matching the given filters.</div>
              ) : (
                <div 
                  style={{
                    height: `${rowVirtualizer.getTotalSize()}px`,
                    width: '100%',
                    position: 'relative',
                  }}
                >
                  {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                    const alert = memoizedAlerts[virtualRow.index];
                    return isMobile ? (
                      <AlertCard
                        key={alert._id || alert.id || virtualRow.index}
                        alert={alert}
                        updateStatus={updateStatus}
                        columns={alertColumns}
                        style={{
                          height: `${virtualRow.size}px`,
                          transform: `translateY(${virtualRow.start}px)`,
                        }}
                      />
                    ) : (
                      <AlertRow
                        key={alert._id || alert.id || virtualRow.index}
                        alert={alert}
                        index={virtualRow.index}
                        page={page}
                        pageSize={pageSize}
                        updateStatus={updateStatus}
                        style={{
                          height: `${virtualRow.size}px`,
                          transform: `translateY(${virtualRow.start}px)`,
                        }}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Pagination */}
        <div className="flex-none px-4 md:px-6 py-3 md:py-4 bg-[var(--bg_primary)]/50 border-t border-[var(--border)] flex flex-col sm:flex-row justify-between items-center gap-3">
          <div className="text-xs md:text-sm text-[var(--text_secondary)] text-center sm:text-left">
            Showing <span className="font-medium text-[var(--text_primary)]">{total === 0 ? 0 : (page * pageSize) + 1}</span> to <span className="font-medium text-[var(--text_primary)]">{Math.min((page * pageSize) + pageSize, total)}</span> of <span className="font-medium text-[var(--text_primary)]">{total}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-3 md:px-4 py-1.5 bg-[var(--bg_secondary)] border border-[var(--border)] rounded-lg text-xs md:text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg_tertiary)] transition-colors text-[var(--text_primary)]"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={(page + 1) * pageSize >= total}
              className="px-3 md:px-4 py-1.5 bg-[var(--bg_secondary)] border border-[var(--border)] rounded-lg text-xs md:text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg_tertiary)] transition-colors text-[var(--text_primary)]"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
