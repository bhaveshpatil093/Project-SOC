import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useNotificationStore = create(
  persist(
    (set) => ({
      // Settings
      settings: {
        browserEnabled: false,
        soundEnabled: true,
        volume: 50,
        threshold: 'medium', // 'all', 'medium', 'high', 'critical'
      },
      updateSettings: (newSettings) => 
        set((state) => ({ 
          settings: { ...state.settings, ...newSettings } 
        })),

      // History
      history: [],
      unreadCount: 0,
      
      addNotification: (notification) => set((state) => {
        // notification: { id, title, body, level, timestamp, entity_key, alert_id }
        const newHistory = [notification, ...state.history].slice(0, 20); // Keep last 20
        return {
          history: newHistory,
          unreadCount: state.unreadCount + 1
        };
      }),

      markAllRead: () => set({ unreadCount: 0 }),
      clearHistory: () => set({ history: [], unreadCount: 0 }),
    }),
    {
      name: 'soc-notification-storage',
      partialize: (state) => ({ settings: state.settings }), // Only persist settings
    }
  )
);
