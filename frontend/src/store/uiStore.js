import { create } from 'zustand';

export const useUiStore = create((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  toasts: [],
  
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
  
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
