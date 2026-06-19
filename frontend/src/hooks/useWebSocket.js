import { useEffect, useState, useRef } from "react";
import { useAlertStore } from "../store/alertStore";
import { useBannerStore } from "../store/bannerStore";
import { useNotifications } from "./useNotifications";
import { create } from "zustand";

export const useWebSocketStore = create((set) => ({
  wsConnected: false,
  lastIngestion: null,
  lastScoring: null,
  ingestionRunning: false,
  scoringRunning: false,
  liveAlerts: [],
  liveStats: null,
  setWsConnected: (status) => set({ wsConnected: status }),
  setLastIngestion: (data) => set({ lastIngestion: data, ingestionRunning: false }),
  setLastScoring: (data) => set({ lastScoring: data, scoringRunning: false }),
  setIngestionRunning: (status) => set({ ingestionRunning: status }),
  setScoringRunning: (status) => set({ scoringRunning: status }),
  setLiveStats: (data) => set({ liveStats: data }),
  addLiveAlert: (alert) => set((state) => {
    const alertId = alert.id || alert._id;
    const exists = state.liveAlerts.find(a => (a.id || a._id) === alertId);
    if (exists) return state;
    return { liveAlerts: [alert, ...state.liveAlerts].slice(0, 20) };
  })
}));

export function useWebSocket(isAuthenticated = false) {
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  
  const { notify } = useNotifications();
  
  const wsRef = useRef(null);
  const retryCount = useRef(0);
  const maxRetries = 10;

  useEffect(() => {
    let timeoutId;
    
    if (!isAuthenticated) return;

    const connect = () => {
      const ws = new WebSocket("ws://localhost:8000/ws/alerts");
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        useWebSocketStore.getState().setWsConnected(true);
        setReconnecting(false);
        retryCount.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          setLastMessage(msg);
          
          if (msg.type === "new_alert" && msg.data) {
             const alertData = msg.data;
             
             // 1. Inject into live Alert Grid
             useAlertStore.setState(state => {
                 // Check if it already exists to prevent dups
                 const alertId = alertData.id || alertData._id;
                 const exists = state.alerts.find(a => (a.id || a._id) === alertId);
                 if (exists) return state;
                 
                 // Unshift gracefully
                 return {
                     alerts: [alertData, ...state.alerts].slice(0, state.pageSize),
                     total: state.total + 1
                 }
             });

             // 2. Trigger Multi-Channel Notifications
             notify(alertData);

             // 3. Trigger Notification Banner for High/Critical (Legacy if still used)
             const threat = (alertData.threat_level || "").toLowerCase();
             if (threat === "critical" || threat === "high") {
                 useBannerStore.getState().addBanner(alertData);
             }

             // 4. Add to live alerts feed for dashboard
             useWebSocketStore.getState().addLiveAlert(alertData);
          }
          else if (msg.type === "scoring_started") {
             useWebSocketStore.getState().setScoringRunning(true);
          }
          else if (msg.type === "scoring_complete") {
             useWebSocketStore.getState().setLastScoring(msg.data);
          }
          else if (msg.type === "ingestion_started") {
             useWebSocketStore.getState().setIngestionRunning(true);
          }
          else if (msg.type === "ingestion_complete") {
             useWebSocketStore.getState().setLastIngestion(msg.data);
          }
          else if (msg.type === "stats_update") {
             useWebSocketStore.getState().setLiveStats(msg.data);
          }
        } catch (err) {
          console.error("Failed to parse WS message", err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        useWebSocketStore.getState().setWsConnected(false);
        if (retryCount.current < maxRetries) {
          setReconnecting(true);
          retryCount.current += 1;
          timeoutId = setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (wsRef.current) wsRef.current.close();
    };
  }, [isAuthenticated, notify]);

  return { connected, reconnecting, lastMessage };
}
