with open("frontend/src/pages/Alerts.jsx", "r") as f:
    content = f.read()

import_stmt = "import { Clock, AlertCircle } from 'lucide-react'"
if "AlertCircle" not in content:
    content = content.replace("from 'lucide-react'", "  AlertCircle,\n  Clock,\nfrom 'lucide-react'")

sla_component = """
const SLACountdown = ({ alert }) => {
  const [timeLeft, setTimeLeft] = useState('')
  const [status, setStatus] = useState('met') // met, approaching, breached
  
  useEffect(() => {
    // Determine deadline based on SLA rules
    // This could also come directly from backend if alert object includes it
    // For now, we'll implement a simple client-side logic for the visual countdown
    // Critical: 15m ack, 30m triage
    if (alert.threat_level !== 'critical' && alert.threat_level !== 'high') {
      return
    }
    
    // Simplistic fallback if backend doesn't provide SLA in the stream yet
    const created = new Date(alert.timestamp || new Date()).getTime()
    const isAcked = alert.alert_status && alert.alert_status !== 'open'
    const deadlineMins = alert.threat_level === 'critical' ? (isAcked ? 30 : 15) : (isAcked ? 60 : 30)
    const deadline = created + (deadlineMins * 60000)
    
    const update = () => {
      const now = new Date().getTime()
      const diff = deadline - now
      
      if (diff <= 0) {
        setStatus('breached')
        setTimeLeft('00:00')
        return
      }
      
      if (diff < 10 * 60000) {
        setStatus('approaching')
      } else {
        setStatus('met')
      }
      
      const m = Math.floor(diff / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`)
    }
    
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [alert])

  if (alert.threat_level !== 'critical' && alert.threat_level !== 'high') {
    return <div className="text-[var(--text_secondary)]">-</div>
  }
  
  if (alert.alert_status === 'closed') {
    return <div className="text-green-500 font-bold"><CheckCircle className="w-4 h-4 inline" /></div>
  }

  let colorClass = 'text-green-500'
  let Icon = Clock
  if (status === 'breached') {
    colorClass = 'text-red-500 animate-pulse'
    Icon = AlertCircle
  } else if (status === 'approaching') {
    colorClass = 'text-amber-500'
  }

  return (
    <div className={`flex items-center gap-1.5 font-mono text-xs font-bold ${colorClass}`}>
      <Icon className="w-3.5 h-3.5" />
      {timeLeft}
    </div>
  )
}
"""

if "SLACountdown" not in content:
    content = content.replace("const ProgressBar = ({ score }) => {", sla_component + "\nconst ProgressBar = ({ score }) => {")

row_col = """
      {columns.sla && (
        <div className="w-32 flex-none px-5 py-3 flex items-center">
          <SLACountdown alert={alert} />
        </div>
      )}"""

if "{columns.sla" not in content:
    content = content.replace("{columns.status && (", row_col + "\n      {columns.status && (")

header_col = """
                {alertColumns.sla && (
                  <div className="w-32 flex-none px-5 py-4 text-xs font-semibold text-[var(--text\_secondary)] uppercase tracking-wider">
                    SLA
                  </div>
                )}"""

if "{alertColumns.sla" not in content:
    content = content.replace("{alertColumns.status && (", header_col + "\n                {alertColumns.status && (")

with open("frontend/src/pages/Alerts.jsx", "w") as f:
    f.write(content)
