with open("frontend/src/hooks/useAlerts.js", "r") as f:
    content = f.read()

sorting_logic = """
        // Sort SLA approaching/breached to top
        const now = new Date().getTime()
        fetchedAlerts.sort((a, b) => {
          // Calculate SLA urgency for A
          let urgencyA = 0
          if (a.threat_level === 'critical' || a.threat_level === 'high') {
            const isAckedA = a.alert_status && a.alert_status !== 'open'
            const isResolvedA = a.alert_status === 'closed' || a.alert_status === 'resolved'
            if (!isResolvedA) {
              const deadlineMins = a.threat_level === 'critical' ? (isAckedA ? 30 : 15) : (isAckedA ? 60 : 30)
              const createdA = new Date(a.timestamp || new Date()).getTime()
              const diffA = createdA + (deadlineMins * 60000) - now
              if (diffA <= 0) urgencyA = 2 // breached
              else if (diffA < 10 * 60000) urgencyA = 1 // approaching
            }
          }

          // Calculate SLA urgency for B
          let urgencyB = 0
          if (b.threat_level === 'critical' || b.threat_level === 'high') {
            const isAckedB = b.alert_status && b.alert_status !== 'open'
            const isResolvedB = b.alert_status === 'closed' || b.alert_status === 'resolved'
            if (!isResolvedB) {
              const deadlineMins = b.threat_level === 'critical' ? (isAckedB ? 30 : 15) : (isAckedB ? 60 : 30)
              const createdB = new Date(b.timestamp || new Date()).getTime()
              const diffB = createdB + (deadlineMins * 60000) - now
              if (diffB <= 0) urgencyB = 2
              else if (diffB < 10 * 60000) urgencyB = 1
            }
          }

          return urgencyB - urgencyA // Descending urgency
        })

        store.setAlerts(fetchedAlerts, res.total || 0)
"""

if "urgencyB - urgencyA" not in content:
    content = content.replace("        store.setAlerts(fetchedAlerts, res.total || 0)", sorting_logic)

with open("frontend/src/hooks/useAlerts.js", "w") as f:
    f.write(content)
