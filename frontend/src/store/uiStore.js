import { create } from 'zustand';
import { getInitialTheme, applyTheme } from '../utils/theme';

export const useUiStore = create((set) => ({
  sidebarOpen: true,
  theme: getInitialTheme(),
  toasts: [],
  
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (isOpen) => set({ sidebarOpen: isOpen }),
  toggleTheme: () => set(state => {
      const next = state.theme === "dark" ? "light" : "dark";
      applyTheme(next);
      return { theme: next };
  }),
  
  addToast: (message, type = 'success') => {
    const id = Date.now() + Math.random();
    set(state => ({
      toasts: [...state.toasts, { id, message, type }]
    }));
    
    setTimeout(() => {
      set(state => ({
        toasts: state.toasts.filter(t => t.id !== id)
      }));
    }, 4000);
  },
  
  removeToast: (id) => set(state => ({
    toasts: state.toasts.filter(t => t.id !== id)
  }))
}));
