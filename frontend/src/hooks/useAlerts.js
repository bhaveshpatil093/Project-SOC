import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAlertStore } from "../store/alertStore";
import { getAlerts, getAlert, getAlertTimeline, getAlertStats, updateAlertStatus as apiUpdateStatus, triggerScoring } from "../api/alerts";
import { usePreferencesStore } from "../store/preferencesStore";

export function useAlerts() {
  const store = useAlertStore();
  const prefs = usePreferencesStore();
  
  const activePageSize = prefs.alertsPageSize;
  const activeSortBy = store.sortBy || prefs.defaultAlertSort;
  const activeSortOrder = store.sortOrder || "desc";

  const params = {
    ...store.filters,
    limit: activePageSize,
    offset: store.page * activePageSize,
    sort_by: activeSortBy,
    sort_desc: activeSortOrder === 'desc'
  };

  const query = useQuery({
    queryKey: ["alerts", params],
    queryFn: async () => {
      store.setLoading(true);
      try {
        const res = await getAlerts(params);
        let fetchedAlerts = res.alerts || [];
        
        // Filter out low alerts locally if disabled in preferences and no explicit filter is applied
        if (!prefs.showLowAlerts && !params.threat_level) {
           fetchedAlerts = fetchedAlerts.filter(a => a.threat_level !== 'low');
        }

        store.setAlerts(fetchedAlerts, res.total || 0);
        store.setError(null);
        return res;
      } catch (err) {
        store.setError(err.message);
        throw err;
      } finally {
        store.setLoading(false);
      }
    },
    refetchInterval: 30000,
  });

  const statsQuery = useQuery({
    queryKey: ["alertStats"],
    queryFn: async () => {
      const res = await getAlertStats();
      store.setStats(res);
      return res;
    },
    refetchInterval: 30000,
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }) => apiUpdateStatus(id, status),
    onSuccess: (_, variables) => {
      store.updateAlertStatus(variables.id, variables.status);
    }
  });

  return {
    alerts: store.alerts,
    total: store.total,
    loading: query.isLoading || store.loading,
    error: store.error,
    filters: store.filters,
    page: store.page,
    pageSize: activePageSize,
    sortBy: activeSortBy,
    sortOrder: activeSortOrder,
    stats: store.stats || statsQuery.data,
    refetch: query.refetch,
    setFilters: store.setFilters,
    setPage: store.setPage,
    setSort: store.setSort,
    clearFilters: store.clearFilters,
    updateStatus: updateStatusMutation.mutate,
    isUpdating: updateStatusMutation.isPending
  };
}

export function useAlert(alert_id) {
  const query = useQuery({
    queryKey: ["alert", alert_id],
    queryFn: () => getAlert(alert_id),
    enabled: !!alert_id,
  });

  return {
    alert: query.data,
    loading: query.isLoading,
    error: query.isError ? query.error : null,
    refetch: query.refetch,
  };
}

export function useAlertTimeline(alert_id) {
  const query = useQuery({
    queryKey: ["alertTimeline", alert_id],
    queryFn: () => getAlertTimeline(alert_id),
    enabled: !!alert_id,
  });

  return {
    timeline: query.data?.alerts || query.data || [],
    loading: query.isLoading,
  };
}

// Aliases required by other components
export const useUpdateAlertStatus = () => {
  const queryClient = useQueryClient();
  const store = useAlertStore();
  return useMutation({
    mutationFn: ({ id, status }) => apiUpdateStatus(id, status),
    onSuccess: (_, vars) => {
      store.updateAlertStatus(vars.id, vars.status);
      queryClient.invalidateQueries({ queryKey: ["alert", vars.id] });
    }
  });
};

export const useTriggerScoring = () => {
  return useMutation({
    mutationFn: triggerScoring,
  });
};
