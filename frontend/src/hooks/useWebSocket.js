import { useEffect, useState, useRef } from "react";
import { useAlertStore } from "../store/alertStore";
import { useBannerStore } from "../store/bannerStore";

export function useWebSocket(isAuthenticated = false) {
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  
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

             // 2. Trigger Notification Banner for High/Critical
             const threat = (alertData.threat_level || "").toLowerCase();
             if (threat === "critical" || threat === "high") {
                 useBannerStore.getState().addBanner(alertData);
             }
          }
        } catch (err) {
          console.error("Failed to parse WS message", err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
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
  }, [isAuthenticated]);

  return { connected, reconnecting, lastMessage };
}
