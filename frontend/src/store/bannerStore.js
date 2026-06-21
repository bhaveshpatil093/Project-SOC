import { create } from 'zustand'

export const useBannerStore = create((set) => ({
  banners: [],
  addBanner: (alert) =>
    set((state) => ({
      banners: [...state.banners, { ...alert, _ws_id: Date.now() + Math.random() }].slice(-3),
    })),
  removeBanner: (id) =>
    set((state) => ({
      banners: state.banners.filter((b) => b._ws_id !== id),
    })),
}))
