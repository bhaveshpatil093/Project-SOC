import { useCallback, useState } from 'react';
import { useNotificationStore } from '../store/notificationStore';
import { usePreferencesStore } from '../store/preferencesStore';
import { useToast } from '../contexts/ToastContext';

// Helper to check if the document is focused
const isDocumentFocused = () => {
  return document.hasFocus();
};

export function useNotifications() {
  const { addNotification } = useNotificationStore();
  const { notificationsEnabled, soundEnabled, soundVolume, notifyForLevel } = usePreferencesStore();
  const { showToast } = useToast();
  const [notificationPermission, setNotificationPermission] = useState(
    typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default'
  );

  const requestPermission = async () => {
    if (!('Notification' in window)) return 'denied';
    const permission = await Notification.requestPermission();
    setNotificationPermission(permission);
    return permission;
  };

  const sendBrowserNotification = useCallback((title, body, alertId) => {
    if (!notificationsEnabled || notificationPermission !== 'granted') return;
    if (isDocumentFocused()) return; // Don't notify if user is actively on the page

    const notification = new Notification(title, {
      body,
      icon: '/vite.svg', // Fallback icon
      tag: alertId || 'soc-alert',
    });

    notification.onclick = () => {
      window.focus();
      if (alertId) {
        window.location.href = `/alerts/${alertId}`;
      }
      notification.close();
    };
  }, [notificationsEnabled, notificationPermission]);

  const playAlertSound = useCallback((level) => {
    if (!soundEnabled || soundVolume === 0) return;

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const masterGain = audioCtx.createGain();
    masterGain.gain.value = soundVolume / 100;
    masterGain.connect(audioCtx.destination);

    const playTone = (freq, type, duration, startTime) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(1, startTime + 0.05);
      gain.gain.linearRampToValueAtTime(0, startTime + duration);

      osc.connect(gain);
      gain.connect(masterGain);

      osc.start(startTime);
      osc.stop(startTime + duration);
    };

    const now = audioCtx.currentTime;

    switch (level) {
      case 'critical':
        // Urgent beep: 880Hz, 3 pulses
        playTone(880, 'square', 0.15, now);
        playTone(880, 'square', 0.15, now + 0.25);
        playTone(880, 'square', 0.15, now + 0.5);
        break;
      case 'high':
        // Single tone: 660Hz
        playTone(660, 'triangle', 0.4, now);
        break;
      case 'medium':
        // Soft click
        playTone(330, 'sine', 0.1, now);
        break;
      default:
        break;
    }
  }, [soundEnabled, soundVolume]);

  const showToastNotification = useCallback((alert) => {
    const isCritical = alert.threat_level === 'critical';
    showToast({
      id: `toast-${alert._id || alert.id || Date.now()}`,
      title: `New ${alert.threat_level?.toUpperCase() || 'ALERT'} Threat Detected`,
      message: `${alert.entity_key || alert.host_id || 'Unknown Entity'} - ${alert.log_type || 'Anomaly'}`,
      level: alert.threat_level,
      persistent: isCritical,
      duration: 6000
    });
  }, [showToast]);

  const notify = useCallback((alert) => {
    // Map string levels to numeric for threshold comparison
    const levelMap = { critical: 4, high: 3, medium: 2, low: 1, all: 0 };
    const alertScore = levelMap[alert.threat_level?.toLowerCase()] || 0;
    const thresholdScore = levelMap[notifyForLevel] || 0;

    // Orchestrate
    if (alertScore >= thresholdScore) {
      if (alertScore >= levelMap.high) {
        sendBrowserNotification(
          `SOC Alert: ${alert.threat_level?.toUpperCase()}`,
          `${alert.entity_key} triggered ${alert.log_type}`,
          alert._id || alert.id
        );
        playAlertSound(alert.threat_level);
        showToastNotification(alert);
      } else if (alertScore === levelMap.medium) {
        showToastNotification(alert);
        playAlertSound('medium');
      }
    }

    // Always add to history regardless of threshold, so user can see what they missed
    addNotification({
      id: alert._id || alert.id || Date.now().toString(),
      title: `${alert.entity_key}`,
      body: alert.log_type,
      level: alert.threat_level,
      timestamp: alert.timestamp || new Date().toISOString(),
      alert_id: alert._id || alert.id
    });
  }, [notifyForLevel, sendBrowserNotification, playAlertSound, showToastNotification, addNotification]);

  return { notify, requestPermission, notificationPermission, playAlertSound };
}
