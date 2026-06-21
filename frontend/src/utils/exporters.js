import jsPDF from 'jspdf'
import 'jspdf-autotable'
import { formatDate } from './formatters'

// Helper: Download a file Blob
const downloadFile = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// =======================
// CSV & JSON Exports
// =======================

export function exportAlertsToCSV(alerts, filename = 'soc_alerts.csv') {
  const headers = [
    'ID',
    'Timestamp',
    'Host',
    'User',
    'Log Type',
    'Threat Score',
    'Threat Level',
    'MITRE Tactic',
    'Triggered Rules',
    'Status',
  ]
  const rows = alerts.map((a) => [
    a._id || a.id || 'N/A',
    a.timestamp || '',
    a.host_id || '',
    a.user_name || '',
    a.log_type || '',
    a.threat_score || 0,
    a.threat_level || '',
    a.mitre_tactic || '',
    a.triggered_rules?.join('|') || '',
    a.alert_status || '',
  ])
  downloadCSV(headers, rows, filename)
}

export function exportIncidentsToCSV(incidents, filename = 'soc_incidents.csv') {
  const headers = [
    'Incident ID',
    'Entity',
    'Started At',
    'Duration (min)',
    'Alert Count',
    'Max Threat',
    'Stage',
    'Multi-Stage',
    'Status',
  ]
  const rows = incidents.map((i) => [
    i.incident_id || '',
    i.entity_key || '',
    i.started_at || '',
    Math.round((i.duration_seconds || 0) / 60),
    i.alert_count || 0,
    i.max_threat_score || 0,
    i.attack_stage || '',
    i.is_multi_stage ? 'Yes' : 'No',
    i.status || '',
  ])
  downloadCSV(headers, rows, filename)
}

export function exportFeedbackToCSV(feedback, filename = 'soc_feedback.csv') {
  const headers = ['Alert ID', 'Analyst', 'Feedback Type', 'Status Update', 'Notes', 'Timestamp']
  const rows = feedback.map((f) => [
    f.alert_id || '',
    f.analyst_id || '',
    f.feedback_type || '',
    f.status_update || '',
    f.notes ? f.notes.replace(/,/g, ';') : '',
    f.timestamp || '',
  ])
  downloadCSV(headers, rows, filename)
}

function downloadCSV(headers, rows, filename) {
  const csvContent = [
    headers.join(','),
    ...rows.map((e) => e.map((field) => `"${String(field).replace(/"/g, '""')}"`).join(',')),
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  downloadFile(blob, filename)
}

export function downloadJSON(data, filename = 'data.json') {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  downloadFile(blob, filename)
}

// =======================
// PDF Exports
// =======================

const setupDoc = (title) => {
  const doc = new jsPDF()
  const pageWidth = doc.internal.pageSize.width

  // Header
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(20)
  doc.text('ISRO ISTRAC SOC', 14, 22)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(12)
  doc.setTextColor(100)
  doc.text(title, 14, 30)

  // Line separator
  doc.setDrawColor(200)
  doc.line(14, 35, pageWidth - 14, 35)

  return { doc, pageWidth }
}

const addFooter = (doc) => {
  const pageCount = doc.internal.getNumberOfPages()
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i)
    doc.setFontSize(10)
    doc.setTextColor(150)
    const text = `ISRO ISTRAC — Confidential — Generated: ${new Date().toLocaleString()} — Page ${i} of ${pageCount}`
    doc.text(text, 14, doc.internal.pageSize.height - 10)
  }
}

export async function generateAlertReport(alert) {
  const { doc, pageWidth } = setupDoc(`Alert Report: ${alert._id || alert.id}`)

  // Page 1: Alert Summary
  doc.setTextColor(0)
  doc.setFontSize(14)
  doc.setFont('helvetica', 'bold')
  doc.text('Alert Summary', 14, 45)

  doc.setFontSize(11)
  doc.setFont('helvetica', 'normal')

  const summaryData = [
    ['Entity', alert.host_id || 'N/A'],
    ['User', alert.user_name || 'N/A'],
    ['Timestamp', alert.timestamp ? formatDate(alert.timestamp) : 'N/A'],
    ['Log Type', alert.log_type || 'N/A'],
    ['Threat Level', alert.threat_level?.toUpperCase() || 'N/A'],
    ['Threat Score', `${((alert.threat_score || 0) * 100).toFixed(1)}/100`],
    ['Status', alert.alert_status?.toUpperCase() || 'N/A'],
    ['MITRE Tactic', alert.mitre_tactic || 'N/A'],
  ]

  doc.autoTable({
    startY: 50,
    body: summaryData,
    theme: 'plain',
    styles: { fontSize: 11, cellPadding: 2 },
    columnStyles: { 0: { fontStyle: 'bold', cellWidth: 40 } },
  })

  let currentY = doc.lastAutoTable.finalY + 15

  // Rule Matches
  if (alert.triggered_rules && alert.triggered_rules.length > 0) {
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Triggered Rules', 14, currentY)

    doc.autoTable({
      startY: currentY + 5,
      head: [['Rule Name']],
      body: alert.triggered_rules.map((r) => [r]),
      theme: 'grid',
      headStyles: { fillColor: [41, 128, 185] },
    })
    currentY = doc.lastAutoTable.finalY + 15
  }

  // Feature Importance
  if (alert.feature_importance) {
    if (currentY > 230) {
      doc.addPage()
      currentY = 20
    }

    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Feature Importance (SHAP)', 14, currentY)

    const features = Object.entries(alert.feature_importance)
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      .slice(0, 10)

    doc.autoTable({
      startY: currentY + 5,
      head: [['Feature', 'Contribution']],
      body: features.map(([k, v]) => [k, typeof v === 'number' ? v.toFixed(4) : v]),
      theme: 'grid',
      headStyles: { fillColor: [41, 128, 185] },
    })
    currentY = doc.lastAutoTable.finalY + 15
  }

  addFooter(doc)
  doc.save(`Alert_${alert._id || alert.id}.pdf`)
}

export async function generateIncidentReport(incident, alerts = []) {
  const { doc, pageWidth } = setupDoc(`Incident Report: ${incident.incident_id}`)

  // Page 1: Cover & Summary
  doc.setTextColor(0)
  doc.setFontSize(14)
  doc.setFont('helvetica', 'bold')
  doc.text('Incident Summary', 14, 45)

  doc.setFontSize(11)
  doc.setFont('helvetica', 'normal')

  const summaryData = [
    ['Entity Key', incident.entity_key || 'N/A'],
    ['Threat Level', incident.threat_level?.toUpperCase() || 'N/A'],
    ['Max Threat Score', `${((incident.max_threat_score || 0) * 100).toFixed(1)}/100`],
    ['Status', incident.status?.toUpperCase() || 'N/A'],
    ['First Seen', incident.started_at ? formatDate(incident.started_at) : 'N/A'],
    ['Last Seen', incident.last_seen ? formatDate(incident.last_seen) : 'N/A'],
    ['Duration', `${Math.round((incident.duration_seconds || 0) / 60)} minutes`],
    ['Alert Count', (incident.alert_count || 0).toString()],
    ['Attack Stage', (incident.attack_stage || 'N/A').replace('_', ' ').toUpperCase()],
    ['Multi-Stage', incident.is_multi_stage ? 'Yes' : 'No'],
  ]

  doc.autoTable({
    startY: 50,
    body: summaryData,
    theme: 'plain',
    styles: { fontSize: 11, cellPadding: 2 },
    columnStyles: { 0: { fontStyle: 'bold', cellWidth: 50 } },
  })

  let currentY = doc.lastAutoTable.finalY + 15

  // MITRE Mapping
  doc.setFontSize(14)
  doc.setFont('helvetica', 'bold')
  doc.text('MITRE ATT&CK Mapping', 14, currentY)

  doc.autoTable({
    startY: currentY + 5,
    body: [
      ['Tactics', (incident.mitre_tactics || []).join(', ') || 'None mapped'],
      ['Techniques', (incident.mitre_techniques || []).join(', ') || 'None mapped'],
    ],
    theme: 'grid',
    headStyles: { fillColor: [41, 128, 185] },
    columnStyles: { 0: { fontStyle: 'bold', cellWidth: 40 } },
  })

  // Page 2: Attack Chain Timeline
  doc.addPage()
  doc.setFontSize(14)
  doc.setFont('helvetica', 'bold')
  doc.text('Attack Chain & Timeline', 14, 20)

  if (incident.attack_chain && incident.attack_chain.length > 0) {
    doc.autoTable({
      startY: 30,
      head: [['Time Delta', 'Log Source', 'Tactic', 'Threat Score']],
      body: incident.attack_chain.map((ac) => [
        ac.time,
        ac.log_type,
        ac.tactic,
        ((ac.score || 0) * 100).toFixed(1),
      ]),
      theme: 'striped',
      headStyles: { fillColor: [41, 128, 185] },
    })
  } else {
    doc.setFontSize(11)
    doc.setFont('helvetica', 'normal')
    doc.text('No attack chain data available.', 14, 30)
  }

  // Page 3: Contributing Alerts
  if (alerts && alerts.length > 0) {
    doc.addPage()
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Contributing Alerts', 14, 20)

    doc.autoTable({
      startY: 30,
      head: [['Timestamp', 'Log Type', 'Score', 'Tactic']],
      body: alerts.map((a) => [
        a.timestamp ? formatDate(a.timestamp) : '',
        a.log_type || '',
        ((a.threat_score || 0) * 100).toFixed(1),
        a.mitre_tactic || '',
      ]),
      theme: 'grid',
      headStyles: { fillColor: [41, 128, 185] },
      styles: { fontSize: 9 },
    })
  }

  addFooter(doc)
  doc.save(`Incident_${incident.incident_id}.pdf`)
}
