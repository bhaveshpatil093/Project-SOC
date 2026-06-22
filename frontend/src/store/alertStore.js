import { create } from 'zustand'

export const useAlertStore = create((set) => ({
  alerts: [],
  total: 0,
  loading: false,
  error: null,
  filters: {
    status: '',
    threat_level: '',
    host_id: '',
    user_name: '',
    from_time: '',
    to_time: '',
  },
  page: 0,
  sortBy: null,
  sortOrder: null,
  lastRefresh: null,
  stats: null,

  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      page: 0,
    })),

  setPage: (page) => set({ page }),

  setSort: (field, order) => set({ sortBy: field, sortOrder: order, page: 0 }),

  setAlerts: (alerts, total) => set({ alerts, total, lastRefresh: Date.now() }),

  setStats: (stats) => set({ stats }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  clearFilters: () =>
    set({
      filters: {
        status: '',
        threat_level: '',
        host_id: '',
        user_name: '',
        from_time: '',
        to_time: '',
      },
      page: 0,
    }),

  updateAlertStatus: (alert_id, status) =>
    set((state) => ({
      alerts: state.alerts.map((a) => {
        const id = a._id || a.id
        return id === alert_id ? { ...a, status, alert_status: status } : a
      }),
    })),
}))
