import { create } from 'zustand'

export const useToastStore = create((set) => ({
  toasts: [],
  showToast: (message, type = 'success') => {
    const id = Date.now() + Math.random()
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }))
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }))
    }, 4000)
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}))

export const useToast = () => {
  const store = useToastStore()
  return { showToast: store.showToast, toasts: store.toasts }
}
