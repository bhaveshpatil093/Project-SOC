import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useNotificationStore = create(
  persist(
    (set) => ({
      // History
      history: [],
      unreadCount: 0,

      addNotification: (notification) =>
        set((state) => {
          // notification: { id, title, body, level, timestamp, entity_key, alert_id }
          const newHistory = [notification, ...state.history].slice(0, 20) // Keep last 20
          return {
            history: newHistory,
            unreadCount: state.unreadCount + 1,
          }
        }),

      markAllRead: () => set({ unreadCount: 0 }),
      clearHistory: () => set({ history: [], unreadCount: 0 }),
    }),
    {
      name: 'soc-notification-storage',
      partialize: (state) => ({ history: state.history, unreadCount: state.unreadCount }), // Persist history
    },
  ),
)
