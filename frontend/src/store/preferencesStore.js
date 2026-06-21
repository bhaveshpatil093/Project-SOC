import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { applyTheme } from '../utils/theme';

const initialState = {
  // Display
  theme: "dark",
  alertsPageSize: 50,
  defaultAlertSort: "threat_score",
  showLowAlerts: true,

  // Notifications
  notificationsEnabled: false,
  soundEnabled: true,
  soundVolume: 50,
  notifyForLevel: "high", // "critical" | "high" | "medium" | "all"

  // Dashboard
  dashboardRefreshInterval: 30, // seconds
  showLiveStream: true,
  defaultTimeRange: "24h", // "1h"|"24h"|"7d"|"30d"

  // Investigation (SLM)
  defaultAnalystName: "",
  autoLoadAlertContext: true,
  showParsedResponse: true,

  // Table columns visibility
  alertColumns: {
    timestamp: true,
    host: true,
    user: true,
    logType: true,
    score: true,
    level: true,
    tactic: true,
    status: true,
    actions: true,
  },
};

export const usePreferencesStore = create(
  persist(
    (set, get) => ({
      ...initialState,

      setPreference: (key, value) => {
        set({ [key]: value });
        if (key === 'theme') {
            applyTheme(value);
        }
      },

      setAlertColumn: (column, isVisible) => {
        set((state) => ({
          alertColumns: {
            ...state.alertColumns,
            [column]: isVisible,
          },
        }));
      },

      resetPreferences: () => {
        set(initialState);
        applyTheme(initialState.theme);
      },
    }),
    { 
      name: "soc-preferences",
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyTheme(state.theme);
        }
      }
    }
  )
);
